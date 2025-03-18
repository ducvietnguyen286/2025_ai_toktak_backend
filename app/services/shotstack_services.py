import requests
import json
import os
import random
from app.models.video_create import VideoCreate
from app.models.video_viral import VideoViral
from app.models.captions import Caption
from app.models.setting import Setting
import datetime
from app.lib.logger import log_make_video_message
import uuid
from app.extensions import redis_client
from pydub import AudioSegment
import subprocess
from app.services.request_log import RequestLogService
import base64

import srt

# import ffmpeg
import textwrap
import re  # Thêm thư viện để xử lý dấu câu


class ShotStackService:

    @staticmethod
    def create_video_from_images_v2(
        post_id, voice_google, origin_caption, images_url, images_slider_url, captions
    ):

        config = ShotStackService.get_settings()
        SHOTSTACK_API_KEY = config["SHOTSTACK_API_KEY"]
        SHOTSTACK_URL = config["SHOTSTACK_URL"]
        is_ai_image = config["SHOTSTACK_AI_IMAGE"]
        MUSIC_BACKGROUP_VOLUMN = float(config["MUSIC_BACKGROUP_VOLUMN"])
        video_size_json = config["VIDEO_SIZE"] or '{"width": 1200, "height": 800}'
        video_size = json.loads(video_size_json)

        key_redis = f"caption_videos_default"
        progress_json = redis_client.get(key_redis)

        if progress_json:
            caption_videos_default = json.loads(progress_json) if progress_json else {}
        else:

            caption_videos_default = ShotStackService.get_caption_defaults()
            redis_client.set(key_redis, json.dumps(caption_videos_default))

        # prompt fake
        prompts = [
            "Slowly zoom in and out for a dramatic effect.",
            "Add a soft fade transition between images.",
            "Use a pan effect to make the image feel dynamic.",
            "Apply a sepia filter for a vintage look.",
            "Zoom in on the center of the image for emphasis.",
        ]

        # Kiểm tra nếu danh sách prompts ít hơn số lượng hình ảnh
        if len(prompts) < len(images_url):
            # Lặp lại prompts để đủ số lượng ảnh
            prompts = (
                prompts * (len(images_url) // len(prompts))
                + prompts[: len(images_url) % len(prompts)]
            )

        date_create = datetime.datetime.now().strftime("%Y_%m_%d")
        dir_path = f"static/voice/gtts_voice/{date_create}/{post_id}"
        current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"

        # Chọn giọng nói ngẫu nhiên
        korean_voice = get_korean_voice(voice_google)

        mp3_file, audio_duration = text_to_speech_kr(
            korean_voice, origin_caption, dir_path, config
        )

        video_urls =  ShotStackService.get_random_videos(2)
        
        audio_urls = get_random_audio(1)
         
        first_viral_detail = video_urls[0] or []
        first_duration = float(first_viral_detail["duration"] or 0)

        new_image_sliders = distribute_images_over_audio(
            images_slider_url, audio_duration, first_duration
        )
        clips_data = create_combined_clips_v2(
            new_image_sliders,
            video_urls,
            config,
            caption_videos_default,
        )

        file_caption = generate_srt(
            origin_caption, mp3_file, f"{dir_path}/test.srt", first_duration
        )

        clips_caption = {
            "asset": {
                "type": "caption",
                "src": file_caption,
                "font": {
                    "lineHeight": 1,
                    "family": "JalnanGothic",
                    "color": "#ffffff",
                    "size": 46,
                    "stroke": "#000000",
                    "strokeWidth": 1.5,
                },
            },
            "start": 0,
            "length": "end",
        }

        mp3_file = mp3_file.replace("static/", "")
        voice_url = f"{current_domain}/{mp3_file}"
        clips_audio_sub = {
            "asset": {
                "type": "audio",
                "src": voice_url,
                "volume": 1,
            },
            "start": clips_data["intro_length"],
            "length": "end",
        }

        payload = {
            "timeline": {
                "fonts": [
                    {
                        "src": "http://admin.lang.canvasee.com/fonts/Jalnan2/Jalnan2TTF.ttf"
                    },
                    {"src": "http://admin.lang.canvasee.com/fonts/Jalnan2/Jalnan2.otf"},
                    {
                        "src": "http://admin.lang.canvasee.com/fonts/Jalnan2/JalnanGothicTTF.ttf"
                    },
                    {
                        "src": "http://admin.lang.canvasee.com/fonts/Jalnan2/JalnanGothic.otf"
                    },
                ],
                "background": "#FFFFFF",
                "tracks": [
                    {
                        "clips": [
                            {
                                "asset": {
                                    "type": "image",
                                    "src": "https://admin.lang.canvasee.com/img/watermarker6.png",
                                },
                                "start": 0,
                                "length": 3,
                                "fit": "none",
                                "position": "left",
                                "offset": {"x": 0.05, "y": 0},
                            }
                        ]
                    },
                    {
                        "clips": [
                            {
                                "asset": {
                                    "type": "image",
                                    "src": "https://admin.lang.canvasee.com/img/watermarker6.png",
                                },
                                "start": 3,
                                "length": "end",
                                "fit": "none",
                                "position": "bottomRight",
                                "offset": {"x": -0.05, "y": 0.22},
                            }
                        ]
                    },
                    {"clips": [clips_caption]},
                    {"clips": [clips_audio_sub]},
                    clips_data["clips"],
                    {
                        "clips": [
                            {
                                "asset": {
                                    "type": "audio",
                                    "src": audio_urls[0]['video_url'],
                                    "effect": "fadeOut",
                                    "volume": MUSIC_BACKGROUP_VOLUMN,
                                },
                                "start": 0,
                                "length": "end",
                            }
                        ]
                    },
                ],
            },
            "output": {
                "format": "mp4",
                "quality": "veryhigh",
                # "resolution": "hd",
                # "aspectRatio": "16:9",
                "size": {"width": video_size["width"], "height": video_size["height"]},
                # "size": video_size,
            },
            "callback": f"{current_domain}/api/v1/video_maker/shotstack_webhook",
        }

        log_make_video_message(
            f"++++++++++++++++++++++++++++++payload_dumps:\n\n {json.dumps(payload)} \n\n"
        )

        # Header với API Key
        headers = {"x-api-key": SHOTSTACK_API_KEY, "Content-Type": "application/json"}

        try:
            # Gửi yêu cầu POST đến Shotstack API
            response = requests.post(
                SHOTSTACK_URL, headers=headers, data=json.dumps(payload)
            )

            # Kiểm tra trạng thái phản hồi
            # A new resource was created successfully.
            if response.status_code == 201:
                result = response.json()
                result["status_code"] = 200

                log_make_video_message(f"render_id : : {result}")

                RequestLogService.create_request_log(
                    post_id=post_id,
                    ai_type="shotstack",
                    request=json.dumps(payload),
                    response=json.dumps(result),
                    prompt_tokens=0,
                    prompt_cache_tokens=0,
                    prompt_audio_tokens=0,
                    completion_tokens=0,
                    completion_reasoning_tokens=0,
                    completion_audio_tokens=0,
                    completion_accepted_prediction_tokens=0,
                    completion_rejected_prediction_tokens=0,
                    total_tokens=0,
                    status=1,
                )

                return result
            else:
                result = response.json()
                log_make_video_message("create video Failed :{0}".format(str(result)))
                return {
                    "message": "AI 영상 서버와 연결할 수 없어요.",
                    "status_code": response.status_code,
                }

        except Exception as e:
            log_make_video_message(
                "create_video_from_images : Exception: {0}".format(str(e))
            )
            RequestLogService.create_request_log(
                post_id=post_id,
                ai_type="shotstack",
                request=json.dumps(payload),
                response=str(e),
                prompt_tokens=0,
                prompt_cache_tokens=0,
                prompt_audio_tokens=0,
                completion_tokens=0,
                completion_reasoning_tokens=0,
                completion_audio_tokens=0,
                completion_accepted_prediction_tokens=0,
                completion_rejected_prediction_tokens=0,
                total_tokens=0,
                status=2,
            )

            return {
                "message": str(e),
                "status_code": 500,
            }

    @staticmethod
    def get_settings():
        settings = Setting.query.all()
        settings_dict = {
            setting.setting_name: setting.setting_value for setting in settings
        }
        return settings_dict

    @staticmethod
    def get_caption_defaults():
        captions = Caption.query.filter_by(status=1).all()
        return [
            {"content": caption.content, "type_content": caption.type_content}
            for caption in captions
        ]

    def filter_content_by_type(captions_list, type_content):
        filtered = [
            item["content"]
            for item in captions_list
            if item["type_content"] == f"{type_content}"
        ]
        if filtered:
            return random.choice(filtered)
        return ""
    @staticmethod
    def get_random_videos(limit=2):
        try:

            key_redis = "viral_video_redis_video"
            progress_json = redis_client.get(key_redis)

            if progress_json:
                video_viral_s = json.loads(progress_json) if progress_json else {}
            else:
                videos = VideoViral.query.filter_by(status=1, type="video").all()
                video_data = [
                    {
                        "video_name": video_detail.video_name,
                        "video_url": video_detail.video_url,
                        "duration": video_detail.duration,
                    }
                    for video_detail in videos
                ]
                video_viral_s = video_data
                redis_client.set(key_redis, json.dumps(video_viral_s))

            random_items = random.sample(video_viral_s, limit)
            return random_items

        except Exception as e:
            log_make_video_message(f"get_random_videos: {str(e)}")
            return []



def create_combined_clips_v2(
    images_slider_url,
    video_urls,
    config=None,
    caption_videos_default=None,
):
    first_viral_detail = video_urls[0] or []
    last_viral_detail = video_urls[1] or []
    # Chọn 2 URL khác nhau một cách ngẫu nhiên
    first_viral_url = first_viral_detail["video_url"]
    first_duration = float(first_viral_detail["duration"] or 0)

    clips = []
    current_start = 0
    intro_length = first_duration

    clips.append(
        {
            "asset": {"type": "video", "src": first_viral_url},
            "start": current_start,
            "length": intro_length,
        }
    )
    first_caption_videos_default = ShotStackService.filter_content_by_type(
        caption_videos_default, 1
    )

    clip_detail = create_header_text(first_caption_videos_default, current_start, 2)
    clips.append(clip_detail)

    current_start += intro_length

    time_show_image = 5

    SHOTSTACK_IMAGE_EFFECTS = config["SHOTSTACK_IMAGE_EFFECTS"] or ""
    if SHOTSTACK_IMAGE_EFFECTS == "random":
        effects = [
            "zoomIn",
            "zoomOut",
            "slideLeft",
            "slideRight",
            "slideUp",
            "slideDown",
        ]
    else:
        effects = [
            SHOTSTACK_IMAGE_EFFECTS,
        ]

    last_caption_videos_default = ShotStackService.filter_content_by_type(
        caption_videos_default, 4
    )

    end_time = current_start
    for j_index, image_slider_detail in enumerate(images_slider_url):
        url = image_slider_detail["url"]
        start_time = image_slider_detail["start_time"]
        end_time = image_slider_detail["end_time"]
        length = image_slider_detail["length"]
        random_effect = random.choice(effects)
        start_slider_time = start_time

        clip_detail = {
            "asset": {"type": "image", "src": url},
            "start": start_slider_time,
            "length": length,
        }

        if random_effect != "":
            clip_detail["effect"] = random_effect
        clips.append(clip_detail)

        if j_index == 0:
            first_caption_image_default = ShotStackService.filter_content_by_type(
                caption_videos_default, 2
            )
            clip_detail = create_header_text(
                first_caption_image_default, start_slider_time, 2
            )
            clips.append(clip_detail)
        elif j_index == 2:
            # When 3rd image start, display for 2 sec
            first_caption_image_default = ShotStackService.filter_content_by_type(
                caption_videos_default, 3
            )
            clip_detail = create_header_text(
                first_caption_image_default, start_slider_time, 2
            )
            clips.append(clip_detail)

        elif j_index == 4:
            # When 5th image start, display for 2 sec & When start last hooking video, display for 2 sec in the middle of screen until end of video
            clip_detail = create_header_text(
                last_caption_videos_default, start_slider_time, 2
            )
            clips.append(clip_detail)
        # lấy thời gian cuối
        current_start = end_time

    last_viral_url = last_viral_detail["video_url"]
    last_duration = float(last_viral_detail["duration"] or 0)
    clips.append(
        {
            "asset": {"type": "video", "src": last_viral_url},
            "start": current_start,
            "length": last_duration,
        }
    )

    clip_detail = create_header_text(
        last_caption_videos_default, current_start, last_duration
    )
    clips.append(clip_detail)

    # Kết hợp hai danh sách clip lại
    combined_clips = clips
    return {"intro_length": intro_length, "clips": {"clips": combined_clips}}




def get_random_audio(limit=1):
    try:

        key_redis = "viral_video_redis_audio"
        progress_json = redis_client.get(key_redis)

        if progress_json:
            video_viral_s = json.loads(progress_json) if progress_json else {}
        else:
            videos = VideoViral.query.filter_by(status=1, type="mp3").all()
            video_data = [
                {
                    "video_name": video_detail.video_name,
                    "video_url": video_detail.video_url,
                    "duration": video_detail.duration,
                }
                for video_detail in videos
            ]
            video_viral_s = video_data
            redis_client.set(key_redis, json.dumps(video_viral_s))

        random_items = random.sample(video_viral_s, limit)
        return random_items

    except Exception as e:
        log_make_video_message(f"get_random_audio: {str(e)}")
        return []


def parse_srt_to_html_assets(url_path_srt: str, start_time):
    """
    Đọc file SRT từ đường dẫn url_path_srt và chuyển đổi từng caption
    thành asset kiểu "html" với định dạng CSS tùy chỉnh.

    :param url_path_srt: Đường dẫn tới file SRT (ví dụ: 'assets/transcript.srt')
    :return: Danh sách các asset (dạng dictionary) cho caption
    """

    url_path_srt = url_path_srt.replace("http://118.70.171.129:6001", "static")

    # Đọc file SRT với encoding utf-8
    with open(url_path_srt, "r", encoding="utf-8") as f:
        srt_content = f.read()

    # Phân tích nội dung SRT thành danh sách đối tượng caption
    captions = list(srt.parse(srt_content))
    html_assets = []

    for caption in captions:
        # Chuyển nội dung caption: thay các ký tự xuống dòng thành <br>
        caption_text = caption.content.replace("\n", "<br>")

        # Tạo HTML cho asset với style tùy chỉnh
        html_text = f"<div  class='large-div'>{caption_text}</div>"

        # "asset": {
        #     "type": "html",
        #     "html": "<div style='font-size: 60px; color: #000000; padding: 10px; text-align: center;'>Wait a minute.</div>",
        #     "css": "div { font-weight: bold; font-family: 'JalnanGothic', sans-serif; border-radius: 40px; }",
        #     "width": 500,
        #     "height": 200,
        #     "background": "#FFD600",
        #     "position": "center",
        # },

        # "start": caption.start.total_seconds() + 0.01,
        # "length": (caption.end - caption.start).total_seconds(),
        start_play = caption.start.total_seconds() + 0.01 + start_time
        length_seconds = (caption.end - caption.start).total_seconds()
        asset_dict = {
            "asset": {
                "type": "html",
                "html": "<div style='font-size: 40px; color: #080000; text-align: center;  padding: 10px 20px; display: inline-block; border-radius: 20px;'>Nội dung của bạn</div>",
                "css": "div {   background: #FFD600; border-radius: 20px;  margin-bottom : 10px;  margin-top : 10px;}",
                "width": 500,
                "height": 400,
                "background": "#80ffffff",
                # "html": html_text,
                # "css": '.large-div { background-color: #030303;color: #ffffff;font-family: "JalnanGothic", sans-serif;      font-size: 60px;  text-align: center;padding: 40px;border-radius: 40px;box-shadow: 0 0 15px rgba(0, 0, 0, 0.2);       height : 400;   }',
            },
            "start": start_play,
            "length": length_seconds,
            "position": "bottom",
            "offset": {"x": 0, "y": 0.08},
        }
        start_time = start_time + 2
        html_assets.append(asset_dict)
    return html_assets


def create_header_text(caption_text, start=0, length=0, add_time=0.01):
    clip_detail = {
        "asset": {
            "type": "text",
            "text": caption_text,
            "font": {
                "family": "JalnanGothic",
                "color": "#ffffff",
                "opacity": 0.8,
                "size": 46,
                "lineHeight": 0.85,
            },
            # "background": {
            #     "color": "#000000",
            #     "borderRadius": 20,
            #     "padding": 0,
            #     "opacity": 0.6,
            # },
            "stroke": {"color": "#000000", "width": 1.5},
            "height": 110,
            "width": 600,
        },
        "start": start + add_time,
        "length": length,
        "position": "top",
        "offset": {"x": 0, "y": -0.01},
    }
    return clip_detail


def text_to_speech_kr(korean_voice, text, disk_path="output", config=None):
    """
    Gọi Google Text-to-Speech API để tạo file MP3 và lấy thời gian audio bằng ffmpeg.

    :param text: Văn bản cần chuyển đổi
    :param disk_path: Thư mục lưu file MP3
    :param config: Dictionary chứa API Key và URL
    :return: Tuple (đường dẫn file MP3, thời gian audio)
    """
    try:
        if not config:
            log_make_video_message("Lỗi: Config không được truyền vào.")
            return "", 0.0

        GOOGLE_API_SPEED = float(config.get("GOOGLE_API_SPEED", 1))
        api_key = config.get("GOOGLE_API_TEXT_TO_SPEECH", "")
        api_url = config.get(
            "GOOGLE_API_TEXT_TO_URL",
            "https://texttospeech.googleapis.com/v1/text:synthesize",
        )

        if not api_key or not api_url:
            log_make_video_message("Lỗi: API Key hoặc API URL chưa được thiết lập.")
            return "", 0.0

        if not text:
            log_make_video_message("Lỗi: Vui lòng nhập văn bản.")
            return "", 0.0

        os.makedirs(disk_path, exist_ok=True)
        output_file = os.path.join(disk_path, "output.mp3")

        # Payload gửi lên Google API
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "ko-KR",
                "name": korean_voice["name"],
                "ssmlGender": korean_voice["ssmlGender"],
            },
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": GOOGLE_API_SPEED},
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{api_url}?key={api_key}", json=payload, headers=headers
        )

        if response.status_code != 200:
            log_make_video_message(f"Lỗi từ Google API: {response.text}")
            return "", 0.0

        response_json = response.json()

        if "audioContent" not in response_json:
            log_make_video_message("Lỗi: Không nhận được dữ liệu âm thanh từ API.")
            return "", 0.0

        # Giải mã Base64 và lưu file MP3
        audio_content = base64.b64decode(response_json["audioContent"])
        with open(output_file, "wb") as audio_file:
            audio_file.write(audio_content)

        # Lấy thời gian audio bằng ffmpeg
        audio_duration = get_audio_duration(output_file)

        log_make_video_message(
            f"Đã tạo file âm thanh ({korean_voice['name']}): {output_file} (Thời gian: {audio_duration:.2f}s)"
        )
        return output_file, audio_duration

    except Exception as e:
        log_make_video_message(f"Exception: {str(e)}")
        return "", 0.0


