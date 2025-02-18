import requests
import json
import os

# Lấy API Key từ môi trường hoặc .env
SHOTSTACK_API_KEY = os.getenv("SHOTSTACK_API_KEY")

# URL của Shotstack API

SHOTSTACK_URL = os.getenv("SHOTSTACK_URL")


def create_video_from_images(product_name, images_url):
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
                                "prompt": "Slowly zoom in and out for a dramatic effect.",
                            },
                            "start": i * 2,  # Đặt thời gian xuất hiện của mỗi ảnh
                            "length": 2,
                        }
                        for i, url in enumerate(images_url)
                    ]
                }
            ],
        },
        "output": {"format": "mp4", "size": {"width": 720, "height": 1280}},
    }

    # Header với API Key
    headers = {"x-api-key": SHOTSTACK_API_KEY, "Content-Type": "application/json"}

    try:
        
        print(json.dumps(payload))
        # Gửi yêu cầu POST đến Shotstack API
        response = requests.post(
            SHOTSTACK_URL, headers=headers, data=json.dumps(payload)
        )

        # Kiểm tra trạng thái phản hồi
        print(response.json())
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            return {
                "message": "Failed to create video",
                "status_code": response.status_code,
            }

    except Exception as e:
        return {
            "message": str(e),
            "status_code": 500,
        }
