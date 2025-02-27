import datetime
import json
import os
import time
import traceback
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
    def exchange_token(access_token, user_link):
        try:
            log_social_message(
                "------------------  EXCHANGE FACEBOOK TOKEN  ------------------"
            )

            EXCHANGE_URL = f"https://graph.facebook.com/v22.0/oauth/access_token"

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

            log_social_message(f"Exchange token response: {data}")

            if "access_token" in data:
                meta = user_link.meta
                meta = json.loads(meta)
                meta.update(data)

                user_link.meta = json.dumps(meta)

                # expires_in = data.get("expires_in")
                # expired_at = time.time() + expires_in
                # user_link.expired_at = datetime.fromtimestamp(expired_at)
                # user_link.expired_date = datetime.fromtimestamp(expired_at).date()

                user_link.save()
                return True
            else:
                user_link.status = 0
                user_link.save()

                log_social_message(f"Error exchanging token: {data}")
                return False

        except Exception as e:
            traceback.print_exc()
            log_social_message(e)
            print(e)
            return False


class FacebookService:
    def __init__(self):
        self.pages = []
        self.photo_ids = []
        self.video_id = ""
        self.url_to_video = ""
        self.user = None
        self.link = None
        self.meta = None

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
        for page in self.pages:
            page_id = page.get("id")
            page_access_token = page.get("access_token")

            result = self.start_session_upload_reel(
                page_id=page_id, page_access_token=page_access_token
            )
            video_id = result["video_id"]

            self.upload_video(
                video_id=video_id,
                video_url=post.video_url,
                access_token=page_access_token,
            )
            result_status = self.get_upload_status(video_id, page_access_token)
            status = result_status.get("status")
            if status == "ready":
                self.publish_the_reel(
                    post=post,
                    video_id=video_id,
                    page_id=page_id,
                    access_token=page_access_token,
                )
                reels = self.get_reel_uploaded(
                    page_id=page_id, access_token=page_access_token
                )
                reel_data = reels.get("data")
                reel_id = reel_data[0].get("id")
                permalink = f"https://www.facebook.com/reel/{reel_id}"

                SocialPostService.create_social_post(
                    link_id=link.id,
                    user_id=post.user_id,
                    post_id=post.id,
                    status="PUBLISHED",
                    social_link=permalink,
                )
            else:
                log_social_message(f"Upload video error: {result_status}")
                video_status = result_status.get("video_status")
                uploading_phase = result_status.get("uploading_phase")

                if video_status == "error":
                    log_social_message("Tình trạng video lỗi. Không thể upload video")
                    SocialPostService.create_social_post(
                        link_id=link.id,
                        user_id=post.user_id,
                        post_id=post.id,
                        status="ERRORED",
                        error_message="Video is error. Can't upload video",
                    )
                if uploading_phase == "error":
                    error_message = uploading_phase.get("error").get("message")
                    log_social_message(error_message)
                    SocialPostService.create_social_post(
                        link_id=link.id,
                        user_id=post.user_id,
                        post_id=post.id,
                        status="ERRORED",
                        error_message=error_message,
                    )
        return True

    def start_session_upload_reel(self, page_id, page_access_token):
        URL_UPLOAD = f"https://graph.facebook.com/v22.0/{page_id}/video_reels"

        post_data = {"upload_phase": "start", "access_token": page_access_token}
        headers = {"Content-Type": "application/json"}

        post_response = requests.post(URL_UPLOAD, data=post_data, headers=headers)
        result = post_response.json()
        return result

    def upload_video(self, video_id, video_url, access_token):
        UPLOAD_VIDEO_URL = f"https://rupload.facebook.com/video-upload/v22.0/{video_id}"
        headers = {
            "Authorization": f"OAuth {access_token}",
            "file_url": video_url,
        }
        post_response = requests.post(UPLOAD_VIDEO_URL, headers=headers)
        result = post_response.json()
        log_social_message(f"Upload video: {result}")

    def get_upload_status(self, video_id, access_token):
        status = None
        try:
            URL_CHECK_STATUS = f"https://graph.facebook.com/v22.0/{video_id}?fields=status&access_token={access_token}"
            get_response = requests.get(URL_CHECK_STATUS)
            result = get_response.json()

            log_social_message(f"get upload status: {result}")

            status = result["status"]
        except Exception as e:
            log_social_message(f"Error get upload status: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
            }

        uploading_phase = status.get("uploading_phase")
        video_status = status.get("video_status", "uploading")
        status_uploading_phase = uploading_phase.get("status")

        if video_status == "upload_complete" and status_uploading_phase == "complete":
            return {
                "status": "ready",
            }
        elif video_status == "error":
            return {
                "status": "error",
                "video_status": video_status,
                "uploading_phase": uploading_phase,
            }
        else:
            return self.get_upload_status(video_id, access_token)

    def publish_the_reel(self, post, video_id, page_id, access_token):
        URL_PUBLISH = f"https://graph.facebook.com/v22.0/{page_id}/video_reels"

        post_data = {
            "upload_phase": "finish",
            "video_id": video_id,
            "access_token": access_token,
            "video_state": "PUBLISHED",
            "description": post.content + " " + post.hashtag,
        }

        final_url = (
            URL_PUBLISH + "?" + "&".join([f"{k}={v}" for k, v in post_data.items()])
        )

        post_response = requests.post(final_url)
        result = post_response.json()
        return result

    def get_reel_uploaded(self, page_id, access_token):
        URL_REEL = f"https://graph.facebook.com/v22.0/{page_id}/video_reels?access_token={access_token}"
        get_response = requests.get(URL_REEL)
        result = get_response.json()
        log_social_message(f"Get reel: {result}")
        return result

    def send_post_image(self, post, link):
        for page in self.pages:
            page_id = page["id"]
            page_access_token = page["access_token"]
            FEED_URL = f"https://graph.facebook.com/v18.0/{page_id}/feed"

            images = post.images
            images = json.loads(images)

            photo_ids = self.unpublish_images(
                images=images, page_id=page_id, page_access_token=page_access_token
            )

            attached_media = [{"media_fbid": pid} for pid in photo_ids]

            log_social_message(f"Attached media: {attached_media}")

            post_data = {
                "message": post.content + " " + post.hashtag,
                "attached_media": json.dumps(attached_media),
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
            post_id = photo_ids[0]

            permalink = f"https://www.facebook.com/photo/?fbid={post_id}"

            SocialPostService.create_social_post(
                link_id=link.id,
                user_id=post.user_id,
                post_id=post.id,
                status="PUBLISHED",
                social_link=permalink,
            )
        return True

    def unpublish_images(self, images, page_id, page_access_token):
        UNPUBLISH_URL = f"https://graph.facebook.com/v22.0/{page_id}/photos"
        photo_ids = []
        for url in images:
            data = {
                "url": url,
                "published": "false",
                "access_token": page_access_token,
            }
            response = requests.post(UNPUBLISH_URL, data=data)
            result = response.json()

            if "id" in result:
                photo_ids.append(result["id"])
            else:
                log_social_message(f"Lỗi upload ảnh: {result}")
        return photo_ids
