import requests
import json
import os
import random
from app.models.video_create import VideoCreate
from app.models.video_viral import VideoViral
from app.models.captions import Caption
from app.models.setting import Setting
from app.lib.logger import logger
from sqlalchemy.sql.expression import func
from flask import Flask, request
import time
import datetime
from app.lib.logger import log_make_video_message

from gtts import gTTS
import uuid
import srt
from moviepy.editor import VideoFileClip
from app.extensions import redis_client
from pydub import AudioSegment
import subprocess
from app.services.request_log import RequestLogService


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
        MUSIC_BACKGROUP_VOLUMN = float(config["MUSIC_BACKGROUP_VOLUMN"])
        MUSIC_VOLUMN = float(config["MUSIC_VOLUMN"])
        video_size_json = config["VIDEO_SIZE"] or '{"width": 1200, "height": 800}'
        video_size = json.loads(video_size_json)

        key_redis = f"caption_videos_default"
        progress_json = redis_client.get(key_redis)

        if progress_json:
            caption_videos_default = json.loads(progress_json) if progress_json else {}
        else:

            caption_videos_default = VideoService.get_caption_defaults()
            redis_client.set(key_redis, json.dumps(caption_videos_default))

        # FAKE để cho local host không tạo AI
        if domain.startswith("localhost") or domain.startswith("127.0.0.1"):
            is_ai_image = "0"

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
            post_id,
            images_url,
            images_slider_url,
            prompts,
            is_ai_image,
            captions,
            config,
            caption_videos_default,
        )

        current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
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
                    clips_data["clips"],
                    {
                        "clips": [
                            {
                                "asset": {
                                    "type": "audio",
                                    "src": "https://apitoktak.voda-play.com/voice/audio/ambisax.mp3",
                                    "effect": "fadeOut",
                                    "volume": MUSIC_BACKGROUP_VOLUMN,
                                },
                                "start": clips_data["intro_length"],
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
                    "message": "Failed to create video",
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

        clips_data = test_create_combined_clips(post_id, images_url, prompts)

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

    def create_combined_clips(
        post_id,
        ai_images,
        images_slider_url,
        prompts=None,
        is_ai_image="0",
        captions=None,
        config=None,
        caption_videos_default=None,
    ):
        video_urls = get_random_videos(2)
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
        first_caption_videos_default = VideoService.filter_content_by_type(
            caption_videos_default, 1
        )

        clip_detail = create_header_text(first_caption_videos_default, current_start, 2)
        clips.append(clip_detail)

        current_start += intro_length
        file_path_srts = generate_srt(post_id, captions)

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
                # Cái này cần phải lấy từ chat GPT
                # captions form Image to video

                url_path_srt = file_path_srts[i]
                clips.append(
                    {
                        "asset": {
                            "type": "caption",
                            "src": url_path_srt,
                            "background": {
                                "color": "#000000",
                                "padding": 20,
                                "borderRadius": 18,
                                "opacity": 0.6,
                            },
                            "font": {
                                "lineHeight": 0.8,
                                "family": "JalnanGothic",
                                "color": "#ff0505",
                                "size": 50,
                            },
                        },
                        "start": current_start + i * time_run_ai,
                        "length": time_run_ai,
                    },
                )
            current_start += len(ai_images) * time_run_ai

        start_time_caption = current_start
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

        last_caption_videos_default = VideoService.filter_content_by_type(
            caption_videos_default, 4
        )

        for j_index, url in enumerate(images_slider_url):

            random_effect = random.choice(effects)
            start_slider_time = current_start + j_index * time_show_image

            clip_detail = {
                "asset": {"type": "image", "src": url},
                "start": start_slider_time,
                "length": time_show_image,
            }

            if random_effect != "":
                clip_detail["effect"] = random_effect
            clips.append(clip_detail)

            if j_index == 0:
                first_caption_image_default = VideoService.filter_content_by_type(
                    caption_videos_default, 2
                )
                clip_detail = create_header_text(
                    first_caption_image_default, start_slider_time, 2
                )
                clips.append(clip_detail)
            elif j_index == 2:
                # When 3rd image start, display for 2 sec
                first_caption_image_default = VideoService.filter_content_by_type(
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

            url_path_srt = file_path_srts[j_index]

            # srt_captions = parse_srt_to_html_assets(url_path_srt, start_slider_time)
            # for srt_caption in srt_captions:
            # clips.append(srt_caption)

            voice_url = create_mp3_from_srt(post_id, url_path_srt)

            clips.append(
                {
                    "asset": {
                        "type": "caption",
                        "src": url_path_srt,
                        "font": {
                            "lineHeight": 1,
                            "family": "JalnanGothic",
                            "color": "#ffffff",
                            "size": 46,
                            "stroke": "#000000",
                            "strokeWidth": 1.5,
                        },
                    },
                    "start": start_slider_time + 0.01,
                    "length": time_show_image,
                },
            )
            if voice_url != "":
                clips.append(
                    {
                        "asset": {
                            "type": "audio",
                            "src": voice_url,
                            "volume": 1,
                        },
                        "start": start_slider_time + 0.01,
                        "length": time_show_image,
                    }
                )
            # clips.append(
            #     {
            #         "asset": {
            #             "type": "html",
            #             "html": "<div style='font-size: 40px; color: #080000;  text-align: center; font-family: 'JalnanGothic', sans-serif;'>잠시만요. <span style='font-weight: bold;'>10</span>초 뒤에 더<br> 놀라운 영상이 이어집니다.</div>",
            #             "css": "div {   font-family: 'JalnanGothic', sans-serif; background: #FFD600 ;  border-radius: 40px;}",
            #         },
            #         "start": start_slider_time + 0.01,
            #         "length": time_show_image,
            #         "position": "top",
            #         "offset": {"x": 0, "y": 0.4},
            #     }
            # )

        current_start += len(images_slider_url) * time_show_image
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

        clips_shape = [
            # {
            #     "asset": {
            #         "type": "image",
            #         "src": "https://apitoktak.voda-play.com/voice/logo.png",
            #     },
            #     "start": 0,
            #     "length": "end",
            #     "scale": 0.15,
            #     "position": "topRight",
            # },
            # {
            #     "asset": {
            #         "type": "html",
            #         "html": "<div style='font-size: 60px; color: #000000; padding: 10px; text-align: center;'>Wait a minute.</div>",
            #         "css": "div { font-weight: bold; font-family: 'JalnanGothic', sans-serif; border-radius: 40px; }",
            #         "width": 500,
            #         "height": 200,
            #         "background": "#FFD600",
            #         "position": "center",
            #     },
            #     "start": 0.1,
            #     "length": 5,
            # },
        ]

        # Kết hợp hai danh sách clip lại
        combined_clips = clips_shape + clips
        return {"intro_length": intro_length, "clips": {"clips": combined_clips}}


def get_random_videos(limit=2):
    try:
        videos = VideoViral.query.filter_by(status=1).all()
        video_data = [
            {
                "video_name": video_detail.video_name,
                "video_url": video_detail.video_url,
                "duration": video_detail.duration,
            }
            for video_detail in videos
        ]

        key_redis = "viral_video_redis"
        progress_json = redis_client.get(key_redis)

        if progress_json:
            video_viral_s = json.loads(progress_json) if progress_json else {}
        else:
            video_viral_s = video_data
            redis_client.set(key_redis, json.dumps(video_viral_s))

        random_items = random.sample(video_viral_s, limit)
        return random_items

    except Exception as e:
        log_make_video_message(f"get_random_videos: {str(e)}")
        return []


def generate_srt(post_id, captions):
    """
    Tạo các file transcript.srt riêng biệt cho từng caption.
    Lưu vào thư mục static/voice/caption/
    """
    date_create = datetime.datetime.now().strftime("%Y_%m_%d")
    file_path = f"voice/gtts_voice/{date_create}/{post_id}"
    os.makedirs(f"static/{file_path}", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_paths = []

    for i, text in enumerate(captions):
        file_name = f"transcript_{timestamp}_{i}.srt"
        file_path_srt = f"static/{file_path}/{file_name}"

        start_time = 0
        start = format_time(start_time)
        end = format_time(start_time + 5)
        let_step = 1
        duration_per_caption = 5

        text = text.replace("\\", "")
        text = text.replace("…", "\n")
        text = text.replace("...", "\n")
        text = text.strip()
        with open(file_path_srt, "w", encoding="utf-8") as f:

            segments = text.split("\n")

            if len(segments) == 1:
                f.write(f"{1}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
            else:
                duration_per_caption = 2.5
                for segment in segments:
                    segment = segment.replace('"', "")
                    segment = segment.strip()
                    end_time = start_time + duration_per_caption
                    f.write(f"{let_step}\n")
                    f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
                    f.write(f"{segment}\n\n")
                    let_step = let_step + 1
                    start_time = end_time
                    duration_per_caption = duration_per_caption + 0.1
        CURRENT_DOMAIN = os.environ.get("CURRENT_DOMAIN") or "localhost"
        file_paths.append(f"{CURRENT_DOMAIN}/{file_path}/{file_name}")
        # file_paths.append(file_path_srt)

    return file_paths  # Trả về danh sách các file đã tạo


def format_time(seconds):
    """
    Chuyển đổi giây (có thể là float) thành định dạng thời gian SRT (hh:mm:ss,ms).
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    sec = int(seconds % 60)
    # Tính phần mili giây
    ms = int(round((seconds - int(seconds)) * 1000)) + 1
    return f"{hours:02}:{minutes:02}:{sec:02},{ms:03}"


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


def create_mp3_from_srt(post_id, srt_filepath):
    """
    Đọc file SRT, trích xuất nội dung và tạo file MP3 từ nội dung đó.

    :param srt_filepath: Đường dẫn tới file SRT.
    :param output_mp3_path: Đường dẫn file MP3 sẽ được lưu.
    :param lang: Mã ngôn ngữ cho TTS (mặc định 'ko' cho tiếng Hàn, có thể đổi 'en' cho tiếng Anh).
    """

    CURRENT_DOMAIN = os.environ.get("CURRENT_DOMAIN") or "localhost"

    srt_filepath = srt_filepath.replace(CURRENT_DOMAIN, "static")

    # Đọc nội dung file SRT với encoding UTF-8
    with open(srt_filepath, "r", encoding="utf-8") as f:
        srt_content = f.read()

    # Phân tích file SRT thành danh sách caption
    captions = list(srt.parse(srt_content))

    # Ghép nội dung tất cả các caption, thay dòng mới bằng dấu cách
    text_to_speak = " ".join(
        [caption.content.replace("\n", "") for caption in captions]
    )

    date_create = datetime.datetime.now().strftime("%Y_%m_%d")

    public_patch = f"/voice/gtts_voice/{date_create}/{post_id}"
    voice_dir = f"static/{public_patch}"
    os.makedirs(voice_dir, exist_ok=True)

    uuid_str = uuid.uuid4().hex

    text_to_speak = text_to_speak.strip()
    if text_to_speak != "":

        # create voice Google TTS
        tts = gTTS(text=text_to_speak, lang="ko")
        file_name = f"template_voice_sub_caption_{uuid_str}_1.mp3"
        file_path = f"{voice_dir}/{file_name}"

        tts.save(file_path)

        CURRENT_DOMAIN = os.environ.get("CURRENT_DOMAIN") or "localhost"
        voice_url = f"{CURRENT_DOMAIN}/{public_patch}/{file_name}"

        new_file_name = f"template_voice_sub_caption_{uuid_str}_3.mp3"
        new_voice_dir = f"{voice_dir}/{new_file_name}"

        change_speed_ffmpeg(file_path, new_voice_dir, speed=1.5)

        new_voice_url = f"{CURRENT_DOMAIN}/{public_patch}/{new_file_name}"
        return new_voice_url
    return ""


def create_html_caption(caption_text, start=0, length=0, add_time=0):
    """
    Tạo HTML cho caption text.
    """
    # html = f"<div style='font-size: 60px; color: #ffffff;  text-align: center; font-family: 'JalnanGothic', sans-serif; text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000; -webkit-text-stroke: 2px #000000; '> <span style='font-weight: bold;'>{caption_text}</span> </div>"
    # css = "div {  text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000; -webkit-text-stroke: 2px #000000; font-family: 'JalnanGothic', sans-serif;    border-radius: 40px;}"

    html = f"<table border='0' width='1000'><tr><td bgcolor='#FF0000' width='10'>&nbsp;</td><td width='990'><p>{caption_text}</p></td></tr></table>"
    css = "table { background-color: #77000000; } td { padding-top: 16px; padding-bottom: 16px; } p { color: #FFFFFF; font-size: 34px; font-family: 'JalnanGothic' sans-serif; font-weight: bold; margin: 20px; }"

    return {
        "html": html,
        "css": css,
    }


def speed_change(sound, speed=1.5):
    """
    Tăng tốc độ phát của âm thanh bằng cách thay đổi frame_rate.
    Lưu ý: Phương pháp này cũng thay đổi cao độ của âm thanh.
    """
    # Tăng frame_rate theo hệ số speed
    altered_sound = sound._spawn(
        sound.raw_data, overrides={"frame_rate": int(sound.frame_rate * speed)}
    )
    # Thiết lập lại frame_rate ban đầu để file mp3 có thể phát đúng định dạng
    return altered_sound.set_frame_rate(sound.frame_rate)


def change_speed_ffmpeg(input_file, output_file, speed=1.5):
    # Lưu ý: ffmpeg atempo filter hỗ trợ tốc độ từ 0.5 đến 2.0, đối với tốc độ ngoài khoảng này cần thực hiện nhiều bước.
    command = [
        "ffmpeg",
        "-i",
        input_file,
        "-filter:a",
        f"atempo={speed}",
        "-vn",  # Không xử lý video
        output_file,
    ]

    try:
        # Thực hiện lệnh ffmpeg
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        log_make_video_message(f"Đã xảy ra lỗi khi thay đổi tốc độ: {e}")
    else:
        # Nếu không có lỗi, xóa file cũ
        try:
            os.remove(input_file)
        except OSError as e:
            log_make_video_message(f"Lỗi khi xóa file {input_file}: {e}")


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
