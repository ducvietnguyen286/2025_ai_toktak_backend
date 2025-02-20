import json
import requests

from app.services.batch import BatchService


class FacebookService:
    def __init__(self, page_id, access_token):
        self.page_id = page_id
        self.access_token = access_token
        self.photo_ids = []
        self.video_id = ""
        self.url_to_video = ""

    def send_post(self, post):
        if post.type == "social":
            self.send_post_social(post)
        if post.type == "video":
            self.send_post_video(post)

    def send_post_video(self, post):
        self.start_session_upload_reel()

    def start_session_upload_reel(self):
        page_id = self.page_id
        URL_UPLOAD = f"https://graph.facebook.com/v22.0/{page_id}/video_reels"

        post_data = {"upload_phase": "start", "access_token": self.access_token}
        headers = {"Content-Type": "application/json"}

        post_response = requests.post(URL_UPLOAD, data=post_data, headers=headers)
        result = post_response.json()
        self.video_id = result["video_id"]
        self.url_to_video = result["upload_url"]

    def upload_video(self, video_url):
        UPLOAD_VIDEO_URL = (
            f"https://rupload.facebook.com/video-upload/v22.0/{self.video_id}"
        )
        headers = {
            "Authorization": f"OAuth {self.access_token}",
            "file_url": video_url,
        }
        post_response = requests.post(UPLOAD_VIDEO_URL, headers=headers)
        result = post_response.json()
        print("Upload video:", result)

    def get_upload_status(self):
        URL_CHECK_STATUS = f"https://graph.facebook.com/v22.0/{self.video_id}?fields=status&access_token={self.access_token}"
        get_response = requests.get(URL_CHECK_STATUS)
        result = get_response.json()
        print("Check status:", result)
        return result["status"]

    def publish_the_reel(self, post):
        page_id = self.page_id
        URL_PUBLISH = f"https://graph.facebook.com/v22.0/{page_id}/video_reels"

        post_data = {
            "upload_phase": "finish",
            "video_id": self.video_id,
            "access_token": self.access_token,
            "video_state": "PUBLISHED",
            "description": post.title + " " + post.hashtag,
        }

        final_url = (
            URL_PUBLISH + "?" + "&".join([f"{k}={v}" for k, v in post_data.items()])
        )

        post_response = requests.post(final_url)
        result = post_response.json()
        if "success" in result:
            print("Upload video thành công")

        return

    def send_post_social(self, post):
        page_id = self.page_id
        FEED_URL = f"https://graph.facebook.com/{page_id}/feed"

        images = [post.thumbnail]

        self.unpublish_images(images)

        attached_media = [{"media_fbid": pid} for pid in self.photo_ids]

        post_data = {
            "message": post.content + " " + post.hashtag,
            "attached_media": json.dumps(attached_media),
            "access_token": self.access_token,
        }
        post_response = requests.post(FEED_URL, data=post_data)
        result = post_response.json()
        print(result)

    def unpublish_images(self, images):
        page_id = self.page_id
        UNPUBLISH_URL = f"https://graph.facebook.com/{page_id}/photos"

        for path in images:
            response = requests.get(path)
            if response.status_code == 200:
                files = {"source": response.content}
                data = {
                    "published": "false",
                    "access_token": self.access_token,
                }
                response = requests.post(UNPUBLISH_URL, data=data, files=files)
                result = response.json()
                if "id" in result:
                    self.photo_ids.append(result["id"])
                else:
                    print("Lỗi upload ảnh:", result)
            else:
                print("Lỗi tải ảnh:", response.status_code)
