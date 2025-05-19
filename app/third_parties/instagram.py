import datetime
import json
import os
import time
import traceback

import requests
from app.enums.limit import LimitSNS
from app.lib.logger import log_instagram_message
from app.services.request_social_log import RequestSocialLogService
from app.services.social_post import SocialPostService
from app.services.user import UserService
from app.third_parties.base_service import BaseService


class InstagramTokenService:

    @staticmethod
    def exchange_code(code, user_link):
        try:
            log_instagram_message(
                "------------------  EXCHANGE INSTAGRAM CODE  ------------------"
            )

            EXCHANGE_URL = f"https://api.instagram.com/oauth/access_token"

            CLIENT_ID = os.environ.get("INSTAGRAM_APP_ID") or ""
            CLIENT_SECRET = os.environ.get("INSTAGRAM_APP_SECRET") or ""
            REDIRECT_URL = os.environ.get("INSTAGRAM_REDIRECT_URL") or ""

            body = {
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URL,
                "code": code,
            }

            response = requests.post(EXCHANGE_URL, data=body)
            data = response.json()

            RequestSocialLogService.create_request_social_log(
                social="INSTAGRAM",
                social_post_id="",
                user_id=user_link.user_id,
                type="authorization_code",
                request=json.dumps(body),
                response=json.dumps(data),
            )

            log_instagram_message(f"Exchange code response: {data}")

            if "access_token" in data:
                meta = user_link.meta
                meta = json.loads(meta)
                meta.update(data)

                user_link.meta = json.dumps(meta)
                user_link.save()
                return True
            else:
                # user_link.status = 0
                # user_link.save()

                log_instagram_message(f"Error exchanging code: {data}")
                return False

        except Exception as e:
            traceback.print_exc()
            log_instagram_message(e)
            return False

    @staticmethod
    def exchange_long_live_token(user_link):
        try:
            log_instagram_message(
                "------------------  EXCHANGE INSTAGRAM TOKEN  ------------------"
            )
            user_link = UserService.find_user_link_by_id(user_link.id)
            meta = json.loads(user_link.meta)
            access_token = meta.get("access_token")

            EXCHANGE_URL = f"https://graph.instagram.com/access_token"

            CLIENT_SECRET = os.environ.get("INSTAGRAM_APP_SECRET") or ""

            params = {
                "grant_type": "ig_exchange_token",
                "client_secret": CLIENT_SECRET,
                "access_token": access_token,
            }

            response = requests.get(EXCHANGE_URL, params=params)
            data = response.json()

            RequestSocialLogService.create_request_social_log(
                social="INSTAGRAM",
                social_post_id="",
                user_id=user_link.user_id,
                type="exchange_token",
                request=json.dumps(params),
                response=json.dumps(data),
            )

            log_instagram_message(f"Exchange token response: {data}")

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
                # user_link.status = 0
                # user_link.save()

                log_instagram_message(f"Error exchanging token: {data}")
                return False

        except Exception as e:
            traceback.print_exc()
            log_instagram_message(e)
            return False

    @staticmethod
    def refresh_token(access_token, user_link):
        try:
            log_instagram_message(
                "------------------  REFRESH INSTAGRAM TOKEN  ------------------"
            )
            EXCHANGE_URL = f"https://graph.instagram.com/refresh_access_token"

            params = {
                "grant_type": "ig_refresh_token",
                "access_token": access_token,
            }

            response = requests.get(EXCHANGE_URL, params=params)
            data = response.json()

            RequestSocialLogService.create_request_social_log(
                social="INSTAGRAM",
                social_post_id="",
                user_id=user_link.user_id,
                type="refresh_token",
                request=json.dumps(params),
                response=json.dumps(data),
            )

            log_instagram_message(f"Refresh token response: {data}")

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
                # user_link.status = 0
                # user_link.save()

                log_instagram_message(f"Error exchanging token: {data}")
                return False
        except Exception as e:
            traceback.print_exc()
            log_instagram_message(e)
            return False

    @staticmethod
    def get_info(user_link):
        try:
            log_instagram_message(
                "------------------  GET INSTAGRAM USER INFO  ------------------"
            )
            user_link = UserService.find_user_link_by_id(user_link.id)
            meta = json.loads(user_link.meta)
            access_token = meta.get("access_token")

            INFO_URL = f"https://graph.instagram.com/v22.0/me"

            params = {
                "fields": "id,username,profile_picture_url",
                "access_token": access_token,
            }

            response = requests.get(INFO_URL, params=params)
            data = response.json()

            RequestSocialLogService.create_request_social_log(
                social="INSTAGRAM",
                social_post_id="",
                user_id=user_link.user_id,
                type="get_info",
                request=json.dumps(params),
                response=json.dumps(data),
            )

            log_instagram_message(f"Get info response: {data}")

            username = data.get("username") or ""
            profile_url = f"https://instagram.com/{username}"

            return {
                "id": data.get("id") or "",
                "username": username,
                "name": username,
                "avatar": data.get("profile_picture_url") or "",
                "url": profile_url,
            }
        except Exception as e:
            traceback.print_exc()
            log_instagram_message(e)
            return False


