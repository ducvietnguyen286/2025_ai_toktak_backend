import json
import os
import base64
import time
import traceback
import requests

from app.services.post import PostService
from app.services.video_service import VideoService

from app.lib.logger import log_twitter_message
from app.services.request_social_log import RequestSocialLogService
from app.services.social_post import SocialPostService
from app.services.user import UserService

from app.third_parties.base_service import BaseService

PROGRESS_CHANNEL = os.environ.get("REDIS_PROGRESS_CHANNEL") or "progessbar"

MEDIA_ENDPOINT_URL = "https://api.x.com/2/media/upload"
X_POST_TO_X_URL = "https://api.x.com/2/tweets"
TOKEN_URL = "https://api.x.com/2/oauth2/token"


class TwitterTokenService:
    def __init__(self):
        config = VideoService.get_settings()
        self.client_id = config["TWITTER_CLIENT_ID"]
        self.client_secret = config["TWITTER_CLIENT_SECRET"]
        self.redirect_uri = os.environ.get("X_REDIRECT_URI")

    def fetch_user_info(self, user_link):
        try:
            log_twitter_message(
                "------------------  FETCH TWITTER USER INFO  ------------------"
            )
            meta = json.loads(user_link.meta)
            access_token = meta.get("access_token")

            URL_USER_INFO = (
                f"https://api.x.com/2/users/me?user.fields=profile_image_url"
            )

            response = requests.get(
                URL_USER_INFO, headers={"Authorization": f"Bearer {access_token}"}
            )
            user_data = response.json()

            RequestSocialLogService.create_request_social_log(
                social="X-TWITTER",
                social_post_id="",
                user_id=user_link.user_id,
                type="fetch_user_info",
                request="{}",
                response=json.dumps(user_data),
            )

            log_twitter_message(f"Fetch user info response: {user_data}")

            data = user_data.get("data")

            return {
                "id": data.get("id") or "",
                "username": data.get("username") or "",
                "name": data.get("name") or "",
                "avatar": data.get("profile_image_url") or "",
                "url": f"https://x.com/{data.get('username')}" or "",
            }
        except Exception as e:
            traceback.print_exc()
            log_twitter_message(e)
            return None

    def fetch_token(self, code, user_link):
        try:

            # Tạo header Authorization kiểu Basic bằng cách mã hóa "client_id:client_secret"
            client_credentials = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode("utf-8")
            ).decode("utf-8")

            headers = {
                "Authorization": f"Basic {client_credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            # Các thông số yêu cầu trong body để trao đổi code lấy access token
            r_data = {
                "code": code,
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "code_verifier": "challenge",
            }
            response = requests.post(TOKEN_URL, headers=headers, data=r_data)
            data = response.json()

            RequestSocialLogService.create_request_social_log(
                social="X-TWITTER",
                social_post_id="",
                user_id=user_link.user_id,
                type="authorization_code",
                request=json.dumps(r_data),
                response=json.dumps(data),
            )

            has_token = data.get("access_token")
            if not has_token:
                return False

            meta = user_link.meta
            meta = json.loads(meta)
            meta.update(data)

            user_link.meta = json.dumps(meta)
            user_link.status = 1
            user_link.save()

            return True
        except Exception as e:
            traceback.print_exc()
            log_twitter_message(e)
            return False

    def refresh_token(self, link, user):
        try:
            credentials_str = f"{self.client_id}:{self.client_secret}"
            credentials = base64.b64encode(credentials_str.encode("utf-8")).decode(
                "utf-8"
            )

            user_link = UserService.find_user_link(link_id=link.id, user_id=user.id)
            user_link_meta = json.loads(user_link.meta)
            refresh_token = user_link_meta.get("refresh_token")

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {credentials}",
            }

            r_data = {
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            response = requests.post(TOKEN_URL, headers=headers, data=r_data)
            data = response.json()

            log_twitter_message(data)

            RequestSocialLogService.create_request_social_log(
                social="X-TWITTER",
                social_post_id="",
                user_id=user_link.user_id,
                type="refresh_token",
                request=json.dumps(r_data),
                response=json.dumps(data),
            )

            has_token = data.get("access_token")
            if not has_token:
                user_link.status = 0
                user_link.save()
                return False

            meta = user_link.meta
            meta = json.loads(meta)
            meta.update(data)

            user_link.meta = json.dumps(meta)
            user_link.save()

            return data
        except Exception as e:
            traceback.print_exc()
            log_twitter_message(e)
            return False


class TwitterService(BaseService):
    def __init__(self, sync_id=""):
        self.sync_id = sync_id
        self.user_link = None
        self.user = None
        self.link = None
        self.meta = None
        self.processing_info = None
        self.social_post = None
        self.link_id = None
        self.post_id = None
        self.batch_id = None
        self.social_post_id = ""
        self.service = "X-TWITTER"
        self.key_log = ""

    def send_post(self, post, link, user_id, social_post_id):
        self.user = UserService.find_user(user_id)
        self.link = link
        self.user_link = UserService.find_user_link(link_id=link.id, user_id=user_id)
        self.meta = json.loads(self.user_link.meta)
        self.social_post = SocialPostService.find_social_post(social_post_id)
        self.link_id = link.id
        self.post_id = post.id
        self.batch_id = post.batch_id
        self.social_post_id = str(self.social_post.id)
        self.key_log = f"{self.post_id} - {self.social_post.session_key}"

        try:
            self.save_uploading(0)
            log_twitter_message(
                f"------------ READY TO SEND POST: {post._to_json()} ----------------"
            )
            if post.type == "image":
                self.send_post_social(post, link)
            if post.type == "video":
                self.send_post_video(post, link)
            return True
        except Exception as e:
            self.save_errors("ERRORED", f"POST {self.key_log} SEND POST: {str(e)}")
            return True

    def send_post_social(self, post, link):
        images = post.images
        if images:
            images = json.loads(images)
        else:
            images = [post.thumbnail]
        images = images[:4]

        media_ids = []
        for img in images:
            media_id = self.upload_media(img)
            if not media_id:
                return False

            media_ids.append(media_id)

        return self.send_post_images(media_ids, post, link)

    def send_post_images(self, media_ids, post, link, retry=0):
        try:
            access_token = self.meta.get("access_token")

            hashtags = post.hashtag.split()
            hashtags = hashtags[: len(hashtags) // 2]
            hashtag = " ".join(hashtags)

            text = post.description + "\n\n " + hashtag

            if len(text) > 250:
                text = text[:250]
            data = {
                "text": text,
                "media": {"media_ids": media_ids},
            }
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            try:
                response = requests.post(
                    X_POST_TO_X_URL, headers=headers, data=json.dumps(data)
                )
            except Exception as e:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} SEND POST IMAGES - REQUEST URL: {str(e)}",
                    base_message=str(e),
                )
                return False
            parsed_response = response.json()

            self.save_request_log("send_images", data, parsed_response)

            status = parsed_response.get("status")
            if status == 401:
                if retry > 0:
                    self.save_errors(
                        "ERRORED",
                        f"POST {self.key_log} SEND POST IMAGES: Access token invalid",
                        base_message="Access token invalid",
                    )

                    return False

                TwitterTokenService().refresh_token(link=self.link, user=self.user)
                self.user_link = UserService.find_user_link(
                    link_id=self.link.id, user_id=self.user.id
                )
                self.meta = json.loads(self.user_link.meta)
                return self.send_post_images(media_ids, post, link, retry + 1)
            elif status == 403:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} SEND POST IMAGES: {parsed_response}",
                    base_message=f"{parsed_response}",
                )
                return False
            errors = parsed_response.get("errors")
            if errors:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} SEND POST IMAGES: {errors}",
                    base_message=f"{errors}",
                )
                return False
            else:
                data = parsed_response.get("data")
                if data:
                    x_post_id = data.get("id")

                    username = self.user_link.username
                    if username == "" or not username:
                        user_url = self.user_link.url
                        permalink = f"{user_url}/status/{x_post_id}"
                    else:
                        permalink = f"https://x.com/{username}/status/{x_post_id}"

                    self.save_publish("PUBLISHED", permalink)
                    return True
                else:
                    detail = parsed_response.get("detail")
                    if detail:
                        self.save_errors(
                            "ERRORED",
                            f"POST {self.key_log} SEND POST IMAGES: {detail}",
                            base_message=f"{detail}",
                        )
                    else:
                        self.save_errors(
                            "ERRORED",
                            f"POST {self.key_log} SEND POST IMAGES: {parsed_response}",
                            base_message=f"{parsed_response}",
                        )
                    return False
        except Exception as e:
            traceback.print_exc()
            self.save_errors(
                "ERRORED", f"POST {self.key_log} SEND POST IMAGES - ERROR: " + str(e)
            )
            return False

    def send_post_video(self, post, link):
        video_path = post.video_path
        time_waited = 0
        while not video_path and time_waited < 30:
            time.sleep(2)
            time_waited += 2
            post = PostService.find_post(post.id)
            video_path = post.video_path

        return self.send_post_video_to_x(video_path, post, link)

    def send_post_video_to_x(self, media, post, link, media_id=None, retry=0):
        try:
            access_token = self.meta.get("access_token")
            if not media_id:
                media_id = self.upload_media(media, True)
            if not media_id:
                return False

            hashtags = post.hashtag.split()
            hashtags = hashtags[: len(hashtags) // 2]
            hashtag = " ".join(hashtags)

            text = post.description + "\n\n " + hashtag
            if len(text) > 250:
                text = text[:250]
            data = {
                "text": text,
                "media": {"media_ids": [media_id]},
            }
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            try:
                response = requests.post(
                    X_POST_TO_X_URL, headers=headers, data=json.dumps(data)
                )
            except Exception as e:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} SEND POST VIDEO - REQUEST URL: {str(e)}",
                    base_message=str(e),
                )
                return False
            parsed_response = response.json()

            self.save_request_log("send_video", data, parsed_response)

            status = parsed_response.get("status")
            if status == 401:
                if retry > 0:
                    self.save_errors(
                        "ERRORED",
                        f"POST {self.key_log} SEND POST VIDEO: Access token invalid",
                        base_message="Access token invalid",
                    )

                    return False

                TwitterTokenService().refresh_token(link=self.link, user=self.user)
                self.user_link = UserService.find_user_link(
                    link_id=self.link.id, user_id=self.user.id
                )
                self.meta = json.loads(self.user_link.meta)
                return self.send_post_video_to_x(media, post, link, media_id, retry + 1)
            elif status == 403:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} SEND POST VIDEO: {parsed_response}",
                    base_message=f"{parsed_response}",
                )
                return False
            errors = parsed_response.get("errors")
            if errors:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} SEND POST VIDEO: {errors}",
                    base_message=f"{errors}",
                )
                return False
            else:
                data = parsed_response.get("data")
                if data:
                    x_post_id = data.get("id")

                    username = self.user_link.username
                    if username == "" or not username:
                        user_url = self.user_link.url
                        permalink = f"{user_url}/status/{x_post_id}"
                    else:
                        permalink = f"https://x.com/{username}/status/{x_post_id}"

                    self.save_publish("PUBLISHED", permalink)
                    return True
                else:
                    details = parsed_response.get("details")
                    if details:
                        self.save_errors(
                            "ERRORED",
                            f"POST {self.key_log} SEND POST VIDEO: {details}",
                            base_message=f"{details}",
                        )
                    else:
                        self.save_errors(
                            "ERRORED",
                            f"POST {self.key_log} SEND POST VIDEO: {parsed_response}",
                            base_message=f"{parsed_response}",
                        )
                    return False
        except Exception as e:
            traceback.print_exc()
            self.save_errors(
                "ERRORED", f"POST {self.key_log} SEND POST VIDEO - ERROR: " + str(e)
            )
            return False

    def upload_media(self, media, is_video=False):
        if is_video:
            response = self.get_media_content_by_path(
                media_path=media, get_content=False
            )
        else:
            response = self.get_media_content(
                media_url=media, get_content=False, is_photo=not is_video
            )
        if not response:
            return False

        total_bytes = response.get("media_size", 0)
        media_type = response.get("media_type", "")
        media_content = response.get("content", "")

        media_id = self.upload_media_init(media_type, total_bytes, is_video)

        if not media_id:
            return False

        uploaded = self.upload_append(
            media_id=media_id, content=media_content, total_bytes=total_bytes
        )
        if not uploaded:
            return False
        final = self.upload_finalize(media_id)
        if not final:
            return False
        return media_id

    def upload_media_init(self, media_type, total_bytes, is_video=False, retry=0):
        access_token = self.meta.get("access_token")

        headers = {
            "Authorization": "Bearer {}".format(access_token),
            "Content-Type": "application/json",
        }

        request_data = {
            "command": "INIT",
            "media_type": media_type,
            "total_bytes": total_bytes,
            "media_category": "tweet_video" if is_video else "tweet_image",
        }

        log_twitter_message(request_data)

        try:
            req = requests.post(
                url=MEDIA_ENDPOINT_URL, params=request_data, headers=headers
            )
        except Exception as e:
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} UPLOAD MEDIA INIT - REQUEST URL: {str(e)}",
                base_message=str(e),
            )
            return False

        self.save_request_log("upload_media_init", request_data, req.json())

        self.save_uploading(10)

        status_code = req.status_code
        if status_code == 401:
            if retry > 0:

                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD MEDIA INIT: Access token invalid",
                    base_message="Access token invalid",
                )
                return False

            TwitterTokenService().refresh_token(link=self.link, user=self.user)
            self.user_link = UserService.find_user_link(
                link_id=self.link_id, user_id=self.user.id
            )
            self.meta = json.loads(self.user_link.meta)
            return self.upload_media_init(
                media_type=media_type,
                total_bytes=total_bytes,
                is_video=is_video,
                retry=retry + 1,
            )

        res_json = req.json()
        if "data" not in res_json:
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} UPLOAD MEDIA INIT: Error Get Data",
                base_message=f"{res_json}",
            )
            return False
        if "id" not in res_json["data"]:
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} UPLOAD MEDIA INIT: Error Get Media ID",
                base_message=f"{res_json}",
            )
            return False
        media_id = res_json["data"]["id"]

        return media_id

    def upload_append(self, media_id, content, total_bytes, retry=0):
        access_token = self.meta.get("access_token")
        segment_id = 0
        bytes_sent = 0
        chunk_size = 4 * 1024 * 1024  # 4MB chunk size

        total_chunks = total_bytes // chunk_size
        progress_by_chunk = 20 // (total_chunks if total_chunks > 0 else 1)

        while bytes_sent < total_bytes:
            chunk = content[bytes_sent : bytes_sent + chunk_size]

            files = {"media": ("chunk", chunk, "application/octet-stream")}

            data = {
                "command": "APPEND",
                "media_id": media_id,
                "segment_index": segment_id,
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "MediaUploadSampleCode",
            }

            try:
                req = requests.post(
                    url=MEDIA_ENDPOINT_URL, data=data, files=files, headers=headers
                )
            except Exception as e:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD MEDIA APPEND - REQUEST URL: {str(e)}",
                    base_message=str(e),
                )
                return False

            self.save_request_log("upload_media_append", data, {"text": req.text})

            self.save_uploading(10 + (progress_by_chunk * (segment_id + 1)))

            status_code = req.status_code
            if status_code == 401:
                if retry > 0:
                    self.save_errors(
                        "ERRORED",
                        f"POST {self.key_log} UPLOAD MEDIA APPEND: Access token invalid",
                        base_message="Access token invalid",
                    )
                    return False

                TwitterTokenService().refresh_token(link=self.link, user=self.user)
                self.user_link = UserService.find_user_link(
                    link_id=self.link.id, user_id=self.user.id
                )
                self.meta = json.loads(self.user_link.meta)
                return self.upload_append(
                    media_id=media_id,
                    content=content,
                    total_bytes=total_bytes,
                    retry=retry + 1,
                )

            if req.status_code < 200 or req.status_code > 299:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD MEDIA APPEND: {req.status_code} {req.text}",
                    base_message=f"{req.status_code} {req.text}",
                )
                return False

            segment_id += 1
            bytes_sent += len(chunk)

        return True

    def upload_finalize(self, media_id, retry=0):
        access_token = self.meta.get("access_token")

        headers = {
            "Authorization": "Bearer {}".format(access_token),
            "Content-Type": "application/json",
        }

        request_data = {"command": "FINALIZE", "media_id": media_id}

        try:
            req = requests.post(
                url=MEDIA_ENDPOINT_URL, params=request_data, headers=headers
            )
        except Exception as e:
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} UPLOAD MEDIA FINALIZE - REQUEST URL: {str(e)}",
                base_message=str(e),
            )
            return False

        self.save_request_log("upload_media_finalize", request_data, req.json())

        status_code = req.status_code
        if status_code == 401:
            if retry > 0:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD MEDIA FINALIZE: Access token invalid",
                    base_message="Access token invalid",
                )

                return False
            TwitterTokenService().refresh_token(link=self.link, user=self.user)
            self.user_link = UserService.find_user_link(
                link_id=self.link.id, user_id=self.user.id
            )
            self.meta = json.loads(self.user_link.meta)
            return self.upload_finalize(media_id=media_id, retry=retry + 1)
        else:
            try:
                response_json = req.json()
                if "data" in response_json:
                    data = response_json.get("data", None)
                    if "processing_info" in data:
                        self.processing_info = data.get("processing_info", None)
                        self.save_uploading(40)
                        is_done = self.check_status(media_id=media_id)
                        if is_done:
                            return True
                        return False
                    else:
                        self.save_uploading(90)
                        return True
                else:
                    self.save_errors(
                        "ERRORED",
                        f"POST {self.key_log} UPLOAD MEDIA FINALIZE: {response_json}",
                        base_message=f"{response_json}",
                    )
                    return False
            except requests.exceptions.JSONDecodeError as e:
                self.save_errors(
                    "ERRORED", f"POST {self.key_log} UPLOAD MEDIA FINALIZE: {str(e)}"
                )
                return False

    def check_status(self, media_id, count=1, retry=0):
        access_token = self.meta.get("access_token")

        # Checks video processing status
        if self.processing_info is None:
            return False

        headers = {
            "Authorization": "Bearer {}".format(access_token),
            "Content-Type": "application/json",
        }

        state = self.processing_info["state"]

        if state == "succeeded":
            return True

        if state == "failed":
            return False

        check_after_secs = self.processing_info["check_after_secs"]

        time.sleep(check_after_secs)

        request_params = {"command": "STATUS", "media_id": media_id}

        try:
            req = requests.get(
                url=MEDIA_ENDPOINT_URL, params=request_params, headers=headers
            )
        except Exception as e:
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} UPLOAD MEDIA STATUS - REQUEST URL: {str(e)}",
                base_message=str(e),
            )
            return False

        self.save_request_log("check_status", request_params, req.json())

        status_code = req.status_code
        if status_code == 401:
            if retry > 0:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD MEDIA STATUS: Access token invalid",
                    base_message="Access token invalid",
                )
                return False
            TwitterTokenService().refresh_token(link=self.link, user=self.user)
            self.user_link = UserService.find_user_link(
                link_id=self.link.id, user_id=self.user.id
            )
            self.meta = json.loads(self.user_link.meta)
            return self.check_status(media_id=media_id, count=count, retry=retry + 1)

        if count <= 5:
            progress = 40 + (count * 10)
            self.save_uploading(progress)

        self.processing_info = req.json()["data"].get("processing_info", None)
        return self.check_status(media_id=media_id, count=count + 1, retry=retry)
