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
from app.services.post import PostService

import srt

# import ffmpeg
import textwrap
import re  # Thêm thư viện để xử lý dấu câu
from const import EFFECTS_CONST, KOREAN_VOICES
from PIL import Image, ImageDraw, ImageFont


class ShotStackService:

    @staticmethod
    def create_video_from_images_v2(data_make_video):
        post_id = data_make_video["post_id"]
        batch_id = data_make_video["batch_id"]
        is_advance = data_make_video["is_advance"]
        template_info = data_make_video["template_info"]
        voice_google = data_make_video["voice_google"]
        origin_caption = data_make_video["origin_caption"]
        images_url = data_make_video["images_url"]
        images_slider_url = data_make_video["images_slider_url"]
        product_video_url = data_make_video["product_video_url"] or ""

        config = ShotStackService.get_settings()
        SHOTSTACK_API_KEY = config["SHOTSTACK_API_KEY"]
        SHOTSTACK_URL = config["SHOTSTACK_URL"]
        is_ai_image = config["SHOTSTACK_AI_IMAGE"]
        MUSIC_BACKGROUP_VOLUMN = float(config["MUSIC_BACKGROUP_VOLUMN"])
        IS_GOOGLE_DRIVER = int(config["IS_GOOGLE_DRIVER"])
        video_size_json = config["VIDEO_SIZE"] or '{"width": 1200, "height": 800}'
        video_size = json.loads(video_size_json)

        key_redis = "caption_videos_default"
        progress_json = redis_client.get(key_redis)
        timestamp = datetime.datetime.now().strftime("%H%M%S")

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
        dir_path = f"static/voice/gtts_voice/{date_create}/{batch_id}"
        current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"

        # Chọn giọng nói ngẫu nhiên
        korean_voice = get_korean_voice(voice_google)

        mp3_file, audio_duration = text_to_speech_kr(
            korean_voice, origin_caption, dir_path, config
        )

        video_urls = ShotStackService.get_random_videos(2)

        audio_urls = get_random_audio(1)
        first_viral_detail = video_urls[0] or []
        first_duration = float(first_viral_detail["duration"] or 0)

        if is_advance == 1:

            template_info = data_make_video["template_info"]

            template_info_json = json.loads(template_info)
            is_video_hooking = template_info_json["is_video_hooking"]

            if is_video_hooking == 0:
                first_duration = 0

            new_image_sliders = distribute_images_over_audio(
                images_slider_url, audio_duration, first_duration
            )
            clips_data = create_combined_clips_with_advance(
                data_make_video,
                new_image_sliders,
                video_urls,
                config,
                caption_videos_default,
            )
        else:

            first_duration = 0
            new_image_sliders = distribute_images_over_audio(
                images_slider_url, audio_duration, first_duration
            )
            # Man  hinh thong thuong
            clips_data = create_combined_clips_normal(
                new_image_sliders,
                video_urls,
                config,
                caption_videos_default,
                product_video_url,
            )

        file_caption = generate_srt(
            origin_caption,
            mp3_file,
            f"{dir_path}/caption_file{timestamp}.srt",
            first_duration,
        )

        clips_caption = {
            "asset": {
                "type": "caption",
                "src": file_caption,
                "font": {
                    "lineHeight": 1,
                    "family": "Jalnan2",
                    "color": "#ffffff",
                    "size": 38,
                    "stroke": "#000000",
                    "strokeWidth": 1.8,
                },
            },
            "offset": {"x": 0.04, "y": 0.05},
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

        layout_advance = {}
        layout_advance_image_last = {}
        layout_advance_caption_top = {}
        if is_advance == 1:
            template_info = json.loads(template_info)
            product_name = template_info["product_name"]
            purchase_guide = template_info["purchase_guide"]
            is_video_hooking = template_info["is_video_hooking"]
            is_caption_top = template_info["is_caption_top"]
            is_caption_last = template_info["is_caption_last"]
            is_product_name = template_info["is_product_name"]
            is_purchase_guide = template_info["is_purchase_guide"]

            output_file_image_tag = add_centered_text_to_png(
                text=product_name,
                output_path=f"{dir_path}/emoji_with_text_{timestamp}.png",
            )

            if len(purchase_guide) > 5:
                purchase_guide = purchase_guide[:5] + "\n" + purchase_guide[5:]

            is_product_name = int(template_info.get("is_product_name", 0))
            is_purchase_guide = int(template_info.get("is_purchase_guide", 0))

            clip_advance = []
            # Chỉ thêm ảnh nếu is_product_name là 1
            if is_product_name == 1:
                clip_advance.append(
                    {
                        "asset": {
                            "type": "image",
                            "src": output_file_image_tag,
                        },
                        "start": 0,
                        "length": "end",
                        "fit": "none",
                        "position": "topLeft",
                        "offset": {"x": 0.04, "y": -0.026},
                    }
                )

            # Chỉ thêm văn bản nếu is_purchase_guide == 1
            if is_purchase_guide == 1:
                clip_advance.append(
                    {
                        "asset": {
                            "type": "text",
                            "text": purchase_guide,
                            "font": {
                                "family": "GmarketSansTTFMedium",
                                "color": "#ffffff",
                                "size": 30,
                                "lineHeight": 1.2,
                            },
                            "stroke": {"color": "#000000", "width": 0.5},
                            "height": 200,
                            "width": 600,
                        },
                        "start": 0.01,
                        "length": "end",
                        "position": "topRight",
                        "offset": {"x": 0.25, "y": 0.0255},
                    }
                )

            # Chỉ gán `clips` vào `layout_advance` nếu có phần tử
            if clip_advance:
                layout_advance["clips"] = clip_advance

            if is_caption_top == 1:
                layout_advance_caption_top = {}

            if is_caption_last == 1:
                layout_advance_image_last = {
                    "clips": [
                        {
                            "asset": {
                                "type": "video",
                                "src": f"{current_domain}/voice/advance/subscribe_video.mp4",
                            },
                            "start": clips_data["current_start"],
                            "length": 5,
                        }
                    ]
                }

        tracks = [
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
                            "src": audio_urls[0]["video_url"],
                            "effect": "fadeOut",
                            "volume": MUSIC_BACKGROUP_VOLUMN,
                        },
                        "start": 0,
                        "length": "end",
                    }
                ]
            },
        ]

        # Nếu layout_advance có dữ liệu thì thêm vào
        if layout_advance:
            tracks.insert(2, layout_advance)

        if layout_advance_image_last:
            tracks.append(layout_advance_image_last)

        payload = {
            "timeline": {
                "fonts": [
                    {"src": f"{current_domain}/voice/font/GmarketSansTTFBold.ttf"},
                    {"src": f"{current_domain}/voice/font/GmarketSansTTFLight.ttf"},
                    {"src": f"{current_domain}/voice/font/GmarketSansTTFMedium.ttf"},
                    {"src": f"{current_domain}/voice/font/Jalnan2TTF.ttf"},
                    {"src": f"{current_domain}/voice/font/JalnanGothicTTF.ttf"},
                    {"src": f"{current_domain}/voice/font/JalnanGothic.otf"},
                    {"src": f"{current_domain}/voice/font/Jalnan2.otf"},
                ],
                "background": "#FFFFFF",
                "tracks": tracks,
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

        if layout_advance:
            tracks.insert(2, layout_advance)

        if IS_GOOGLE_DRIVER == 1:
            payload["output"]["destinations"] = [
                {
                    "provider": "google-drive",
                    "options": {
                        "filename": f"short_video_{date_create}_{batch_id}",
                        "folderId": "1bUcQ5eo-MhP7GxL23JhzUZ9LbJvqUp_p",
                    },
                },
                {"provider": "shotstack", "exclude": True},
            ]

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


def create_combined_clips_normal(
    images_slider_url,
    video_urls,
    config=None,
    caption_videos_default=None,
    product_video_url=None,
):
    first_viral_detail = video_urls[0] or []
    last_viral_detail = video_urls[1] or []
    # Chọn 2 URL khác nhau một cách ngẫu nhiên
    first_viral_url = first_viral_detail["video_url"]
    first_duration = float(first_viral_detail["duration"] or 0)

    clips = []
    current_start = 0
    intro_length = 0

    # intro_length = first_duration
    # clips.append(
    #     {
    #         "asset": {"type": "video", "src": first_viral_url},
    #         "start": current_start,
    #         "length": intro_length,
    #     }
    # )
    # first_caption_videos_default = ShotStackService.filter_content_by_type(
    #     caption_videos_default, 1
    # )

    # clip_detail = create_header_text(first_caption_videos_default, current_start, 2)
    # clips.append(clip_detail)

    current_start += intro_length

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
        type_asset = image_slider_detail["type"]
        random_effect = random.choice(effects)
        start_slider_time = start_time

        if type_asset == "video":
            clips.append(
                {
                    "asset": {"type": "video", "src": url},
                    "start": start_slider_time,
                    "length": length,
                }
            )
        elif type_asset == "gif":
            clips.append(
                {
                    "asset": {"type": "video", "src": url},
                    "start": start_slider_time,
                    "length": length,
                }
            )
        else:
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
            clip_detail = create_first_header_text(
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
    last_duration = 0
    # clips.append(
    #     {
    #         "asset": {"type": "video", "src": last_viral_url},
    #         "start": current_start,
    #         "length": last_duration,
    #     }
    # )

    # clip_detail = create_header_text(
    #     last_caption_videos_default, current_start, last_duration
    # )
    # clips.append(clip_detail)

    current_start = current_start + last_duration

    # Kết hợp hai danh sách clip lại
    combined_clips = clips
    return {
        "intro_length": intro_length,
        "clips": {"clips": combined_clips},
        "current_start": current_start,
    }


def create_combined_clips_with_advance(
    data_make_video,
    images_slider_url,
    video_urls,
    config=None,
    caption_videos_default=None,
):  # sourcery skip: switch

    is_advance = data_make_video["is_advance"]
    template_info = data_make_video["template_info"]

    template_info = json.loads(template_info)
    product_name = template_info["product_name"]
    purchase_guide = template_info["purchase_guide"]
    is_video_hooking = template_info["is_video_hooking"]
    is_caption_top = template_info["is_caption_top"]
    is_caption_last = template_info["is_caption_last"]

    first_viral_detail = video_urls[0] or []
    last_viral_detail = video_urls[1] or []
    # Chọn 2 URL khác nhau một cách ngẫu nhiên
    first_viral_url = first_viral_detail["video_url"]
    first_duration = float(first_viral_detail["duration"] or 0)

    clips = []
    current_start = 0
    intro_length = 0

    if is_advance == 1:
        if is_video_hooking == 1:
            intro_length = first_duration
            clips.append(
                {
                    "asset": {"type": "video", "src": first_viral_url},
                    "start": current_start,
                    "length": intro_length,
                }
            )
        if is_caption_top == 1:
            first_caption_videos_default = ShotStackService.filter_content_by_type(
                caption_videos_default, 1
            )

            clip_detail = create_header_text(
                first_caption_videos_default, current_start, 2
            )
            clips.append(clip_detail)

    current_start += intro_length

    SHOTSTACK_IMAGE_EFFECTS = config["SHOTSTACK_IMAGE_EFFECTS"] or ""
    if SHOTSTACK_IMAGE_EFFECTS == "random":
        effects = EFFECTS_CONST
    else:
        effects = [
            SHOTSTACK_IMAGE_EFFECTS,
        ]

    last_caption_videos_default = ShotStackService.filter_content_by_type(
        caption_videos_default, 4
    )

    end_time = current_start
    start_time = 0
    for j_index, image_slider_detail in enumerate(images_slider_url):
        url = image_slider_detail["url"]
        start_time = image_slider_detail["start_time"]
        end_time = image_slider_detail["end_time"]
        length = image_slider_detail["length"]
        type_asset = image_slider_detail["type"]
        random_effect = random.choice(effects)
        start_slider_time = start_time

        if type_asset == "video":
            clips.append(
                {
                    "asset": {"type": "video", "src": url},
                    "start": start_slider_time,
                    "length": length,
                }
            )
        elif type_asset == "gif":
            clips.append(
                {
                    "asset": {"type": "video", "src": url},
                    "start": start_slider_time,
                    "length": length,
                }
            )
        else:
            clip_detail = {
                "asset": {"type": "image", "src": url},
                "start": start_slider_time,
                "length": length,
            }
            if random_effect != "":
                clip_detail["effect"] = random_effect
            clips.append(clip_detail)

        # khi chon 영상 위에 바이럴 문구가 표시됩니다. moi hien thi text tren dau
        if is_caption_top == 1:
            if j_index == 0:
                first_caption_image_default = ShotStackService.filter_content_by_type(
                    caption_videos_default, 2
                )
                clip_detail = create_first_header_text(
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

    if is_video_hooking == 1:
        last_viral_url = last_viral_detail["video_url"]
        last_duration = float(last_viral_detail["duration"] or 0)
        clips.append(
            {
                "asset": {"type": "video", "src": last_viral_url},
                "start": current_start,
                "length": last_duration,
            }
        )
        if is_caption_top == 1:
            clip_detail = create_header_text(
                last_caption_videos_default, current_start, last_duration
            )
            clips.append(clip_detail)
            current_start = current_start + last_duration

    # Kết hợp hai danh sách clip lại
    combined_clips = clips
    return {
        "intro_length": intro_length,
        "clips": {"clips": combined_clips},
        "current_start": current_start,
    }


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
    font_size = 40 if len(caption_text) > 20 else 45

    clip_detail = {
        "asset": {
            "type": "text",
            "text": caption_text,
            "font": {
                "family": "Jalnan2",
                "color": "#ffffff",
                "size": font_size,
                "lineHeight": 1.2,
            },
            # "background": {
            #     "color": "#000000",
            #     "borderRadius": 20,
            #     "padding": 0,
            #     "opacity": 0.6,
            # },
            "stroke": {"color": "#000000", "width": 1.5},
            "height": 120,
            "width": 500,
        },
        "start": start + add_time,
        "length": length,
        "position": "top",
        "offset": {"x": 0, "y": -0.14},
    }
    return clip_detail


def create_first_header_text(viral_text, start=0, length=0, add_time=0.01):
    font_size = 60 if len(viral_text) > 20 else 55
    clip_detail = {
        "asset": {
            "type": "text",
            "text": viral_text,
            "font": {
                "family": "Jalnan2",
                "color": "#ffffff",
                "size": font_size,
                "lineHeight": 1,
            },
            "stroke": {"color": "#000000", "width": 3.5},
            "height": 360,
            "width": 700,
        },
        "start": start + add_time,
        "length": length,
        "position": "center",
        "transition": {"in": "slideUp", "out": "slideDown"},
        "offset": {"x": 0, "y": 0},
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
        output_file = f"{disk_path}/google_voice_output.mp3"
        # output_file =  os.path.join(disk_path, "google_voice_output.mp3")

        # Danh sách value của giọng Chirp3-HD (cần bỏ speakingRate)
        chirp3_hd_voices = {
            "ko-KR-Chirp3-HD-Charon",
            "ko-KR-Chirp3-HD-Fenrir",
            "ko-KR-Chirp3-HD-Puck",
            "ko-KR-Chirp3-HD-Aoede",
            "ko-KR-Chirp3-HD-Kore",
            "ko-KR-Chirp3-HD-Leda",
            "ko-KR-Chirp3-HD-Zephyr",
            "ko-KR-Chirp3-HD-Orus",
        }

        # Payload gửi lên Google API
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "ko-KR",
                "name": korean_voice["name"],
                "ssmlGender": korean_voice["ssmlGender"],
            },
            "audioConfig": {"audioEncoding": "MP3"},
        }

        # Nếu giọng không thuộc Chirp3-HD, thêm speakingRate
        if korean_voice["name"] not in chirp3_hd_voices:
            payload["audioConfig"]["speakingRate"] = GOOGLE_API_SPEED

        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{api_url}?key={api_key}", json=payload, headers=headers
        )

        if response.status_code != 200:
            log_make_video_message(f"Lỗi từ Google API payload: {payload}")
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
        log_make_video_message(f"Exception text_to_speech_kr : {str(e)}")
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
    # Điều chỉnh index để luôn nằm trong phạm vi hợp lệ
    adjusted_index = (index - 1) % len(KOREAN_VOICES)
    return KOREAN_VOICES[adjusted_index]


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


def split_text_to_sentences(text):
    """
    Tách văn bản thành danh sách các câu, giữ dấu câu nhưng không tách số thập phân.
    Đồng thời, chia nhỏ câu nếu dài hơn 20 ký tự và xóa dấu chấm cuối câu nếu có.
    :param text: Văn bản đầu vào.
    :return: Danh sách các câu đã được xử lý.
    """

    # Biểu thức chính quy tách câu:
    # - `(?<!\d)[.,](?!\d)`: Chỉ tách `.` hoặc `,` nếu KHÔNG nằm giữa hai chữ số (để giữ số thập phân).
    # - `([!?])\s+`: Luôn tách `!` hoặc `?` nếu có khoảng trắng theo sau.
    sentences = [s for s in re.split(r"(?<!\d)[.,](?!\d)|([!?])\s+", text) if s]

    processed_sentences = []
    temp_sentence = ""

    for segment in sentences:
        if segment in ".!?,":  # Nếu là dấu câu, thêm vào câu trước đó
            temp_sentence += segment
            processed_sentences.append(temp_sentence.strip())
            temp_sentence = ""
        else:
            if temp_sentence:
                processed_sentences.append(temp_sentence.strip())
            temp_sentence = segment.strip()

    if temp_sentence:
        processed_sentences.append(temp_sentence.strip())

    # Xóa dấu chấm cuối câu nếu có
    processed_sentences = [
        s.rstrip(".") if s.endswith(".") else s for s in processed_sentences
    ]

    # Chia nhỏ câu nếu dài hơn 20 ký tự
    short_sentences = []
    for sentence in processed_sentences:
        small_chunks = textwrap.wrap(
            sentence, width=20
        )  # Chia nhỏ nhưng vẫn giữ dấu câu
        short_sentences.extend(small_chunks)

    return short_sentences


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

        # Sử dụng hàm tách câu và chia nhỏ
        short_sentences = split_text_to_sentences(text)

        # Tính tổng số ký tự để phân bổ thời gian hợp lý
        total_chars = sum(len(sentence) for sentence in short_sentences)

        start_time = datetime.timedelta(seconds=start_offset)  # Bắt đầu từ start_offset
        srt_content = ""  # Chuỗi chứa nội dung SRT (không có index)

        for subtitle in short_sentences:
            # Kiểm tra nếu subtitle kết thúc bằng dấu chấm, loại bỏ dấu chấm cuối
            if subtitle.endswith("."):
                subtitle = subtitle[:-1]

            # Tính thời gian hiển thị dựa trên số ký tự
            subtitle_duration = (len(subtitle) / total_chars) * audio_duration
            end_time = start_time + datetime.timedelta(seconds=subtitle_duration)

            # Định dạng thời gian chính xác
            start_str = format_time(start_time)
            end_str = format_time(end_time)

            # Thêm vào nội dung file SRT
            srt_content += f"{start_str} --> {end_str}\n{subtitle}\n\n"

            # Cập nhật thời gian bắt đầu cho caption tiếp theo
            start_time = end_time

        # Ghi ra file SRT (không có index)
        with open(output_srt, "w", encoding="utf-8") as f:
            f.write(srt_content)

        # print(f"✅ Đã tạo file SRT (KHÔNG có index): {output_srt}")

        # Tạo đường dẫn file trên server
        current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
        output_srt = output_srt.replace("static/", "").replace("\\", "/")
        file_url = f"{current_domain}/{output_srt}"

        return file_url

    except Exception as e:
        print(f"❌ Lỗi khi tạo SRT: {e}")
        return ""


def get_media_duration(url):
    """Lấy thời gian của file media (MP3 hoặc MP4) bằng ffmpeg"""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-i",
                url,
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
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        print(f"Lỗi khi lấy thời gian media: {e}")
        return 0.0


def distribute_images_over_audio(image_list, audio_duration=None, start_offset=0.0):
    """
    Phân phối thời gian hiển thị ảnh và video dựa trên thời lượng video/audio.
    Nếu video >= audio_duration thì chỉ trả về video.

    :param image_list: Danh sách URL, có thể chứa video ở đầu.
    :param audio_duration: Tổng thời lượng audio (bắt buộc nếu không có video).
    :param start_offset: Thời điểm bắt đầu hiển thị (giây).
    :return: Danh sách dict gồm url, start_time, end_time, length, type.
    """
    if not image_list:
        return []

    timestamps = []
    first_url = image_list[0]
    is_video = first_url.lower().endswith(".mp4")

    # Nếu có video
    if is_video:
        video_duration = get_media_duration(first_url)

        # Nếu video dài hơn hoặc bằng audio_duration → chỉ dùng video
        if audio_duration is not None and video_duration >= audio_duration:
            adjusted_length = round(audio_duration, 2)

            video_entry = {
                "total_audio_duration": audio_duration,
                "url": first_url,
                "start_time": round(start_offset, 2),
                "end_time": round(start_offset + adjusted_length, 2),
                "length": adjusted_length,
                "type": "video",
            }

            timestamps.append(video_entry)
            log_make_video_message(timestamps)
            return timestamps

        # Nếu video ngắn hơn audio, dùng nó và tiếp tục với ảnh
        video_entry = {
            "total_audio_duration": audio_duration,
            "url": first_url,
            "start_time": round(start_offset, 2),
            "end_time": round(start_offset + video_duration, 2),
            "length": round(video_duration, 2),
            "type": "video",
        }

        timestamps.append(video_entry)
        image_only_list = image_list[1:]
        remaining_duration = (
            audio_duration - video_duration if audio_duration else video_duration
        )
        start_time = video_entry["end_time"]
    else:
        image_only_list = image_list
        remaining_duration = audio_duration
        start_time = round(start_offset, 2)

    if not image_only_list or not remaining_duration or remaining_duration <= 0:
        log_make_video_message(timestamps)
        return timestamps

    # Phân phối thời gian cho ảnh
    num_images = len(image_only_list)
    image_duration = round(remaining_duration / num_images, 2)

    for img_url in image_only_list:
        end_time = round(start_time + image_duration, 2)
        is_gif = first_url.lower().endswith(".gif")

        timestamps.append(
            {
                "total_audio_duration": audio_duration,
                "url": img_url,
                "start_time": start_time,
                "end_time": end_time,
                "length": round(image_duration, 2),
                "type": "gif" if is_gif else "image",
            }
        )
        start_time = end_time

    log_make_video_message(timestamps)
    return timestamps


def merge_emoji_image_with_text(
    emoji_image_path: str,
    label_text: str,
    output_path: str,
    bg_color=(0, 0, 0, 255),
    text_color=(255, 255, 255, 255),
    font_size=30,
    padding=30,
    spacing=30,
    border_radius=30,
    text_font_path="app/makers/fonts/GmarketSansTTFBold.ttf",
    fallback_font_path="app/makers/fonts/Arial.ttf",
):
    # Load emoji ảnh gốc, KHÔNG resize
    emoji_img = Image.open(emoji_image_path).convert("RGBA")

    # Load font chữ
    try:
        text_font = ImageFont.truetype(text_font_path, font_size)
    except:
        text_font = ImageFont.truetype(fallback_font_path, font_size)

    # Đo kích thước text
    text_bbox = text_font.getbbox(label_text)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Tính kích thước toàn ảnh
    total_width = padding * 2 + emoji_img.width + spacing + text_width
    total_height = padding + max(emoji_img.height, text_height)

    # Tạo ảnh RGBA trong suốt
    image = Image.new("RGBA", (total_width, total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Vẽ nền bo góc
    draw.rounded_rectangle(
        [(0, 0), (total_width, total_height)], radius=border_radius, fill=bg_color
    )

    # Dán emoji
    emoji_y = (total_height - emoji_img.height) // 2
    image.paste(emoji_img, (padding, emoji_y), mask=emoji_img)

    # Vẽ text
    text_x = padding + emoji_img.width + spacing
    text_y = (total_height - text_height) // 2
    draw.text((text_x, text_y), label_text, font=text_font, fill=text_color)

    # Lưu file
    image.save(output_path)

    # Tạo đường dẫn file trên server
    current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
    output_file_image_tag = output_path.replace("static/", "").replace("\\", "/")
    file_url = f"{current_domain}/{output_file_image_tag}"

    return file_url


def add_centered_text_to_png(
    text: str,
    output_path: str,
    font_size=24,
    text_color=(255, 255, 255, 255),
    offset_x=10,  # Dịch sang phải (tăng = dịch nhiều hơn)
    text_font_path="app/makers/fonts/GmarketSansTTFBold.ttf",
    fallback_font_path="app/makers/fonts/Arial.ttf",
):
    base_image_path = "app/makers/fonts/emoji_tag_base.png"

    # Mở ảnh gốc (RGBA để giữ alpha)
    base_image = Image.open(base_image_path).convert("RGBA")

    # Tạo một layer trong suốt để vẽ chữ
    text_layer = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(text_layer)

    # Load font
    try:
        font = ImageFont.truetype(text_font_path, font_size)
    except:
        font = ImageFont.truetype(fallback_font_path, font_size)

    # Tính kích thước text
    text_bbox = font.getbbox(text)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Tính vị trí căn giữa + offset
    img_width, img_height = base_image.size
    x = (img_width - text_width) // 2 + offset_x
    y = (img_height - text_height) // 2

    # Vẽ text lên lớp trong suốt
    draw.text((x, y), text, font=font, fill=text_color)

    # Kết hợp lớp text với ảnh gốc (giữ alpha)
    final_image = Image.alpha_composite(base_image, text_layer)

    # Lưu ảnh với alpha
    final_image.save(output_path, format="PNG")
    # Tạo đường dẫn file trên server
    current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
    output_file_image_tag = output_path.replace("static/", "").replace("\\", "/")
    file_url = f"{current_domain}/{output_file_image_tag}"

    return file_url
