import json
import os
import base64
import time
import traceback
import requests

from app.lib.logger import log_social_message
from app.services.request_social_log import RequestSocialLogService
from app.services.social_post import SocialPostService
from app.services.user import UserService

MEDIA_ENDPOINT_URL = "https://api.x.com/2/media/upload"
X_POST_TO_X_URL = "https://api.x.com/2/tweets"
TOKEN_URL = "https://api.x.com/2/oauth2/token"


class TwitterTokenService:
    def __init__(self):
        self.client_id = os.environ.get("X_CLIENT_KEY")
        self.client_secret = os.environ.get("X_CLIENT_SECRET")
        self.redirect_uri = os.environ.get("X_REDIRECT_URI")

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
                social="X",
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
            log_social_message(e)
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

            log_social_message(data)

            RequestSocialLogService.create_request_social_log(
                social="X",
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
            log_social_message(e)


class TwitterService:
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

        if post.type == "image":
            self.send_post_social(post, link)
        if post.type == "video":
            self.send_post_video(post, link)

    def send_post_social(self, post, link):
        log_social_message(f"Send post Social to Twitter {post.id}")
        if post.status != 1 or post.thumbnail == "" or post.thumbnail is None:
            return
        images = post.images
        image = ""
        if images:
            images = json.loads(images)
            image = images[0]
        else:
            image = post.thumbnail
        self.send_post_to_x(image, post, link)
        log_social_message(f"Send post Social to Twitter {post.id} successfully")

    def send_post_video(self, post, link):
        log_social_message(f"Send post Video to Twitter {post.id}")
        if post.status != 1 or post.video_url == "" or post.video_url is None:
            return
        self.send_post_to_x(post.video_url, post, link, is_video=True)
        log_social_message(f"Send post Video to Twitter {post.id} successfully")

    def send_post_to_x(self, media, post, link, is_video=False, media_id=None):
        try:
            log_social_message(f"Send post to X {post.id}")
            access_token = self.meta.get("access_token")
            if not media_id:
                media_id = self.upload_media(media, is_video)
            log_social_message(f"media_id: {media_id}")
            data = {
                "text": post.content if post.type == "social" else post.title,
                "media": {"media_ids": [media_id]},
            }
            log_social_message(data)
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            response = requests.post(
                X_POST_TO_X_URL, headers=headers, data=json.dumps(data)
            )
            parsed_response = response.json()
            log_social_message(parsed_response)
            status = parsed_response.get("status")
            if status == 401:
                TwitterTokenService().refresh_token(link=self.link, user=self.user)
                self.user_link = UserService.find_user_link(
                    link_id=self.link.id, user_id=self.user.id
                )
                self.meta = json.loads(self.user_link.meta)
                return self.send_post_to_x(media, post, link, is_video, media_id)
            errors = parsed_response.get("errors")
            if errors:
                SocialPostService.create_social_post(
                    link_id=link.id,
                    user_id=post.user_id,
                    post_id=post.id,
                    status="ERRORED",
                    error_message=json.dumps(errors),
                )
            else:
                data = parsed_response.get("data")
                log_social_message(data)
                permalink = data.get("id")
                SocialPostService.create_social_post(
                    link_id=link.id,
                    user_id=post.user_id,
                    post_id=post.id,
                    status="PUBLISHED",
                    social_link=permalink,
                )
        except Exception as e:
            traceback.print_exc()
            log_social_message(f"Error send post to X: {str(e)}")
            return False

    def upload_media(self, media, is_video=False):
        log_social_message(f"Upload media {media}")

        log_social_message(f"Downloading media {media}")
        response = requests.get(media)
        log_social_message(f"Download media {media} done")

        total_bytes = int(response.headers.get("content-length", 0))
        media_type = response.headers.get("content-type")

        log_social_message(f"media_type: {media_type}")
        log_social_message(f"total_bytes: {total_bytes}")

        media_id = self.upload_media_init(media_type, total_bytes, is_video)
        uploaded = self.upload_append(
            media_id=media_id, content=response.content, total_bytes=total_bytes
        )
        if not uploaded:
            return False
        self.upload_finalize(media_id)
        log_social_message(f"Upload media {media} done")
        return media_id

    def upload_media_init(self, media_type, total_bytes, is_video=False):
        log_social_message("Upload Media INIT")
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

        log_social_message(request_data)

        req = requests.post(
            url=MEDIA_ENDPOINT_URL, params=request_data, headers=headers
        )

        status_code = req.status_code
        if status_code == 401:
            TwitterTokenService().refresh_token(link=self.link, user=self.user)
            self.user_link = UserService.find_user_link(
                link_id=self.link.id, user_id=self.user.id
            )
            self.meta = json.loads(self.user_link.meta)
            return self.upload_media_init(
                media_type=media_type, total_bytes=total_bytes, is_video=is_video
            )

        log_social_message(req.status_code)
        log_social_message(req.text)
        media_id = req.json()["data"]["id"]

        return media_id

    def upload_append(self, media_id, content, total_bytes):
        access_token = self.meta.get("access_token")
        segment_id = 0
        bytes_sent = 0
        chunk_size = 4 * 1024 * 1024  # 4MB chunk size
        while bytes_sent < total_bytes:
            chunk = content[bytes_sent : bytes_sent + chunk_size]

            log_social_message("APPEND")

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

            req = requests.post(
                url=MEDIA_ENDPOINT_URL, data=data, files=files, headers=headers
            )

            status_code = req.status_code
            if status_code == 401:
                TwitterTokenService().refresh_token(link=self.link, user=self.user)
                self.user_link = UserService.find_user_link(
                    link_id=self.link.id, user_id=self.user.id
                )
                self.meta = json.loads(self.user_link.meta)
                return self.upload_append(
                    media_id=media_id, content=content, total_bytes=total_bytes
                )

            if req.status_code < 200 or req.status_code > 299:
                log_social_message(req.status_code)
                log_social_message(req.text)
                return False

            segment_id += 1
            bytes_sent += len(chunk)

            log_social_message(f"{bytes_sent} of {total_bytes} bytes uploaded")

        log_social_message("Upload chunks complete.")
        return True

    def upload_finalize(self, media_id):
        access_token = self.meta.get("access_token")

        # Finalizes uploads and starts video processing
        log_social_message("FINALIZE")

        headers = {
            "Authorization": "Bearer {}".format(access_token),
            "Content-Type": "application/json",
        }

        request_data = {"command": "FINALIZE", "media_id": media_id}

        req = requests.post(
            url=MEDIA_ENDPOINT_URL, params=request_data, headers=headers
        )

        status_code = req.status_code
        if status_code == 401:
            TwitterTokenService().refresh_token(link=self.link, user=self.user)
            self.user_link = UserService.find_user_link(
                link_id=self.link.id, user_id=self.user.id
            )
            self.meta = json.loads(self.user_link.meta)
            return self.upload_finalize(media_id=media_id)
        else:
            try:
                response_json = req.json()
                log_social_message(f"FINALIZE Res: {response_json}")
                self.processing_info = response_json["data"].get(
                    "processing_info", None
                )
                self.check_status(media_id=media_id)
            except requests.exceptions.JSONDecodeError as e:
                log_social_message(f"FINALIZE Res: {req}")
                log_social_message(f"FINALIZE Res: {req.text}")
                log_social_message("JSONDecodeError:", e)
                return None

    def check_status(self, media_id):
        access_token = self.meta.get("access_token")

        # Checks video processing status
        if self.processing_info is None:
            return

        headers = {
            "Authorization": "Bearer {}".format(access_token),
            "Content-Type": "application/json",
        }

        state = self.processing_info["state"]

        log_social_message("Media processing status is %s " % state)

        if state == "succeeded":
            return True

        if state == "failed":
            raise ValueError("Upload failed")

        check_after_secs = self.processing_info["check_after_secs"]

        log_social_message("Checking after %s seconds" % str(check_after_secs))
        time.sleep(check_after_secs)

        log_social_message("STATUS")

        request_params = {"command": "STATUS", "media_id": media_id}

        req = requests.get(
            url=MEDIA_ENDPOINT_URL, params=request_params, headers=headers
        )

        status_code = req.status_code
        if status_code == 401:
            TwitterTokenService().refresh_token(link=self.link, user=self.user)
            self.user_link = UserService.find_user_link(
                link_id=self.link.id, user_id=self.user.id
            )
            self.meta = json.loads(self.user_link.meta)
            return self.check_status(media_id=media_id)

        self.processing_info = req.json()["data"].get("processing_info", None)
        self.check_status(media_id=media_id)
