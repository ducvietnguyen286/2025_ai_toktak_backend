import json
import os
import time
import requests

from app.lib.logger import log_social_message
from app.services.request_social_log import RequestSocialLogService
from app.services.social_post import SocialPostService
from app.services.user import UserService


class FacebookTokenService:
    def __init__(self):
        pass

    @staticmethod
    def fetch_page_token(user_link):
        try:
            log_social_message(
                "------------------  FETCH FACEBOOK PAGE TOKEN  ------------------"
            )

            meta = json.loads(user_link.meta)
            log_social_message(f"Meta: {meta}")
            access_token = meta.get("AccessToken")
            log_social_message(f"AccessToken: {access_token}")
            if not access_token:
                access_token = meta.get("access_token")
                if not access_token:
                    log_social_message("Token not found")
                    return None

            PAGE_URL = f"https://graph.facebook.com/v22.0/me/accounts?access_token={access_token}&fields=id,name,picture,access_token,tasks"

            response = requests.get(PAGE_URL)
            data = response.json()

            RequestSocialLogService.create_request_social_log(
                social="FACEBOOK",
                user_id=user_link.user_id,
                type="fetch_page_token",
                request=json.dumps({"access_token": access_token}),
                response=json.dumps(data),
            )

            if "data" not in data:
                user_link.status = 0
                user_link.save()
                return None

            return data.get("data")

        except Exception as e:
            log_social_message(e)
            return None

    @staticmethod
    def exchange_token(user_link):
        try:
            log_social_message(
                "------------------  EXCHANGE FACEBOOK TOKEN  ------------------"
            )
            meta = json.loads(user_link.meta)
            access_token = meta.get("AccessToken")
            if not access_token:
                access_token = meta.get("access_token")
                if not access_token:
                    log_social_message("Token not found")
                    return None

            EXCHANGE_URL = f"https://graph.facebook.com/v14.0/oauth/access_token"

            CLIENT_ID = os.environ.get("FACEBOOK_APP_ID") or ""
            CLIENT_SECRET = os.environ.get("FACEBOOK_APP_SECRET") or ""

            params = {
                "grant_type": "fb_exchange_token",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "fb_exchange_token": access_token,
            }

            response = requests.get(EXCHANGE_URL, params=params)
            data = response.json()

            RequestSocialLogService.create_request_social_log(
                social="FACEBOOK",
                user_id=user_link.user_id,
                type="refresh_token",
                request=json.dumps(params),
                response=json.dumps(data),
            )

            log_social_message("Exchange token response:", data)

            if "access_token" in data:
                meta = user_link.meta
                meta = json.loads(meta)
                meta.update(data)

                user_link.meta = json.dumps(meta)
                user_link.save()
                return data
            else:
                user_link.status = 0
                user_link.save()

                log_social_message("Error exchanging token:", data)
                return None

        except Exception as e:
            log_social_message(e)


class FacebookService:
    def __init__(self):
        self.pages = []
        self.photo_ids = []
        self.video_id = ""
        self.url_to_video = ""
        self.user = None
        self.link = None
        self.meta = None
        self.page_id = None
        self.access_token = None

    def send_post(self, post, link):
        user_id = post.user_id
        self.user = UserService.find_user(user_id)
        self.link = link
        self.user_link = UserService.find_user_link(link_id=link.id, user_id=user_id)
        self.meta = json.loads(self.user_link.meta)
        access_token = self.meta.get("AccessToken")
        if not access_token:
            access_token = self.meta.get("access_token")
        self.access_token = access_token

        token_pages = FacebookTokenService.fetch_page_token(self.user_link)
        if not token_pages:
            log_social_message("Token not found")

        log_social_message(f"Token pages: {token_pages}")

        for page in token_pages:
            tasks = page.get("tasks", [])
            if "CREATE_CONTENT" not in tasks:
                continue

            page_access = {
                "id": page.get("id"),
                "access_token": page.get("access_token"),
            }
            self.pages.append(page_access)

        if post.type == "image":
            self.send_post_image(post, link)
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
                #: TODO: Get the reel id and permalink to reel. Save to database with status PUBLISHED
                break

            if (
                video_status == "error"
                or status_processing_phase == "error"
                or status_publishing_phase == "error"
                or status_uploading_phase == "error"
            ):
                log_social_message("Error upload video")
                if video_status == "error":
                    log_social_message("Tình trạng video lỗi. Không thể upload video")
                    SocialPostService.create_social_post(
                        link_id=link.id,
                        user_id=post.user_id,
                        post_id=post.id,
                        status="ERRORED",
                        error_message="Video is error. Can't upload video",
                    )
                if status_processing_phase == "error":
                    error_message = processing_phase.get("error").get("message")
                    log_social_message(error_message)
                    SocialPostService.create_social_post(
                        link_id=link.id,
                        user_id=post.user_id,
                        post_id=post.id,
                        status="ERRORED",
                        error_message=error_message,
                    )

                if status_publishing_phase == "error":
                    error_message = publishing_phase.get("error").get("message")
                    log_social_message(error_message)
                    SocialPostService.create_social_post(
                        link_id=link.id,
                        user_id=post.user_id,
                        post_id=post.id,
                        status="ERRORED",
                        error_message=error_message,
                    )
                if status_uploading_phase == "error":
                    error_message = uploading_phase.get("error").get("message")
                    log_social_message(error_message)
                    SocialPostService.create_social_post(
                        link_id=link.id,
                        user_id=post.user_id,
                        post_id=post.id,
                        status="ERRORED",
                        error_message=error_message,
                    )
                break

            time.sleep(1)
        return True

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
        log_social_message("Upload video:", result)

    def get_upload_status(self):
        URL_CHECK_STATUS = f"https://graph.facebook.com/v22.0/{self.video_id}?fields=status&access_token={self.access_token}"
        get_response = requests.get(URL_CHECK_STATUS)
        result = get_response.json()
        log_social_message("Check status:", result)
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
        log_social_message("Get reel:", result)
        return result

    def send_post_image(self, post, link):
        for page in self.pages:
            page_id = page["id"]
            page_access_token = page["access_token"]
            FEED_URL = f"https://graph.facebook.com/v18.0/{page_id}/feed"

            images = post.images
            images = json.loads(images)

            self.unpublish_images(images)

            attached_media = [{"media_fbid": pid} for pid in self.photo_ids]

            log_social_message(f"Attached media: {attached_media}")

            post_data = {
                "message": post.content + " " + post.hashtag,
                "attached_media": attached_media,
                "access_token": page_access_token,
            }

            log_social_message(f"post_data: {post_data}")

            post_response = requests.post(FEED_URL, data=post_data)
            result = post_response.json()

            log_social_message(f"result: {result}")

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
        for page in self.pages:
            page_id = page["id"]
            page_access_token = page["access_token"]

            UNPUBLISH_URL = f"https://graph.facebook.com/v22.0/{page_id}/photos"

            for url in images:
                data = {
                    "url": url,
                    "published": "false",
                    "access_token": page_access_token,
                }
                response = requests.post(UNPUBLISH_URL, data=data)
                result = response.json()
                if "id" in result:
                    self.photo_ids.append(result["id"])
                else:
                    log_social_message(f"Lỗi upload ảnh: {result}")
