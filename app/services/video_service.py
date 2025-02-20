import requests
import json
import os
import random
from app.models.video_create import VideoCreate
from app.models.setting import Setting
from app.lib.logger import logger


class VideoService:

    @staticmethod
    def create_video_from_images(product_name, images_url):
        
        config = VideoService.get_settings()
        SHOTSTACK_API_KEY = config["SHOTSTACK_API_KEY"]
        SHOTSTACK_URL = config["SHOTSTACK_URL"]
        
        print("SHOTSTACK_API_KEY", SHOTSTACK_API_KEY)
        print("SHOTSTACK_URL", SHOTSTACK_URL)
        
        
        print("config", config)
        
        # Danh sách các prompt
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

        payload = {
            "timeline": {
                "background": "#FFFFFF",
                "tracks": [
                    {
                        "clips": [
                            {
                                "asset": {
                                    "type": "image-to-video",
                                    "src": url,
                                    "prompt": random.choice(prompts) if prompts else "",
                                },
                                "start": i * 2,  # Đặt thời gian xuất hiện của mỗi ảnh
                                "length": 2,
                            }
                            for i, url in enumerate(images_url)
                        ]
                    },
                    {
                        "clips": [
                            {
                                "asset": {
                                    "type": "audio",
                                    "src": "https://shotstack-assets.s3-ap-southeast-2.amazonaws.com/music/freepd/motions.mp3",
                                    "effect": "fadeOut",
                                    "volume": 1,
                                },
                                "start": 0,
                                "length": "end",
                            }
                        ]
                    },
                ],
            },
            "output": {"format": "mp4", "size": {"width": 720, "height": 1280}},
            "callback": "https://apitoktak.voda-play.com//api/v1/video_maker/shotstack_webhook",
        }

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
                return result
            else:
                result = response.json()
                logger.error("create video Failed :{0}".format(str(result)))
                return {
                    "message": "Failed to create video",
                    "status_code": response.status_code,
                }

        except Exception as e:
            logger.error("create_video_from_images : Exception: {0}".format(str(e)))
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
        url = f"{SHOTSTACK_URL}/{render_id}"
        headers = {"x-api-key": SHOTSTACK_API_KEY}

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                return {"status": True, "message": "Oke", "data": response.json()}
            else:
                # logger.error(f"API Error {response.status_code}: {response.text}")
                return {"status": False, "message": response.text, "data": []}

        except requests.exceptions.RequestException as e:
            # logger.error(f"Request failed: {str(e)}")
            return {
                "status": False,
                "message": "Request failed, please try again.",
                "data": [],
            }

        except Exception as e:
            # logger.error(f"Unexpected error: {str(e)}")
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
    def get_settings():
        settings = Setting.query.all()
        settings_dict = {
            setting.setting_name: setting.setting_value for setting in settings
        }
        return settings_dict
