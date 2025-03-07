import gc
import io
import sys
import tempfile
import time
import datetime
import uuid
from moviepy.editor import (
    vfx,
    ImageClip,
    concatenate_videoclips,
    AudioFileClip,
)
import av
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
from gtts import gTTS
import concurrent.futures

import requests
from tqdm import tqdm

from app.makers.images import wrap_text_by_pixel
from pydub import AudioSegment
import subprocess

FONT_FOLDER = os.path.join(os.getcwd(), "app/makers/fonts")

date_create = datetime.datetime.now().strftime("%Y_%m_%d")
UPLOAD_FOLDER = os.path.join(os.getcwd(), f"uploads/{date_create}")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class MakerVideo:
    def __init__(self):
        # Cấu hình
        self.video_size = (1080, 1920)  # (width, height)
        self.duration_per_image = 5  # giây
        self.fps = 25
        self.total_frames = self.duration_per_image * self.fps
        self.font = None
        self.container = None
        self.stream = None
        self.audio_stream = None
        self.total_times = 0
        try:
            self.font = ImageFont.truetype(f"{FONT_FOLDER}/dotum.ttc", 80)
        except IOError:
            print(f"Không tìm thấy font dotum.ttc, sử dụng font mặc định.")
            self.font = ImageFont.load_default()

    def standardize_video(self, input_file, output_file):
        """
        Re-encode video để chuẩn hóa các tham số:
        - Video: codec H.264, pixel format yuv420p, fps giữ nguyên.
        - Audio: codec AAC, sample rate 44100, 2 kênh, sample format fltp.
        """
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_file,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "44100",
            "-ac",
            "2",
            output_file,
        ]
        print("Standardizing:", " ".join(cmd))
        subprocess.run(cmd, check=True)

    def merge_videos(self, video_files=[]):
        """
        Standardize các file video, sau đó merge chúng lại bằng concat filter
        với reset timestamp cho video và audio.
        """

        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex

        file_name = f"{timestamp}_{unique_id}.mp4"
        output_file = os.path.join(UPLOAD_FOLDER, file_name)

        # Tạo thư mục tạm để lưu các file đã chuẩn hóa
        temp_dir = tempfile.gettempdir()
        std_files = []
        for file in video_files:
            std_file = os.path.join(temp_dir, f"std_{os.path.basename(file)}")
            self.standardize_video(file, std_file)
            std_files.append(std_file)

        n = len(std_files)
        # Xây dựng lệnh FFmpeg cho merge
        cmd = ["ffmpeg"]
        for f in std_files:
            cmd.extend(["-i", f])

        # Với concat filter, thứ tự của các stream phải theo cặp: [v0][a0][v1][a1]...
        filter_parts = []
        for i in range(n):
            filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")
            filter_parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")

        concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(n))
        filter_parts.append(f"{concat_inputs}concat=n={n}:v=1:a=1[outv][outa]")

        filter_complex = " ; ".join(filter_parts)

        cmd.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[outv]",
                "-map",
                "[outa]",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                output_file,
            ]
        )

        print("Merging with command:")

        print(" ".join(cmd))
        subprocess.run(cmd, check=True)

        # Xóa các file tạm sau khi merge
        for f in std_files:
            try:
                os.remove(f)
            except Exception as e:
                print(f"Không xóa được {f}: {e}")

        return output_file

    def make_video_with_moviepy(self, images=[], captions=[]):
        if images is None:
            images = []
        if captions is None:
            captions = []
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        self.total_times = self.duration_per_image * len(images)

        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex
        file_name = f"{timestamp}_{unique_id}.mp4"

        output_file = os.path.join(UPLOAD_FOLDER, file_name)

        # Tạo progress bar cho toàn bộ quá trình
        total_steps = len(images) + 1  # Số lượng ảnh + 1 cho việc tạo audio
        with tqdm(total=total_steps, desc="Processing video", file=sys.stdout) as pbar:
            # Chạy make_audio song song với việc xử lý ảnh
            with concurrent.futures.ThreadPoolExecutor() as executor:
                audio_future = executor.submit(self.make_audio, captions)
                saved_images = []
                for image_url, caption in zip(images, captions):
                    processed_img = self.process_image(
                        image_url=image_url, caption=caption, is_get_path=True
                    )
                    saved_images.append(processed_img)
                    pbar.update(1)  # Cập nhật progress bar sau khi xử lý mỗi ảnh
                audio_path, temp_audio_path = (
                    audio_future.result()
                )  # đợi audio hoàn thành
                pbar.update(1)  # Cập nhật progress bar sau khi tạo audio

        image_clips = []
        for image_path in saved_images:
            clip = ImageClip(
                image_path, duration=self.duration_per_image
            )  # Mỗi ảnh hiển thị 5 giây
            clip = clip.fx(vfx.fadein, duration=1).fx(vfx.fadeout, duration=1)
            image_clips.append(clip)
        video_clips = image_clips
        final_video_clip = concatenate_videoclips(video_clips, method="compose")
        audio_clip = AudioFileClip(audio_path)
        final_video_clip = final_video_clip.set_audio(audio_clip)
        final_video_clip.write_videofile(output_file, fps=24, codec="libx264")

        os.remove(audio_path)
        os.remove(temp_audio_path)
        for image_path in saved_images:
            os.remove(image_path)

        return output_file

    def make_video(self, images=[], captions=[]):
        if images is None:
            images = []
        if captions is None:
            captions = []
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        self.total_times = self.duration_per_image * len(images)

        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex
        file_name = f"{timestamp}_{unique_id}.mp4"

        output_file = os.path.join(UPLOAD_FOLDER, file_name)

        self.container = av.open(output_file, mode="w", format="mp4")

        # TODO:
        # - libx264 là sử dụng CPU
        # - Cấu hình codec để tối ưu hóa chất lượng video
        # - Sử dụng GPU để tăng tốc độ render video
        # - Sử dụng codec khác để giảm dung lượng file
        # - NVIDIA : h264_nvenc, hevc_nvenc, av1_nvenc
        # - AMD : h264_amf, hevc_amf, h264_vaapi, hevc_vaapi
        # - Intel : h264_qsv, hevc_qsv
        self.stream = self.container.add_stream("libx264", rate=self.fps)

        self.stream.codec_context.options = {
            "preset": "fast",
            "tune": "zerolatency",
            "crf": "23",
            "profile": "high",
            "level": "4.2",
            "movflags": "+faststart",
        }

        self.stream.width, self.stream.height = self.video_size
        self.stream.pix_fmt = "yuv420p"

        self.audio_stream = self.container.add_stream("aac")
        self.audio_stream.codec_context.bit_rate = 32000
        self.audio_stream.codec_context.sample_rate = 44100
        self.audio_stream.codec_context.channels = 2
        self.audio_stream.codec_context.format = "fltp"

        # Tạo progress bar cho toàn bộ quá trình
        total_steps = len(images) + 1  # Số lượng ảnh + 1 cho việc tạo audio
        with tqdm(total=total_steps, desc="Processing video", file=sys.stdout) as pbar:
            # Chạy make_audio song song với việc xử lý ảnh
            with concurrent.futures.ThreadPoolExecutor() as executor:
                audio_future = executor.submit(self.make_audio, captions)
                saved_images = []
                for image_url, caption in zip(images, captions):
                    processed_img = self.process_image(
                        image_url=image_url, caption=caption
                    )
                    saved_images.append(processed_img)
                    pbar.update(1)  # Cập nhật progress bar sau khi xử lý mỗi ảnh
                audio_path, temp_audio_path = (
                    audio_future.result()
                )  # đợi audio hoàn thành
                pbar.update(1)  # Cập nhật progress bar sau khi tạo audio

            # Tạo progress bar cho việc tạo frame
            total_frames = len(saved_images) * self.total_frames
            with tqdm(
                total=total_frames, desc="Creating frames", file=sys.stdout
            ) as frame_pbar:
                for image in saved_images:
                    self.create_frame(image, frame_pbar)
                    del image
                    gc.collect()

        self.flush_encoder()

        video_duration = len(saved_images) * self.duration_per_image

        print("Đã Audio:", audio_path)

        self.add_audio(audio_path, video_duration)

        try:
            self.container.close()
        except Exception as e:
            print("Error closing self.container:", e)

        os.remove(audio_path)
        os.remove(temp_audio_path)

        del saved_images
        del audio_path
        gc.collect()

        file_url = f"{os.getenv('CURRENT_DOMAIN')}/{date_create}/files/{file_name}"
        return file_url

    def make_audio(self, captions):
        text = " ".join(captions)
        tts = gTTS(text=text, lang="ko")

        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex
        file_name = f"{timestamp}_{unique_id}.mp3"
        output_file = os.path.join(UPLOAD_FOLDER, file_name)

        temp_file_name = f"{timestamp}_{unique_id}_temp.mp3"
        temp_file = os.path.join(UPLOAD_FOLDER, temp_file_name)

        tts.save(temp_file)

        audio = AudioSegment.from_file(temp_file, format="mp3")
        current_duration_s = len(audio) / 1000.0

        print("Thời lượng audio hiện tại:", current_duration_s, "giây")
        print("Thời lượng video cần tạo:", self.total_times, "giây")

        if abs(current_duration_s - self.total_times) < 0.1:
            print("Thời lượng đã gần khớp, chỉ copy file.")
            subprocess.run(["ffmpeg", "-y", "-i", temp_file, output_file], check=True)
            return output_file, temp_file

        # Tính hệ số tempo cần thiết
        # Với atempo, thời lượng mới = current_duration / tempo, nên để có new_duration = target_duration_s,
        # cần: tempo = current_duration / target_duration_s.
        factor = current_duration_s / self.total_times
        print(f"Hệ số tempo ban đầu: {factor:.6f}")

        # FFmpeg atempo filter chỉ chấp nhận giá trị trong khoảng [0.5, 2.0]
        # Nếu factor nằm ngoài khoảng này, chúng ta cần chia nhỏ thành các hệ số hợp lệ.
        factors = []
        temp_factor = factor
        while temp_factor > 2.0:
            factors.append(2.0)
            temp_factor /= 2.0
        while temp_factor < 0.5:
            factors.append(0.5)
            temp_factor /= 0.5
        factors.append(temp_factor)

        # Tạo chuỗi filter atempo bằng cách ghép các hệ số lại, ví dụ: "atempo=2.0,atempo=1.1"
        filter_chain = ",".join(f"atempo={f:.6f}" for f in factors)

        print("Chuỗi filter atempo:", filter_chain)

        # Gọi FFmpeg để thay đổi tempo của audio
        cmd = [
            "ffmpeg",
            "-y",  # ghi đè file output nếu tồn tại
            "-i",
            temp_file,
            "-filter:a",
            filter_chain,
            output_file,
        ]

        subprocess.run(cmd, check=True)
        print("Đã xuất file audio với tempo điều chỉnh:", output_file)

        return output_file, temp_file

    def get_image_from_url(self, image_url):
        response = requests.get(image_url)
        image = Image.open(io.BytesIO(response.content))
        return image

    def process_image(self, image_url, caption, is_get_path=False):
        image = self.get_image_from_url(image_url)

        video_width, video_height = self.video_size
        video_ratio = video_width / video_height

        if image.height > image.width:
            # Ảnh portrait: crop theo chiều dọc từ trung tâm
            # Sử dụng toàn bộ chiều rộng, tính chiều cao crop dựa trên video_ratio
            crop_height = int(image.width / video_ratio)
            top = (image.height - crop_height) // 2
            bottom = top + crop_height
            image = image.crop((0, top, image.width, bottom))
            # Resize về kích thước video
            image = image.resize(self.video_size, Image.LANCZOS)
        else:
            # Ảnh landscape hoặc square: thêm khoảng đen (letterbox) ở trên và dưới
            # Resize ảnh sao cho chiều rộng bằng video_width
            new_width = video_width
            new_height = int(image.height * (video_width / image.width))
            resized_image = image.resize((new_width, new_height), Image.LANCZOS)
            # Tạo nền đen với kích thước video
            background = Image.new("RGBA", self.video_size, (0, 0, 0, 255))
            # Tính vị trí dán sao cho ảnh được canh giữa theo chiều dọc
            top = (video_height - new_height) // 2
            background.paste(resized_image, (0, top))
            image = background

        draw = ImageDraw.Draw(image)

        # Chèn caption lên frame sử dụng PIL

        margin = (50, 50, 50, 50)

        # Tính vùng giới hạn chữ
        left_margin, top_margin, right_margin, bottom_margin = margin
        max_width = image.width - left_margin - right_margin

        lines = wrap_text_by_pixel(draw, caption, self.font, max_width)
        wrapped_text = "\n".join(lines)

        # Vẽ multiline text tại vị trí (left_margin, top_margin)
        draw.multiline_text(
            (left_margin, top_margin),
            wrapped_text,
            font=self.font,
            fill=(255, 255, 255),
            stroke_width=10,
            stroke_fill=(0, 0, 0),
        )

        if image_url.lower().endswith(".jpg") or image_url.lower().endswith(".jpeg"):
            image = image.convert("RGB")

        if is_get_path:
            timestamp = int(time.time())
            unique_id = uuid.uuid4().hex
            extension = image_url.split(".")[-1]

            image_name = f"{timestamp}_{unique_id}.{extension}"
            output_file = os.path.join(UPLOAD_FOLDER, image_name)
            image.save(output_file)
            return output_file

        return image

    def create_frame(self, image, pbar):
        """
        Tạo các frame cho 1 ảnh bằng cách xử lý song song dữ liệu frame,
        sau đó encode và đưa vào container.
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Map các chỉ số frame (0 đến total_frames-1) qua hàm compute_frame_data
            frames_data = list(
                executor.map(
                    lambda idx: self.compute_frame_data(idx, image),
                    range(self.total_frames),
                )
            )
        # Encode các frame theo thứ tự
        for final_frame in frames_data:
            video_frame = av.VideoFrame.from_ndarray(final_frame, format="rgb24")
            for packet in self.stream.encode(video_frame):
                self.container.mux(packet)
            pbar.update(1)  # Cập nhật progress bar
        return image

    def compute_frame_data(self, frame_idx, image):
        """
        Tính toán dữ liệu cho một frame dựa trên chỉ số frame.
        Áp dụng hiệu ứng fade in/out bằng cách nhân hệ số alpha.
        """
        if frame_idx < self.fps:
            alpha = frame_idx / self.fps
        elif frame_idx > self.total_frames - self.fps:
            alpha = (self.total_frames - frame_idx) / self.fps
        else:
            alpha = 1.0

        frame_np = np.array(image).astype(np.float32) * alpha
        frame_np = np.clip(frame_np, 0, 255).astype(np.uint8)
        pil_frame = Image.fromarray(frame_np)
        final_frame = np.array(pil_frame)[..., :3]  # Loại bỏ kênh alpha nếu có
        return final_frame

    def add_audio(self, audio_path, video_duration):
        """
        Thêm audio vào container, ép lại giá trị PTS cho audio frame để đồng bộ thời gian.
        """
        try:
            audio_file = av.open(audio_path, mode="r")
        except av.AVError as e:
            print(f"Error opening audio file: {e}")
            return None
        audio_in_stream = audio_file.streams.audio[0]

        print(f"Audio file sample rate: {audio_in_stream.rate}")
        print(f"Audio file channels: {audio_in_stream.channels}")
        print(
            f"Audio file format: {audio_in_stream.format.name if audio_in_stream.format else 'unknown'}"
        )

        self.audio_stream.time_base = audio_in_stream.time_base
        self.audio_stream.codec_context.sample_rate = audio_in_stream.rate
        self.audio_stream.codec_context.channels = audio_in_stream.channels
        self.audio_stream.codec_context.format = audio_in_stream.format

        print(
            f"Audio stream sample rate: {self.audio_stream.codec_context.sample_rate}"
        )
        print(f"Audio stream channels: {self.audio_stream.codec_context.channels}")
        print(f"Audio stream format: {self.audio_stream.codec_context.format}")

        sample_rate = audio_in_stream.rate  # ví dụ: 44100
        channels = audio_in_stream.channels  # ví dụ: 2

        audio_pts = 0
        print("Đang xử lý audio gốc...")
        # Đọc và mã hóa các frame audio từ file gốc
        for frame in audio_file.decode(audio_in_stream):
            print(f"Audio frame PTS trước: {frame.pts}, samples: {frame.samples}")
            frame.pts = audio_pts
            print(f"Audio frame PTS sau gán: {frame.pts}")
            audio_pts += frame.samples
            for packet in self.audio_stream.encode(frame):
                print(f"Audio packet PTS: {packet.pts}")  # In PTS của audio packet
                packet.stream = self.audio_stream
                try:
                    self.container.mux(packet)
                except Exception as e:
                    print(f"Lỗi khi mux packet: {e}")
                    # Có thể in thêm thông tin của packet để debug
                    print(
                        f"Packet info: pts={packet.pts}, dts={packet.dts}, duration={packet.duration}"
                    )
                    raise

        original_duration = audio_pts / sample_rate
        print("Thời lượng audio gốc:", original_duration, "giây")

        # Tính thời lượng audio hiện tại
        if video_duration > original_duration:
            missing_duration = video_duration - original_duration
            total_missing_samples = int(missing_duration * sample_rate)
            print(
                "Pad thêm silence cho",
                missing_duration,
                "giây (tương đương",
                total_missing_samples,
                "samples)",
            )
            chunk_size = 1024  # số mẫu mỗi lần pad
            while total_missing_samples > 0:
                current_chunk = min(chunk_size, total_missing_samples)
                # Tạo mảng numpy chứa âm thanh im lặng (0)
                silence_data = np.zeros((channels, current_chunk), dtype=np.float32)
                # Lưu ý: layout phải khớp với số kênh, ví dụ với 2 kênh dùng "stereo"
                silent_frame = av.AudioFrame.from_ndarray(silence_data, layout="stereo")
                silent_frame.sample_rate = sample_rate
                silent_frame.pts = audio_pts
                audio_pts += current_chunk
                for packet in self.audio_stream.encode(silent_frame):
                    self.container.mux(packet)
                total_missing_samples -= current_chunk

        # Flush encoder audio
        for packet in self.audio_stream.encode(None):
            self.container.mux(packet)

    def flush_encoder(self):
        for packet in self.stream.encode():
            self.container.mux(packet)
