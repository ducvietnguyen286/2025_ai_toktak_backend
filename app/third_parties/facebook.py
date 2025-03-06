import datetime
import json
import os
import time
import traceback
import requests

from app.lib.logger import log_facebook_message
from app.services.request_social_log import RequestSocialLogService
from app.services.social_post import SocialPostService
from app.services.user import UserService
from app.third_parties.base_service import BaseService


class FacebookTokenService:
    def __init__(self):
        pass

    @staticmethod
    def fetch_page_token(user_link):
        try:
            log_facebook_message(
                "------------------  FETCH FACEBOOK PAGE TOKEN  ------------------"
            )

            meta = json.loads(user_link.meta)
            access_token = meta.get("access_token")
            if not access_token:
                log_facebook_message("Token not found")
                return None

            PAGE_URL = f"https://graph.facebook.com/v22.0/me/accounts?access_token={access_token}&fields=id,name,picture,access_token,tasks"

            response = requests.get(PAGE_URL)
            data = response.json()

            RequestSocialLogService.create_request_social_log(
                social="FACEBOOK",
                social_post_id="",
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
            log_facebook_message(e)
            return None

    @staticmethod
    def fetch_page_token_backend(user_link, page_id, is_all=None):
        try:
            log_facebook_message(
                "------------------  FETCH FACEBOOK PAGE TOKEN  ------------------"
            )

            meta = json.loads(user_link.meta)
            access_token = meta.get("access_token")
            if not access_token:
                log_facebook_message("Token not found")
                return None

            PAGE_URL = f"https://graph.facebook.com/v22.0/me/accounts?access_token={access_token}&fields=id,name,picture,access_token,tasks"

            response = requests.get(PAGE_URL)
            data = response.json()

            RequestSocialLogService.create_request_social_log(
                social="FACEBOOK",
                social_post_id="",
                user_id=user_link.user_id,
                type="fetch_page_token",
                request=json.dumps({"access_token": access_token}),
                response=json.dumps(data),
            )

            if "data" not in data:
                user_link.status = 0
                user_link.save()
                return None

            log_facebook_message(
                f"------------------  FACEBOOK PAGES ------------------ : {data}"
            )

            log_facebook_message(
                f"------------------  FACEBOOK PAGE ID INPUT ------------------ : {page_id}"
            )
            if is_all:
                first_page = data.get("data")[0]
                log_facebook_message(
                    f"------------------  FACEBOOK PAGE ------------------ : {first_page}"
                )
                return first_page
            for page in data.get("data"):
                if page.get("id") == page_id:
                    return page.get("access_token")

        except Exception as e:
            log_facebook_message(e)
            return None

    @staticmethod
    def fetch_user_info(user_link):
        try:
            log_facebook_message(
                "------------------  GET FACEBOOK USER INFO BY TOKEN  ------------------"
            )
            user_link = UserService.find_user_link(
                link_id=user_link.id, user_id=user_link.user_id
            )
            meta = json.loads(user_link.meta)
            access_token = meta.get("access_token")
            if not access_token:
                log_facebook_message("Token not found")
                return None

            USER_URL = f"https://graph.facebook.com/v22.0/me?access_token={access_token}&fields=id,name,email,picture"
            response = requests.get(USER_URL)
            data = response.json()

            RequestSocialLogService.create_request_social_log(
                social="FACEBOOK",
                social_post_id="",
                user_id=user_link.user_id,
                type="get_user_info_by_token",
                request=json.dumps({"access_token": access_token}),
                response=json.dumps(data),
            )

            log_facebook_message(f"User info: {data}")
            return {
                "id": data.get("id") or "",
                "name": data.get("name") or "",
                "avatar": data.get("picture").get("data").get("url") or "",
                "url": f"https://facebook.com/profile.php?id={data.get('id')}" or "",
            }

        except Exception as e:
            log_facebook_message(e)
            return None

    @staticmethod
    def exchange_token(access_token, user_link):
        try:
            log_facebook_message(
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
                social_post_id="",
                user_id=user_link.user_id,
                type="refresh_token",
                request=json.dumps(params),
                response=json.dumps(data),
            )

            log_facebook_message(f"Exchange token response: {data}")

            if "access_token" in data:
                meta = user_link.meta
                meta = json.loads(meta)
                meta.update(data)

                user_link.meta = json.dumps(meta)

                expires_in = 60 * 60 * 24 * 60  # 60 days
                expired_at = time.time() + expires_in
                user_link.expired_at = datetime.datetime.fromtimestamp(expired_at)
                user_link.expired_date = datetime.datetime.fromtimestamp(
                    expired_at
                ).date()

                user_link.save()
                return True
            else:
                user_link.status = 0
                user_link.save()

                log_facebook_message(f"Error exchanging token: {data}")
                return False

        except Exception as e:
            traceback.print_exc()
            log_facebook_message(e)
            return False


class FacebookService(BaseService):

    def __init__(self):
        self.pages = []
        self.photo_ids = []
        self.video_id = ""
        self.url_to_video = ""
        self.user = None
        self.link = None
        self.meta = None
        self.social_post = None
        self.page_id = None
        self.page_token = None
        self.access_token = None
        self.link_id = None
        self.post_id = None
        self.batch_id = None
        self.social_post_id = ""
        self.service = "FACEBOOK"
        self.key_log = ""

    def send_post(self, post, link, user_id, social_post_id, page_id, is_all=None):
        self.user = UserService.find_user(user_id)
        self.link = link
        self.user_link = UserService.find_user_link(link_id=link.id, user_id=user_id)
        self.meta = json.loads(self.user_link.meta)
        self.access_token = self.meta.get("access_token")
        self.social_post = SocialPostService.find_social_post(social_post_id)
        self.link_id = link.id
        self.post_id = post.id
        self.batch_id = post.batch_id
        self.social_post_id = str(self.social_post.id)
        self.key_log = f"{self.post_id} - {self.social_post.session_key}"

        token_page = FacebookTokenService.fetch_page_token_backend(
            self.user_link, page_id, is_all
        )

        if not is_all and not token_page:
            self.save_errors("ERRORED", "SEND POST ERROR NOT ALL: Can't get page token")
            return True
        else:
            if not token_page:
                self.save_errors("ERRORED", "SEND POST ERROR ALL: Can't get page token")
                return True
            response_token = token_page
            page_id = response_token.get("id")
            token_page = response_token.get("access_token")

        self.page_id = page_id
        self.page_token = token_page

        try:
            self.save_uploading(0)
            log_facebook_message(
                f"------------ READY TO SEND POST: {post._to_json()} ----------------"
            )

            if post.type == "image":
                self.send_post_image(post, link)
            if post.type == "video":
                self.send_post_video(post, link)
            return True
        except Exception as e:
            self.save_errors("ERRORED", f"SEND POST {self.key_log}: {str(e)}")
            return True

    def send_post_video(self, post, link):
        page_id = self.page_id
        page_access_token = self.page_token

        result = self.start_session_upload_reel(
            page_id=page_id, page_access_token=page_access_token
        )
        video_id = result["video_id"] if "video_id" in result else None
        if not video_id:
            error = result.get("error", {})
            error_message = error.get(
                "message",
                f"POST {self.key_log} : Can't Start Start Session Upload Reel",
            )
            self.save_errors(
                "ERRORED", f"SEND POST {self.key_log} VIDEO: {error_message}"
            )

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
            if not reels:
                self.save_publish("PUBLISHED", "profile")
                return True

            reel_data = reels.get("data")
            reel_id = reel_data[0].get("id")
            permalink = f"https://www.facebook.com/reel/{reel_id}"

            self.save_publish("PUBLISHED", permalink)
            return True
        else:
            log_facebook_message(
                f"POST: {self.key_log} Upload video error: {result_status}"
            )
            video_status = result_status.get("video_status")
            uploading_phase = result_status.get("uploading_phase")

            if video_status == "error":
                self.save_errors(
                    "ERRORED",
                    f"SEND POST {self.key_log} VIDEO: Video is error. Can't upload video",
                )
            if uploading_phase == "error":
                error_message = uploading_phase.get("error").get("message")
                self.save_errors(
                    "ERRORED", f"SEND POST {self.key_log} VIDEO: {error_message}"
                )
            return False

    def start_session_upload_reel(self, page_id, page_access_token):
        URL_UPLOAD = f"https://graph.facebook.com/v22.0/{page_id}/video_reels"

        post_data = {"upload_phase": "start", "access_token": page_access_token}
        headers = {"Content-Type": "application/json"}
        try:
            post_response = requests.post(URL_UPLOAD, data=post_data, headers=headers)
        except Exception as e:
            self.save_errors(
                "ERRORED", f"POST {self.key_log} : START SESSION UPLOAD REEL: {str(e)}"
            )
            return False

        result = post_response.json()
        RequestSocialLogService.create_request_social_log(
            social="FACEBOOK",
            social_post_id=self.social_post_id,
            user_id=self.user.id,
            type="start_session_upload_reel",
            request=json.dumps(post_data),
            response=json.dumps(result),
        )

        self.save_uploading(10)

        return result

    def upload_video(self, video_id, video_url, access_token):
        UPLOAD_VIDEO_URL = f"https://rupload.facebook.com/video-upload/v22.0/{video_id}"
        headers = {
            "Authorization": f"OAuth {access_token}",
            "file_url": video_url,
        }
        try:
            post_response = requests.post(UPLOAD_VIDEO_URL, headers=headers)
        except Exception as e:
            self.save_errors("ERRORED", f"POST {self.key_log}: UPLOAD VIDEO: {str(e)}")
            return False

        result = post_response.json()
        RequestSocialLogService.create_request_social_log(
            social="FACEBOOK",
            social_post_id=self.social_post_id,
            user_id=self.user.id,
            type="upload_video",
            request=json.dumps(headers),
            response=json.dumps(result),
        )
        self.save_uploading(20)
        log_facebook_message(f"Upload video: {result}")

    def get_upload_status(self, video_id, access_token, count=1):
        status = None

        try:
            URL_CHECK_STATUS = f"https://graph.facebook.com/v22.0/{video_id}?fields=status&access_token={access_token}"
            try:
                get_response = requests.get(URL_CHECK_STATUS)
            except Exception as e:
                self.save_errors(
                    "ERRORED", f"POST {self.key_log}: GET UPLOAD STATUS: {str(e)}"
                )
                return {
                    "status": "error",
                    "error": str(e),
                }

            result = get_response.json()

            log_facebook_message(f"POST {self.key_log}: get upload status: {result}")

            status = result["status"]

            time.sleep(1)

            if count <= 6:
                self.save_uploading(20 + (count * 10))

        except Exception as e:
            self.save_errors(
                "ERRORED", f"POST {self.key_log}: GET UPLOAD STATUS - EROROR: {str(e)}"
            )
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
            return self.get_upload_status(video_id, access_token, count + 1)

    def publish_the_reel(self, post, video_id, page_id, access_token):
        URL_PUBLISH = f"https://graph.facebook.com/v22.0/{page_id}/video_reels"

        post_data = {
            "upload_phase": "finish",
            "video_id": video_id,
            "access_token": access_token,
            "video_state": "PUBLISHED",
            "description": post.description + " " + post.hashtag,
        }

        final_url = (
            URL_PUBLISH + "?" + "&".join([f"{k}={v}" for k, v in post_data.items()])
        )
        try:
            post_response = requests.post(final_url)
        except Exception as e:
            self.save_errors(
                "ERRORED", f"POST {self.key_log}: PUBLISH THE REEL: {str(e)}"
            )
            return False

        result = post_response.json()
        RequestSocialLogService.create_request_social_log(
            social="FACEBOOK",
            social_post_id=self.social_post_id,
            user_id=self.user.id,
            type="publish_the_reel",
            request=json.dumps(post_data),
            response=json.dumps(result),
        )

        self.save_uploading(90)

        return result

    def get_reel_uploaded(self, page_id, access_token):
        URL_REEL = f"https://graph.facebook.com/v22.0/{page_id}/video_reels?access_token={access_token}"
        try:
            get_response = requests.get(URL_REEL)
        except Exception as e:
            self.save_errors(
                "ERRORED", f"POST {self.key_log}: GET REEL UPLOADED: {str(e)}"
            )
            return False

        result = get_response.json()
        RequestSocialLogService.create_request_social_log(
            social="FACEBOOK",
            social_post_id=self.social_post_id,
            user_id=self.user.id,
            type="get_reel_uploaded",
            request=json.dumps({"page_id": page_id}),
            response=json.dumps(result),
        )
        log_facebook_message(f"Get reel: {result}")
        return result

    def send_post_image(self, post, link):
        page_id = self.page_id
        page_access_token = self.page_token

        log_facebook_message(f"page_id: {page_id}")
        log_facebook_message(f"page_access_token: {page_access_token}")

        FEED_URL = f"https://graph.facebook.com/v22.0/{page_id}/feed"

        images = post.images
        images = json.loads(images)

        photo_ids = self.unpublish_images(
            images=images, page_id=page_id, page_access_token=page_access_token
        )
        if not photo_ids:
            return False

        attached_media = [{"media_fbid": pid} for pid in photo_ids]

        log_facebook_message(f"POST {self.key_log}: Attached media: {attached_media}")

        post_data = {
            "message": post.description + " " + post.hashtag,
            "attached_media": json.dumps(attached_media),
            "access_token": page_access_token,
        }

        log_facebook_message(f"POST {self.key_log}: post_data: {post_data}")
        try:
            post_response = requests.post(FEED_URL, data=post_data)
        except Exception as e:
            self.save_errors(
                "ERRORED",
                f"SEND POST {self.key_log} IMAGE - REQUEST FEED URL: {str(e)}",
            )
            return False
        result = post_response.json()

        RequestSocialLogService.create_request_social_log(
            social="FACEBOOK",
            social_post_id=self.social_post_id,
            user_id=self.user.id,
            type="send_post_image",
            request=json.dumps(post_data),
            response=json.dumps(result),
        )

        log_facebook_message(f"POST {self.key_log} result: {result}")

        if "id" not in result:
            error = result.get("error", {})
            error_message = error.get("message", "Error")
            self.save_errors(
                "ERRORED", f"SEND POST {self.key_log} IMAGE: {error_message}"
            )

            return False
        post_id = photo_ids[0]

        permalink = f"https://www.facebook.com/photo/?fbid={post_id}"

        self.save_publish("PUBLISHED", permalink)
        return True

    def unpublish_images(self, images, page_id, page_access_token):
        UNPUBLISH_URL = f"https://graph.facebook.com/v22.0/{page_id}/photos"
        photo_ids = []

        progress = 0
        progress_per_image = 80 / len(images)

        for url in images:
            data = {
                "url": url,
                "published": "false",
                "access_token": page_access_token,
            }
            try:
                response = requests.post(UNPUBLISH_URL, data=data)
            except Exception as e:
                self.save_errors(
                    "ERRORED", f"POST {self.key_log} UNPUBLISH IMAGES: {str(e)}"
                )
                return False

            result = response.json()

            RequestSocialLogService.create_request_social_log(
                social="FACEBOOK",
                social_post_id=self.social_post_id,
                user_id=self.user.id,
                type="unpublish_images",
                request=json.dumps(data),
                response=json.dumps(result),
            )

            progress += progress_per_image

            self.save_uploading(progress)

            if "id" in result:
                photo_ids.append(result["id"])
            else:
                error = result.get("error", {})
                error_message = error.get("message", "Error")
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UNPUBLISH IMAGES - GET ERROR: {error_message}",
                )
        return photo_ids
