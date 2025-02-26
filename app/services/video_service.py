import requests
import json
import os
import random
from app.models.video_create import VideoCreate
from app.models.video_viral import VideoViral
from app.models.setting import Setting
from app.lib.logger import logger
from sqlalchemy.sql.expression import func
from flask import Flask, request
import time
import datetime
from app.lib.logger import log_make_video_message

from gtts import gTTS
import uuid


class VideoService:

    @staticmethod
    def create_video_from_images(
        post_id, product_name, images_url, images_slider_url, captions
    ):

        domain = request.host

        config = VideoService.get_settings()
        SHOTSTACK_API_KEY = config["SHOTSTACK_API_KEY"]
        SHOTSTACK_URL = config["SHOTSTACK_URL"]
        is_ai_image = config["SHOTSTACK_AI_IMAGE"]

        # FAKE để cho local host không tạo AI
        if domain.startswith("localhost") or domain.startswith("127.0.0.1"):
            is_ai_image = "0"

        voice_dir = f"static/voice/{post_id}"
        os.makedirs(voice_dir, exist_ok=True)

        # create voice Google TTS
        text_to_speech = f"{product_name} 출시되었습니다. 지금 만나보세요!"
        tts = gTTS(text=text_to_speech, lang="ko")
        file_name = f"template_voice_{uuid.uuid4().hex}.mp3"
        file_path = f"{voice_dir}/{file_name}"

        tts.save(file_path)

        check_live_version = os.environ.get("APP_STAGE") or "localhost"

        voice_url = f"https://apitoktak.voda-play.com/voice/{post_id}/{file_name}"

        if check_live_version == "localhost":
            voice_url = "https://apitoktak.voda-play.com/voice/voice.mp3"

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

        clips_data = VideoService.create_combined_clips(
            post_id, images_url, images_slider_url, prompts, is_ai_image, captions
        )

        payload = {
            "timeline": {
                "background": "#FFFFFF",
                "tracks": [
                    clips_data,
                    {
                        "clips": [
                            {
                                "asset": {
                                    "type": "audio",
                                    "src": voice_url,
                                    "effect": "fadeIn",
                                    "volume": 1,
                                },
                                "start": 5,
                                "length": "end",
                            }
                        ]
                    },
                    {
                        "clips": [
                            {
                                "asset": {
                                    "type": "audio",
                                    "src": "https://shotstack-assets.s3.ap-southeast-2.amazonaws.com/music/unminus/ambisax.mp3",
                                    "effect": "fadeOut",
                                    "volume": 1,
                                },
                                "start": 5,
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
                # "size": {"width": 1200, "height": 800},
                "size": {"width": 720, "height": 1280},
            },
            "callback": "https://apitoktak.voda-play.com/api/v1/video_maker/shotstack_webhook",
        }

        # log_make_video_message(f"payload: {payload}")
        log_make_video_message(f"payload_dumps: {json.dumps(payload)}")

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
                return result
            else:
                result = response.json()
                log_make_video_message("create video Failed :{0}".format(str(result)))
                return {
                    "message": "Failed to create video",
                    "status_code": response.status_code,
                }

        except Exception as e:
            log_make_video_message(
                "create_video_from_images : Exception: {0}".format(str(e))
            )
            return {
                "message": str(e),
                "status_code": 500,
            }

    # Hàm lấy trạng thái video từ Shotstack API
    @staticmethod
    def get_video_status(render_id):
        """
        Kiểm tra trạng thái render của video từ Shotstack API.

        :param render_id: ID của video đã tạo từ Shotstack.
        :return: Trạng thái video hoặc thông báo lỗi.
        """

        config = VideoService.get_settings()
        SHOTSTACK_API_KEY = config["SHOTSTACK_API_KEY"]
        SHOTSTACK_URL = config["SHOTSTACK_URL"]

        url = f"{SHOTSTACK_URL}/{render_id}"
        headers = {"x-api-key": SHOTSTACK_API_KEY}

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                return {"status": True, "message": "Oke", "data": response.json()}
            else:
                # log_make_video_message(f"API Error {response.status_code}: {response.text}")
                return {"status": False, "message": response.text, "data": []}

        except requests.exceptions.RequestException as e:
            # log_make_video_message(f"Request failed: {str(e)}")
            return {
                "status": False,
                "message": "Request failed, please try again.",
                "data": [],
            }

        except Exception as e:
            # log_make_video_message(f"Unexpected error: {str(e)}")
            return {
                "status": False,
                "message": "An unexpected error occurred.",
                "data": [],
            }

    @staticmethod
    def create_create_video(*args, **kwargs):
        create_video = VideoCreate(*args, **kwargs)
        create_video.save()
        return create_video

    @staticmethod
    def get_videos(page, per_page):
        pagination = VideoCreate.query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        return pagination

    @staticmethod
    def update_video_create(render_id, *args, **kwargs):

        create_video = VideoCreate.query.filter_by(render_id=render_id).first()
        if not create_video:
            return None
        create_video.update(**kwargs)
        return create_video

    @staticmethod
    def test_create_video_from_images(post_id, images_url, prompts):
        config = VideoService.get_settings()
        SHOTSTACK_API_KEY = config["SHOTSTACK_API_KEY"]
        SHOTSTACK_URL = config["SHOTSTACK_URL"]
        voice_url = "https://apitoktak.voda-play.com/voice/voice.mp3"

        print(SHOTSTACK_API_KEY)
        clips_data = test_create_combined_clips(
            post_id, images_url, prompts
        )

        payload = {
            "timeline": {
                "background": "#FFFFFF",
                "tracks": [
                    clips_data,
                    {
                        "clips": [
                            {
                                "asset": {
                                    "type": "audio",
                                    "src": voice_url,
                                    "effect": "fadeIn",
                                    "volume": 1,
                                },
                                "start": 5,
                                "length": "end",
                            }
                        ]
                    },
                ],
            },
            "output": {
                "format": "mp4",
                "quality": "veryhigh",
                "size": {"width": 720, "height": 1280},
            },
        }

        # log_make_video_message(f"payload: {payload}")
        log_make_video_message(f"payload_dumps: {json.dumps(payload)}")

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
                return result
            else:
                result = response.json()
                log_make_video_message("create video Failed :{0}".format(str(result)))
                return {
                    "message": "Failed to create video",
                    "status_code": response.status_code,
                }

        except Exception as e:
            log_make_video_message(
                "create_video_from_images : Exception: {0}".format(str(e))
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

    def create_combined_clips(
        post_id,
        ai_images,
        images_slider_url,
        prompts=None,
        is_ai_image="0",
        captions=None,
    ):
        video_urls = get_random_videos(2)
        # Chọn 2 URL khác nhau một cách ngẫu nhiên
        intro_url, outro_url = random.sample(video_urls, 2)

        clips = []
        current_start = 0
        intro_length = 5

        file_path_srts = generate_srt(post_id, captions)

        clips.append(
            {
                "asset": {"type": "video", "src": intro_url},
                "start": current_start,
                "length": intro_length,
            }
        )

        clips.append(
            {
                "asset": {
                    "type": "caption",
                    "src": "https://apitoktak.voda-play.com/voice/caption/first_video_transcript.srt",
                    "font": {
                        "family": "Noto Sans KR",
                        "color": "#ffffff",
                        "opacity": 0.8,
                        "size": 50,
                        "lineHeight": 0.8,
                        "stroke": "#ff6600",
                        "strokeWidth": 0.8,
                    },
                    "background": {
                        "color": "#000000",
                        "opacity": 0.4,
                        "padding": 80,
                        "borderRadius": 30,
                    },
                    "margin": {"top": 0.05, "left": 0.25, "right": 0.25},
                    "speed": 1,
                },
                "start": 0,
                "length": 5,
            },
        )
        current_start += intro_length

        if is_ai_image == "1":

            time_run_ai = 5
            for i, url in enumerate(ai_images):
                clips.append(
                    {
                        "asset": {
                            "src": url,
                            "type": "image-to-video",
                            "prompt": random.choice(prompts) if prompts else "",
                        },
                        "start": current_start + i * time_run_ai,
                        "length": time_run_ai,
                    }
                )
            current_start += len(ai_images) * time_run_ai

        start_time_caption = current_start
        time_show_image = 5

        for j_index, url in enumerate(images_slider_url):
            clips.append(
                {
                    "asset": {"type": "image", "src": url},
                    "start": current_start + j_index * time_show_image,
                    "length": time_show_image,
                    "effect": "zoomIn",
                },
            )

            url_srt = file_path_srts[j_index]
            check_live_version = os.environ.get("APP_STAGE") or "localhost"
            url_path_srt = "https://apitoktak.voda-play.com" + url_srt
            if check_live_version == "localhost":
                url_path_srt = (
                    "https://apitoktak.voda-play.com/voice/caption/transcript.srt"
                )

            clips.append(
                {
                    "asset": {
                        "type": "caption",
                        "src": url_path_srt,
                        "font": {
                            "family": "Noto Sans KR",
                            "color": "#fc0303",
                            "size": 50,
                            "lineHeight": 0.8,
                        },
                    },
                    "start": current_start + j_index * time_show_image,
                    "length": time_show_image,
                },
            )

        current_start += len(images_slider_url) * time_show_image
        outro_length = 5
        clips.append(
            {
                "asset": {"type": "video", "src": outro_url},
                "start": current_start,
                "length": outro_length,
            }
        )
        current_start += outro_length

        time_show_caption = 5

        clips_shape = [
            {
                "asset": {
                    "type": "image",
                    "src": "https://apitoktak.voda-play.com/voice/logo.png",
                },
                "start": 0,
                "length": "end",
                "scale": 0.15,
                "position": "topRight",
            }
            # {
            #     "asset": {
            #         "type": "html",
            #         "html": "<p>Style text in video using <b>HTML</b> and <u>CSS</u></p>",
            #         "css": "p { font-family: 'Open Sans'; color: #ffffff; font-size: 42px; text-align: center; } b { color: #21bcb9; font-weight: normal; } u { color: #e784ff; text-decoration: none; }",
            #         "width": 500,
            #         "height": 300,
            #     },
            #     "start": 0,
            #     "length": "end",
            # },
        ]

        # Kết hợp hai danh sách clip lại
        combined_clips = clips_shape + clips
        return {"clips": combined_clips}

def get_random_videos(limit=2):
    try:
        videos = (
            VideoViral.query.with_entities(VideoViral.video_url)
            .order_by(func.rand())
            .limit(limit)
            .all()
        )
        return [video.video_url for video in videos]

    except Exception as e:
        log_make_video_message(f"get_random_videos: {str(e)}")
        return []

def generate_srt(post_id, captions):
    """
    Tạo các file transcript.srt riêng biệt cho từng caption.
    Lưu vào thư mục static/voice/caption/
    """
    file_path = f"voice/{post_id}"
    os.makedirs(f"static/{file_path}", exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_paths = []

    for i, text in enumerate(captions):
        file_name = f"transcript_{timestamp}_{i}.srt"
        file_path_srt = f"static/{file_path}/{file_name}"

        start_time = 0
        start = format_time(start_time)
        end = format_time(start_time + 5)

        with open(file_path_srt, "w", encoding="utf-8") as f:
            f.write(f"{1}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")

        file_paths.append(f"/{file_path}/{file_name}")

    return file_paths  # Trả về danh sách các file đã tạo

def format_time(seconds):
    """
    Chuyển đổi giây thành định dạng thời gian SRT (hh:mm:ss,ms).
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    sec = seconds % 60
    return f"{hours:02}:{minutes:02}:{sec:02},000"


def test_create_combined_clips(
        post_id,
        ai_images,
        prompts=None,
        is_ai_image="1",
    ):

        clips = []
        current_start = 0

        if is_ai_image == "1":

            time_run_ai = 5
            for i, url in enumerate(ai_images):
                clips.append(
                    {
                        "asset": {
                            "src": url,
                            "type": "image-to-video",
                            "prompt": prompts[i],
                        },
                        "start": current_start + i * time_run_ai,
                        "length": time_run_ai,
                    }
                )
            current_start += len(ai_images) * time_run_ai

        clips_shape = []

        # Kết hợp hai danh sách clip lại
        combined_clips = clips_shape + clips
        return {"clips": combined_clips}