def generate_caption_from_audio(
    audio_file, audio_duration, disk_path, start_time=0.0, config=None
):
    """
    Tạo file caption (.srt) từ file MP3 đã tạo.

    :param audio_file: Đường dẫn file MP3 đầu vào
    :param audio_duration: Thời gian của file MP3 (lấy từ ffmpeg)
    :param disk_path: Thư mục lưu file SRT
    :param start_time: Thời gian bắt đầu caption (tính bằng giây)
    :return: URL của file SRT hoặc thông báo lỗi
    """
    try:
        output_caption_file = os.path.join(disk_path, "output.srt")
        os.makedirs(disk_path, exist_ok=True)

        if not os.path.exists(audio_file):
            log_make_video_message("Lỗi: File âm thanh không tồn tại.")
            return ""

        transcript = google_speech_to_text(audio_file, config)

        if not transcript:
            log_make_video_message("Lỗi: Không thể nhận diện giọng nói.")
            return ""

        words = transcript.split()
        captions = []
        temp_caption = ""

        # Chia văn bản thành từng đoạn khoảng 20 ký tự
        for word in words:
            if len(temp_caption) + len(word) + 1 > 20:
                captions.append(temp_caption)
                temp_caption = word
            else:
                temp_caption += " " + word if temp_caption else word

        if temp_caption:
            captions.append(temp_caption)

        # Tính thời lượng mỗi caption
        caption_duration = audio_duration / len(captions) if captions else 0

        with open(output_caption_file, "w", encoding="utf-8") as f:
            current_time = start_time
            for i, caption in enumerate(captions):
                start_timestamp = format_time_caption(current_time)
                end_time = current_time + caption_duration
                end_timestamp = format_time_caption(end_time)

                # Ghi vào file SRT
                f.write(f"{start_timestamp} --> {end_timestamp}\n")
                f.write(f"{caption}\n\n")

                # Cập nhật thời gian bắt đầu cho caption tiếp theo (+0.01 giây)
                current_time = end_time + 0.01

        log_make_video_message(f"Đã tạo file caption: {output_caption_file}")

        # Chuyển đường dẫn thành URL để trả về
        current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
        output_caption_file = output_caption_file.replace("static/", "").replace(
            "\\", "/"
        )
        file_url = f"{current_domain}/{output_caption_file}"
        return file_url

    except Exception as e:
        log_make_video_message(f"Exception: {str(e)}")
        return ""