class InstagramService(BaseService):
    def __init__(self, sync_id=""):
        self.sync_id = sync_id
        self.user_link = None
        self.user = None
        self.link = None
        self.meta = None
        self.social_post = None
        self.user_id = None
        self.link_id = None
        self.post_id = None
        self.batch_id = None
        self.service = "INSTAGRAM"

    def send_post(self, post, link, user_id, social_post_id):
        self.user = UserService.find_user(user_id)
        self.link = link
        self.user_link = UserService.find_user_link(link_id=link.id, user_id=user_id)
        self.meta = json.loads(self.user_link.meta)
        self.access_token = self.meta.get("access_token")
        self.social_post = SocialPostService.find_social_post(social_post_id)
        self.post_id = str(post.id)
        self.batch_id = str(post.batch_id)
        self.batch_id = post.batch_id
        self.social_post_id = str(self.social_post.id)
        self.istagram_user_id = self.user_link.social_id
        self.key_log = f"{self.post_id} - {self.social_post.session_key}"

        try:
            self.save_uploading(0)
            log_instagram_message(
                f"------------ READY TO SEND POST: {post.to_json()} ----------------"
            )

            if post.type == "image":
                self.send_post_image(post)
            if post.type == "video":
                self.send_post_video(post)
            return True
        except Exception as e:
            self.save_errors("ERRORED", f"SEND POST {self.key_log}: {str(e)}")
            return True

    def send_post_image(self, post):
        try:
            text = (
                (
                    post.description
                    if post.description and post.description != ""
                    else post.title
                )
                + "\n\n"
                + post.hashtag
            )
            images = json.loads(post.images)
            media_ids = []
            for index, image in enumerate(images):
                media_id = self.upload_image(image, index=index + 1)
                time.sleep(LimitSNS.WAIT_PER_API_CALL.value)
                if not media_id:
                    return False
                is_uploaded = self.get_upload_status(media_id)
                time.sleep(LimitSNS.WAIT_PER_API_CALL.value)
                if not is_uploaded:
                    return False
                media_ids.append(media_id)

            carousel_id = self.upload_carousel(media_ids, text)
            time.sleep(LimitSNS.WAIT_PER_API_CALL.value)
            if not carousel_id:
                return False

            publish_id = self.publish_post(carousel_id)
            time.sleep(LimitSNS.WAIT_PER_API_CALL.value)
            if not publish_id:
                return False

            permalink = self.get_permalink_instagram(publish_id)
            time.sleep(LimitSNS.WAIT_PER_API_CALL.value)
            if not permalink:
                return False

            self.save_publish("PUBLISHED", permalink)
            return True
        except Exception as e:
            self.save_errors("ERRORED", f"SEND POST IMAGE {self.key_log}: {str(e)}")
            return False

    def send_post_video(self, post):
        try:
            media_id = self.upload_reels(post)
            time.sleep(LimitSNS.WAIT_PER_API_CALL.value)
            if not media_id:
                return False

            is_uploaded = self.get_upload_status(media_id)
            time.sleep(LimitSNS.WAIT_PER_API_CALL.value)
            if not is_uploaded:
                return False

            publish_id = self.publish_post(media_id)
            time.sleep(LimitSNS.WAIT_PER_API_CALL.value)
            if not publish_id:
                return False

            permalink = self.get_permalink_instagram(publish_id)
            time.sleep(LimitSNS.WAIT_PER_API_CALL.value)
            if not permalink:
                return False

            self.save_publish("PUBLISHED", permalink)
            return True
        except Exception as e:
            self.save_errors("ERRORED", f"SEND POST REEL {self.key_log}: {str(e)}")
            return False

    def get_permalink_instagram(self, media_id):
        try:
            PERMALINK_URL = f"https://graph.instagram.com/v22.0/{media_id}"
            params = {
                "fields": "permalink",
                "access_token": self.access_token,
            }
            response = requests.get(PERMALINK_URL, params=params)

            result = response.json()
            self.save_request_log("get_permalink_instagram", params, result)

            quote = response.headers.get("x-app-usage") if "headers" in response else ""

            if "permalink" in result:
                return result["permalink"]
            elif "error" in result:
                error = result["error"] if "error" in result else {}
                error_message = error["message"] if "message" in error else ""
                if error_message == "":
                    error_message = "Error occurred while getting permalink"
                self.save_errors(
                    "ERRORED",
                    f"GET PERMALINK {self.key_log}: {error_message}",
                    base_message=error_message,
                    instagram_quote=quote,
                )
            else:
                self.save_errors(
                    "ERRORED",
                    f"GET PERMALINK {self.key_log}: {str(result)}",
                    base_message=str(result),
                    instagram_quote=quote,
                )
                return False
            return False
        except Exception as e:
            self.save_errors("ERRORED", f"GET PERMALINK {self.key_log}: {str(e)}")
            return False

    def upload_image(self, media, index=1):
        try:
            log_instagram_message(
                f"------------ UPLOAD MEDIA: {self.key_log} ----------------"
            )
            UPLOAD_URL = (
                f"https://graph.instagram.com/v22.0/{self.istagram_user_id}/media"
            )
            params = {
                "image_url": media,
                "is_carousel_item": True,
                "access_token": self.access_token,
            }

            headers = {"Content-Type": "application/json"}

            try:
                post_response = requests.post(
                    UPLOAD_URL, params=params, headers=headers
                )
            except Exception as e:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} : UPLOAD MEDIA: {str(e)}",
                    base_message=str(e),
                )
                return False

            result = post_response.json()

            self.save_request_log("upload_media", params, result)
            self.save_uploading(index * 10)

            quote = (
                post_response.headers.get("x-app-usage")
                if "headers" in post_response
                else ""
            )

            if "id" in result:
                return result["id"]
            elif "error" in result:
                error = result["error"] if "error" in result else {}
                error_message = error["message"] if "message" in error else ""
                if error_message == "":
                    error_message = "Error occurred while uploading media"
                self.save_errors(
                    "ERRORED",
                    f"UPLOAD MEDIA {self.key_log}: {error_message}",
                    base_message=error_message,
                    instagram_quote=quote,
                )
                return False
            else:
                self.save_errors(
                    "ERRORED",
                    f"UPLOAD MEDIA {self.key_log}: {str(result)}",
                    base_message=str(result),
                    instagram_quote=quote,
                )
                return False

        except Exception as e:
            self.save_errors("ERRORED", f"UPLOAD MEDIA {self.key_log}: {str(e)}")
            return False

    def upload_carousel(self, media_ids, text):
        try:
            log_instagram_message(
                f"------------ UPLOAD CAROUSEL: {self.key_log} ----------------"
            )

            UPLOAD_URL = (
                f"https://graph.instagram.com/v22.0/{self.istagram_user_id}/media"
            )
            upload_data = {
                "access_token": self.access_token,
                "children": ",".join(media_ids),
                "media_type": "CAROUSEL",
                "caption": text,
            }

            headers = {"Content-Type": "application/json"}

            try:
                post_response = requests.post(
                    UPLOAD_URL, params=upload_data, headers=headers
                )
            except Exception as e:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} : UPLOAD CAROUSEL: {str(e)}",
                    base_message=str(e),
                )
                return False

            result = post_response.json()

            self.save_request_log("upload_carousel", upload_data, result)
            self.save_uploading(70)

            quote = (
                post_response.headers.get("x-app-usage")
                if "headers" in post_response
                else ""
            )

            if "id" in result:
                return result["id"]
            elif "error" in result:
                error = result["error"] if "error" in result else {}
                error_message = error["message"] if "message" in error else ""
                if error_message == "":
                    error_message = "Error occurred while uploading media"
                self.save_errors(
                    "ERRORED",
                    f"UPLOAD CAROUSEL {self.key_log}: {error_message}",
                    base_message=error_message,
                    instagram_quote=quote,
                )
                return False
            else:
                self.save_errors(
                    "ERRORED",
                    f"UPLOAD CAROUSEL {self.key_log}: {str(result)}",
                    base_message=str(result),
                    instagram_quote=quote,
                )
                return False
        except Exception as e:
            self.save_errors("ERRORED", f"UPLOAD CAROUSEL {self.key_log}: {str(e)}")
            return False

    def get_upload_status(self, media_id):
        try:
            GET_STATUS_URL = f"https://graph.instagram.com/v22.0/{media_id}"
            params = {
                "access_token": self.access_token,
                "fields": "status,status_code",
            }

            try:
                status_response = requests.get(GET_STATUS_URL, params=params)
            except Exception as e:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} : PUBLISH POST: {str(e)}",
                    base_message=str(e),
                )
                return False

            result = status_response.json()

            self.save_request_log("get_upload_status", params, result)

            quote = (
                status_response.headers.get("x-app-usage")
                if "headers" in status_response
                else ""
            )

            if "status_code" in result:
                status = result["status_code"]
                if status == "FINISHED":
                    return True
                elif status == "ERROR":
                    error = result["error"] if "error" in result else {}
                    error_message = error["message"] if "message" in error else ""
                    if error_message == "":
                        error_message = "Error occurred while uploading media"
                    self.save_errors(
                        "ERRORED",
                        f"ERROR GET UPLOAD STATUS {self.key_log}: {error_message}",
                        base_message=error_message,
                        instagram_quote=quote,
                    )
                    return False
                else:
                    time.sleep(LimitSNS.WAIT_SECOND_CHECK_STATUS.value)
                    return self.get_upload_status(media_id)
            else:
                self.save_errors(
                    "ERRORED",
                    f"ERROR GET UPLOAD STATUS {self.key_log}: {str(result)}",
                    base_message=str(result),
                    instagram_quote=quote,
                )
                return False
        except Exception as e:
            self.save_errors("ERRORED", f"PUBLISH POST {self.key_log}: {str(e)}")
            return False

    def publish_post(self, media_id):
        try:
            log_instagram_message(
                f"------------ PUBLISH POST: {self.key_log} ----------------"
            )
            PUBLISH = f"https://graph.instagram.com/v22.0/{self.istagram_user_id}/media_publish"
            upload_data = {
                "access_token": self.access_token,
                "creation_id": media_id,
            }

            headers = {"Content-Type": "application/json"}

            try:
                post_response = requests.post(
                    PUBLISH, params=upload_data, headers=headers
                )
            except Exception as e:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} : PUBLISH POST: {str(e)}",
                    base_message=str(e),
                )
                return False

            result = post_response.json()

            self.save_request_log("publish_post", upload_data, result)

            quote = (
                post_response.headers.get("x-app-usage")
                if "headers" in post_response
                else ""
            )

            if "id" in result:
                return result["id"]
            elif "error" in result:
                error = result["error"] if "error" in result else {}
                error_message = error["message"] if "message" in error else ""
                if error_message == "":
                    error_message = "Error occurred while publishing post"
                self.save_errors(
                    "ERRORED",
                    f"ERROR PUBLISH POST {self.key_log}: {error_message}",
                    base_message=error_message,
                    instagram_quote=quote,
                )
                return False
            else:
                self.save_errors(
                    "ERRORED",
                    f"ERROR PUBLISH POST {self.key_log}: {str(result)}",
                    base_message=str(result),
                    instagram_quote=quote,
                )
                return False
        except Exception as e:
            self.save_errors("ERRORED", f"PUBLISH POST {self.key_log}: {str(e)}")
            return False

    def upload_reels(self, post):
        try:
            log_instagram_message(
                f"------------ UPLOAD REEL POST: {self.key_log} ----------------"
            )
            UPLOAD_URL = (
                f"https://graph.instagram.com/v22.0/{self.istagram_user_id}/media"
            )

            text = (
                (
                    post.description
                    if post.description and post.description != ""
                    else post.title
                )
                + "\n\n"
                + post.hashtag
            )

            upload_data = {
                "media_type": "REELS",
                "video_url": post.video_url,
                "caption": text,
            }

            headers = {
                "Authorization": f"OAuth {self.access_token}",
            }

            try:
                post_response = requests.post(
                    UPLOAD_URL, data=upload_data, headers=headers
                )
            except Exception as e:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} : UPLOAD REEL: {str(e)}",
                    base_message=str(e),
                )
                return False

            result = post_response.json()

            quote = (
                post_response.headers.get("x-app-usage")
                if "headers" in post_response
                else ""
            )

            self.save_request_log("upload_reels", upload_data, result)

            if "id" in result:
                return result["id"]
            elif "error" in result:
                error = result["error"] if "error" in result else {}
                error_message = error["message"] if "message" in error else ""
                if error_message == "":
                    error_message = "Error occurred while uploading media"
                self.save_errors(
                    "ERRORED",
                    f"ERROR UPLOAD REEL {self.key_log}: {error_message}",
                    base_message=error_message,
                    instagram_quote=quote,
                )
                return False
            else:
                self.save_errors(
                    "ERRORED",
                    f"ERROR UPLOAD REEL {self.key_log}: {str(result)}",
                    base_message=str(result),
                    instagram_quote=quote,
                )
                return False
        except Exception as e:
            self.save_errors("ERRORED", f"UPLOAD REEL {self.key_log}: {str(e)}")
            return False
