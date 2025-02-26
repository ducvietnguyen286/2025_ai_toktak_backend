import gc
import io
import time
import uuid
import av
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
from gtts import gTTS
import concurrent.futures

import requests
from tqdm import tqdm

from app.makers.images import wrap_text_by_pixel

FONT_FOLDER = os.path.join(os.getcwd(), "app/makers/fonts")


class MakerVideo:
    def __init__(self):
        # Cấu hình
        self.video_size = (1080, 1920)  # (width, height)
        self.duration_per_image = 5  # giây
        self.fps = 25
        self.total_frames = self.duration_per_image * self.fps
        self.font = None
        try:
            self.font = ImageFont.truetype(f"{FONT_FOLDER}/dotum.ttc", 80)
        except IOError:
            print(f"Không tìm thấy font dotum.ttc, sử dụng font mặc định.")
            self.font = ImageFont.load_default()

    def make_video(self, images=[], captions=[]):
        if images is None:
            images = []
        if captions is None:
            captions = []
        UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")

        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex
        file_name = f"{timestamp}_{unique_id}.mp4"

        output_file = os.path.join(UPLOAD_FOLDER, file_name)

        container = av.open(output_file, mode="w")

        # TODO:
        # - libx264 là sử dụng CPU
        # - Cấu hình codec để tối ưu hóa chất lượng video
        # - Sử dụng GPU để tăng tốc độ render video
        # - Sử dụng codec khác để giảm dung lượng file
        # - NVIDIA : h264_nvenc, hevc_nvenc, av1_nvenc
        # - AMD : h264_amf, hevc_amf, h264_vaapi, hevc_vaapi
        # - Intel : h264_qsv, hevc_qsv
        stream = container.add_stream("libx264", rate=self.fps)

        stream.codec_context.options = {
            "preset": "fast",
            "tune": "zerolatency",
            "crf": "23",
            "profile": "high",
            "level": "4.2",
            "movflags": "+faststart",
        }

        stream.width, stream.height = self.video_size
        stream.pix_fmt = "yuv420p"

        audio_stream = container.add_stream("aac")
        audio_stream.codec_context.bit_rate = 32000
        audio_stream.codec_context.sample_rate = 44100
        audio_stream.codec_context.channels = 2

        # Tạo progress bar cho toàn bộ quá trình
        total_steps = len(images) + 1  # Số lượng ảnh + 1 cho việc tạo audio
        with tqdm(total=total_steps, desc="Processing video") as pbar:
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
                audio_path = audio_future.result()  # đợi audio hoàn thành
                pbar.update(1)  # Cập nhật progress bar sau khi tạo audio

            # Tạo progress bar cho việc tạo frame
            total_frames = len(saved_images) * self.total_frames
            with tqdm(total=total_frames, desc="Creating frames") as frame_pbar:
                for image in saved_images:
                    self.create_frame(container, stream, image, frame_pbar)
                    del image
                    gc.collect()

        self.flush_encoder(container, stream)

        self.add_audio(container, audio_stream, audio_path)

        container.close()

        del saved_images
        del audio_path
        os.remove(audio_path)
        gc.collect()

        file_url = f"{os.getenv('CURRENT_DOMAIN')}/files/{file_name}"
        return file_url

    def make_audio(self, captions):
        text = " ".join(captions)
        tts = gTTS(text=text, lang="ko")
        UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex
        file_name = f"{timestamp}_{unique_id}.mp3"
        output_file = os.path.join(UPLOAD_FOLDER, file_name)
        tts.save(output_file)
        return output_file

    def get_image_from_url(self, image_url):
        response = requests.get(image_url)
        image = Image.open(io.BytesIO(response.content))
        return image

    def process_image(self, image_url, caption):
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

        return image

    def create_frame(self, container, stream, image, pbar):
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
            for packet in stream.encode(video_frame):
                container.mux(packet)
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

    def add_audio(self, container, audio_stream, audio_path):
        """
        Thêm audio vào container, ép lại giá trị PTS cho audio frame để đồng bộ thời gian.
        """
        audio_file = av.open(audio_path)
        audio_in_stream = audio_file.streams.audio[0]
        # Đồng bộ time_base của stream audio container với input
        audio_stream.time_base = audio_in_stream.time_base

        audio_pts = 0
        for frame in audio_file.decode(audio_in_stream):
            # Ép luôn đặt lại PTS cho frame
            frame.pts = audio_pts
            audio_pts += frame.samples
            for packet in audio_stream.encode(frame):
                container.mux(packet)
        # Flush encoder audio
        for packet in audio_stream.encode(None):
            container.mux(packet)

    def flush_encoder(self, container, stream):
        for packet in stream.encode():
            container.mux(packet)