def google_speech_to_text(audio_file, config=None):
    """
    Sử dụng Google Speech-to-Text để chuyển file âm thanh thành văn bản.
    :param audio_file: File MP3 đầu vào
    :param config: Dictionary chứa API Key
    :return: Văn bản nhận diện được
    """
    try:
        # Lấy API Key từ config
        api_key = config.get("GOOGLE_API_TEXT_TO_SPEECH", "")
        api_url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"

        if not api_key:
            log_make_video_message("Lỗi: API Key chưa được thiết lập.")
            return ""

        # Chuyển file MP3 sang FLAC (Google Speech-to-Text tối ưu cho FLAC)
        flac_file = audio_file.replace(".mp3", ".flac")
        os.system(f"ffmpeg -i {audio_file} -ac 1 -ar 16000 {flac_file} -y")

        # Đọc file FLAC dạng base64
        with open(flac_file, "rb") as f:
            audio_content = base64.b64encode(f.read()).decode("utf-8")

        # Gửi request đến Google API
        payload = {
            "config": {
                "encoding": "FLAC",
                "sampleRateHertz": 16000,
                "languageCode": "ko-KR",
            },
            "audio": {"content": audio_content},
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(api_url, json=payload, headers=headers)

        # Xóa file FLAC sau khi gửi request
        try:
            os.remove(flac_file)
        except Exception as e:
            log_make_video_message(f"Lỗi khi xóa file FLAC: {str(e)}")

        if response.status_code != 200:
            log_make_video_message(f"Lỗi từ Google Speech API: {response.text}")
            return ""

        response_json = response.json()

        # Lấy transcript từ API
        transcript = " ".join(
            [
                alt["transcript"]
                for res in response_json.get("results", [])
                for alt in res.get("alternatives", [])
            ]
        )

        return transcript.strip()

    except Exception as e:
        log_make_video_message(f"Exception: {str(e)}")
        return ""


def get_korean_voice(index):
    korean_voices = [
        {
            "index": 1,
            "type": "Standard",
            "name": "ko-KR-Standard-C",
            "ssmlGender": "MALE",
        },
        {
            "index": 2,
            "type": "Standard",
            "name": "ko-KR-Standard-D",
            "ssmlGender": "MALE",
        },
        {
            "index": 3,
            "type": "Standard",
            "name": "ko-KR-Standard-A",
            "ssmlGender": "FEMALE",
        },
        {
            "index": 4,
            "type": "Standard",
            "name": "ko-KR-Standard-B",
            "ssmlGender": "FEMALE",
        },
        {
            "index": 5,
            "type": "Premium",
            "name": "ko-KR-Chirp3-HD-Aoede",
            "ssmlGender": "FEMALE",
        },
        {
            "index": 6,
            "type": "Premium",
            "name": "ko-KR-Chirp3-HD-Charon",
            "ssmlGender": "MALE",
        },
        {
            "index": 7,
            "type": "Premium",
            "name": "ko-KR-Chirp3-HD-Fenrir",
            "ssmlGender": "MALE",
        },
        {
            "index": 8,
            "type": "Premium",
            "name": "ko-KR-Chirp3-HD-Kore",
            "ssmlGender": "FEMALE",
        },
        {
            "index": 9,
            "type": "Premium",
            "name": "ko-KR-Chirp3-HD-Leda",
            "ssmlGender": "FEMALE",
        },
        {
            "index": 10,
            "type": "Premium",
            "name": "ko-KR-Chirp3-HD-Orus",
            "ssmlGender": "MALE",
        },
        {
            "index": 11,
            "type": "Premium",
            "name": "ko-KR-Chirp3-HD-Puck",
            "ssmlGender": "MALE",
        },
        {
            "index": 12,
            "type": "Premium",
            "name": "ko-KR-Chirp3-HD-Zephyr",
            "ssmlGender": "FEMALE",
        },
        {
            "index": 13,
            "type": "Premium",
            "name": "ko-KR-Neural2-A",
            "ssmlGender": "FEMALE",
        },
        {
            "index": 14,
            "type": "Premium",
            "name": "ko-KR-Neural2-B",
            "ssmlGender": "FEMALE",
        },
        {
            "index": 15,
            "type": "Premium",
            "name": "ko-KR-Neural2-C",
            "ssmlGender": "MALE",
        },
        {
            "index": 16,
            "type": "Premium",
            "name": "ko-KR-Wavenet-A",
            "ssmlGender": "FEMALE",
        },
        {
            "index": 17,
            "type": "Premium",
            "name": "ko-KR-Wavenet-B",
            "ssmlGender": "FEMALE",
        },
        {
            "index": 18,
            "type": "Premium",
            "name": "ko-KR-Wavenet-C",
            "ssmlGender": "MALE",
        },
        {
            "index": 19,
            "type": "Premium",
            "name": "ko-KR-Wavenet-D",
            "ssmlGender": "MALE",
        },
    ]

    # Điều chỉnh index để luôn nằm trong phạm vi hợp lệ
    adjusted_index = (index - 1) % len(korean_voices)
    return korean_voices[adjusted_index]


def format_time_caption(seconds):
    """
    Chuyển đổi thời gian float thành định dạng SRT (hh:mm:ss,ms)
    :param seconds: Thời gian tính bằng giây
    :return: Chuỗi thời gian định dạng SRT
    """
    millisec = int((seconds % 1) * 1000)
    seconds = int(seconds)
    minutes = seconds // 60
    hours = minutes // 60
    return f"{hours:02}:{minutes%60:02}:{seconds%60:02},{millisec:03}"


def get_audio_duration(file_path):
    """Lấy thời gian của file MP3 bằng ffmpeg"""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-i",
                file_path,
                "-show_entries",
                "format=duration",
                "-v",
                "quiet",
                "-of",
                "csv=p=0",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        duration = float(result.stdout.strip())  # Chuyển kết quả thành số thực
        return duration

    except Exception as e:
        print(f"Lỗi khi lấy thời gian audio: {e}")
        return 0.0


def format_time(delta):
    """
    Chuyển đổi thời gian timedelta thành chuỗi định dạng hh:mm:ss,SSS (chuẩn SRT)
    """
    total_seconds = int(delta.total_seconds())
    milliseconds = int((delta.total_seconds() - total_seconds) * 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def generate_srt(text, audio_file, output_srt, start_offset=0.0):
    """
    Tạo file phụ đề SRT từ văn bản, đảm bảo đồng bộ với voice, giữ nguyên dấu câu & bỏ index.

    :param text: Văn bản cần làm phụ đề.
    :param audio_file: Đường dẫn file âm thanh đã tạo.
    :param output_srt: Đường dẫn file SRT cần lưu.
    :param start_offset: Thời gian (giây) mà phụ đề sẽ bắt đầu.
    """
    try:
        # Lấy thời gian file âm thanh
        audio_duration = get_audio_duration(audio_file)

        # Tách văn bản theo dấu câu (vẫn giữ nguyên dấu câu)
        sentences = re.split(r"([.!?])", text)

        # Gộp lại để giữ nguyên dấu câu
        processed_sentences = []
        temp_sentence = ""

        for segment in sentences:
            temp_sentence += segment  # Ghép lại phần nội dung + dấu câu
            if segment in ".!?":  # Nếu gặp dấu câu, thì hoàn thành câu đó
                processed_sentences.append(temp_sentence.strip())
                temp_sentence = ""  # Reset để bắt đầu câu mới

        # Nếu còn câu nào chưa được thêm (trường hợp không có dấu câu cuối)
        if temp_sentence:
            processed_sentences.append(temp_sentence.strip())

        # Chia nhỏ câu nếu dài hơn 20 ký tự
        wrapped_sentences = []
        for sentence in processed_sentences:
            small_chunks = textwrap.wrap(
                sentence, width=20
            )  # Chia nhỏ nhưng vẫn giữ dấu câu
            wrapped_sentences.extend(small_chunks)

        # Tính tổng số ký tự để phân bổ thời gian hợp lý
        total_chars = sum(len(chunk) for chunk in wrapped_sentences)

        start_time = datetime.timedelta(seconds=start_offset)  # Bắt đầu từ start_offset
        srt_content = ""  # Chuỗi chứa nội dung SRT (không có index)

        for chunk in wrapped_sentences:
            # Tính thời gian hiển thị dựa trên số ký tự
            chunk_duration = (len(chunk) / total_chars) * audio_duration
            end_time = start_time + datetime.timedelta(seconds=chunk_duration)

            # Định dạng thời gian chính xác
            start_str = format_time(start_time)
            end_str = format_time(end_time)

            # Thêm vào nội dung file SRT
            srt_content += f"{start_str} --> {end_str}\n{chunk}\n\n"

            # Cập nhật thời gian bắt đầu cho caption tiếp theo
            start_time = end_time

        # Ghi ra file SRT (không có index)
        with open(output_srt, "w", encoding="utf-8") as f:
            f.write(srt_content)

        print(f"✅ Đã tạo file SRT (KHÔNG có index): {output_srt}")

        # Tạo đường dẫn file trên server
        current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
        output_srt = output_srt.replace("static/", "").replace("\\", "/")
        file_url = f"{current_domain}/{output_srt}"

        return file_url

    except Exception as e:
        print(f"❌ Lỗi khi tạo SRT: {e}")
        return ""


def distribute_images_over_audio(image_list, audio_duration, start_offset=0.0):
    """
    Chia thời gian hiển thị ảnh sao cho khớp với thời gian audio, bắt đầu từ một thời điểm nhất định.

    :param image_list: Danh sách ảnh.
    :param audio_duration: Tổng thời gian audio.
    :param start_offset: Thời gian bắt đầu hiển thị ảnh (giây).
    :return: Danh sách dictionary với key (url, start_time, end_time, length).
    """
    num_images = len(image_list)
    if num_images == 0 or audio_duration == 0:
        return []

    image_duration = round(audio_duration / num_images, 2)  # Làm tròn thời gian mỗi ảnh
    timestamps = []

    start_time = round(start_offset, 2)  # Làm tròn thời gian bắt đầu
    for i in range(num_images):
        end_time = round(start_time + image_duration, 2)  # Làm tròn thời gian kết thúc
        length = round(end_time - start_time, 2)  # Tính thời gian xuất hiện của ảnh

        timestamps.append(
            {
                "url": image_list[i],
                "start_time": start_time,
                "end_time": end_time,
                "length": length,  # Thêm thông tin thời gian ảnh xuất hiện
            }
        )

        start_time = end_time  # Cập nhật thời gian bắt đầu ảnh tiếp theo

    log_make_video_message(timestamps)
    return timestamps
