import json
import time
import requests

from app.lib.logger import logger
from app.services.social_post import SocialPostService


class FacebookService:
    def __init__(self, page_id, access_token):
        self.page_id = page_id
        self.access_token = access_token
        self.photo_ids = []
        self.video_id = ""
        self.url_to_video = ""

    def send_post(self, post, link):
        if post.type == "social":
            self.send_post_social(post, link)
        if post.type == "video":
            self.send_post_video(post, link)

    def send_post_video(self, post, link):
        self.start_session_upload_reel()
        self.upload_video(post.video_url)
        while True:
            status = self.get_upload_status()
            processing_phase = status.get("processing_progress")
            publishing_phase = status.get("publishing_phase")
            uploading_phase = status.get("uploading_phase")
            video_status = status.get("video_status", "uploading")

            status_processing_phase = processing_phase.get("status")
            status_publishing_phase = publishing_phase.get("status")
            status_uploading_phase = uploading_phase.get("status")

            if (
                video_status == "ready"
                and status_processing_phase == "completed"
                and status_publishing_phase == "published"
                and status_uploading_phase == "complete"
            ):
                self.publish_the_reel(post)
                reels = self.get_reel_uploaded()
                break

            if (
                video_status == "error"
                or status_processing_phase == "error"
                or status_publishing_phase == "error"
                or status_uploading_phase == "error"
            ):
                logger.error("Error upload video")
                if video_status == "error":
                    logger.error("Tình trạng video lỗi. Không thể upload video")
                    SocialPostService.create_social_post(
                        link_id=link.id,
                        user_id=post.user_id,
                        post_id=post.id,
                        status="ERRORED",
                        error_message="Video is error. Can't upload video",
                    )
                if status_processing_phase == "error":
                    error_message = processing_phase.get("error").get("message")
                    logger.error(error_message)
                    SocialPostService.create_social_post(
                        link_id=link.id,
                        user_id=post.user_id,
                        post_id=post.id,
                        status="ERRORED",
                        error_message=error_message,
                    )

                if status_publishing_phase == "error":
                    error_message = publishing_phase.get("error").get("message")
                    logger.error(error_message)
                    SocialPostService.create_social_post(
                        link_id=link.id,
                        user_id=post.user_id,
                        post_id=post.id,
                        status="ERRORED",
                        error_message=error_message,
                    )
                if status_uploading_phase == "error":
                    error_message = uploading_phase.get("error").get("message")
                    logger.error(error_message)
                    SocialPostService.create_social_post(
                        link_id=link.id,
                        user_id=post.user_id,
                        post_id=post.id,
                        status="ERRORED",
                        error_message=error_message,
                    )
                break

            time.sleep(1)

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
        return result

    def get_reel_uploaded(self):
        URL_REEL = f"https://graph.facebook.com/v22.0/{self.page_id}/video_reels?access_token={self.access_token}"
        get_response = requests.get(URL_REEL)
        result = get_response.json()
        print("Get reel:", result)
        return result

    def send_post_social(self, post, link):
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
        if "id" not in result:
            error = result.get("error", {})
            error_message = error.get("message", "Error")
            SocialPostService.create_social_post(
                link_id=link.id,
                user_id=post.user_id,
                post_id=post.id,
                status="ERRORED",
                error_message=error_message,
            )
            return False
        post_id = result["id"]

        PERMALINK_URL = f"https://graph.facebook.com/{post_id}"
        params = {"fields": "permalink_url", "access_token": self.access_token}

        response_permalink = requests.get(PERMALINK_URL, params=params)
        result_permalink = response_permalink.json()

        permalink = result_permalink["permalink_url"]
        SocialPostService.create_social_post(
            link_id=link.id,
            user_id=post.user_id,
            post_id=post.id,
            status="PUBLISHED",
            social_link=permalink,
        )
        return True

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
