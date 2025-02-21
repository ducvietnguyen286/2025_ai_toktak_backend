import json

import requests
from app.services.user import UserService


class TiktokService:

    def __init__(self):
        self.user_link = None
        self.user = None
        self.link = None
        self.meta = None
        self.processing_info = None

    def send_post(self, post, link):
        user_id = post.user_id
        self.user = UserService.find_user(user_id)
        self.link = link
        self.user_link = UserService.find_user_link(link_id=link.id, user_id=user_id)
        self.meta = json.loads(self.user_link.meta)

        if post.type == "video":
            self.upload_video(post.video_url)

    def upload_video(self, media):
        try:
            print("Upload video to Tiktok")
            upload_info = self.upload_video_init(media)
            print("Upload video info:", upload_info)
            info_data = upload_info.get("data")

            # FILE INFO
            response = requests.get(media)
            total_bytes = int(response.headers.get("content-length", 0))
            media_type = response.headers.get("content-type")

            upload_url = info_data.get("upload_url")
            publish_id = info_data.get("publish_id")

            video_file = response.content
            headers = {
                "Content-Range": f"bytes 0-{total_bytes - 1}/{total_bytes}",
                "Content-Type": media_type,
            }
            requests.put(upload_url, headers=headers, data=video_file)
            print("Upload video")
            self.check_status(publish_id)
            print("Upload video success")
        except Exception as e:
            print(f"Error upload video to Tiktok: {str(e)}")

    def check_status(self, publish_id):
        access_token = self.meta.get("access_token")
        URL_VIDEO_STATUS = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {"publish_id": publish_id}
        response = requests.post(URL_VIDEO_STATUS, headers=headers, data=payload)
        res_json = response.json()
        status = res_json.get("data").get("status")
        if status == "PUBLISH_COMPLETE":
            return True
        return self.check_status(publish_id)

    def upload_video_init(self, media):
        print("Upload video to Tiktok INIT")
        access_token = self.meta.get("access_token")
        URL_VIDEO_UPLOAD = (
            "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": media,
            }
        }

        response = requests.post(URL_VIDEO_UPLOAD, headers=headers, data=payload)
        return response.json()
