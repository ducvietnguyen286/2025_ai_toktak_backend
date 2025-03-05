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

from app.third_parties.base_service import BaseService

PROGRESS_CHANNEL = os.environ.get("REDIS_PROGRESS_CHANNEL") or "progessbar"

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
                social_post_id=0,
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
                social_post_id=0,
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
            return False


class TwitterService(BaseService):
    def __init__(self):
        self.user_link = None
        self.user = None
        self.link = None
        self.meta = None
        self.processing_info = None
        self.social_post = None
        self.link_id = None
        self.post_id = None
        self.batch_id = None
        self.social_post_id = None
        self.service = "X (TWITTER)"

    def send_post(self, post, link, user_id, social_post_id):
        self.user = UserService.find_user(user_id)
        self.link = link
        self.user_link = UserService.find_user_link(link_id=link.id, user_id=user_id)
        self.meta = json.loads(self.user_link.meta)
        self.social_post = SocialPostService.find_social_post(social_post_id)
        self.link_id = link.id
        self.post_id = post.id
        self.batch_id = post.batch_id
        self.social_post_id = self.social_post.id

        try:
            if post.type == "image":
                self.send_post_social(post, link)
            if post.type == "video":
                self.send_post_video(post, link)
        except Exception as e:
            self.save_errors("ERRORED", f"SEND POST: {str(e)}")
            return False

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

    def send_post_to_x(self, media, post, link, is_video=False, media_id=None, retry=0):
        try:
            log_social_message(f"Send post to X {post.id}")
            access_token = self.meta.get("access_token")
            if not media_id:
                media_id = self.upload_media(media, is_video)
            log_social_message(f"media_id: {media_id}")
            data = {
                "text": post.title,
                "media": {"media_ids": [media_id]},
            }
            log_social_message(data)
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            try:
                response = requests.post(
                    X_POST_TO_X_URL, headers=headers, data=json.dumps(data)
                )
            except Exception as e:
                self.save_errors("ERRORED", f"SEND POST TO X - REQUEST URL: {str(e)}")
                return False
            parsed_response = response.json()
            log_social_message(parsed_response)
            status = parsed_response.get("status")
            if status == 401:
                if retry > 0:
                    self.user_link.status = 0
                    self.user_link.save()

                    self.save_errors("ERRORED", "SEND POST TO X: Access token invalid")

                    return False

                TwitterTokenService().refresh_token(link=self.link, user=self.user)
                self.user_link = UserService.find_user_link(
                    link_id=self.link.id, user_id=self.user.id
                )
                self.meta = json.loads(self.user_link.meta)
                return self.send_post_to_x(
                    media, post, link, is_video, media_id, retry + 1
                )
            errors = parsed_response.get("errors")
            if errors:
                self.save_errors("ERRORED", f"SEND POST TO X: {errors}")
                return False
            else:
                data = parsed_response.get("data")
                log_social_message(data)
                permalink = data.get("id")
                self.save_publish("PUBLISHED", permalink)
                return True
        except Exception as e:
            traceback.print_exc()
            self.save_errors("ERRORED", "SEND POST TO X - ERROR: " + str(e))
            return False

    def upload_media(self, media, is_video=False):
        log_social_message(f"Upload media {media}")

        response = requests.get(media)

        total_bytes = int(response.headers.get("content-length", 0))
        media_type = response.headers.get("content-type")

        media_id = self.upload_media_init(media_type, total_bytes, is_video)

        if not media_id:
            return False

        uploaded = self.upload_append(
            media_id=media_id, content=response.content, total_bytes=total_bytes
        )
        if not uploaded:
            return False
        final = self.upload_finalize(media_id)
        if not final:
            return False
        log_social_message(f"Upload media {media} done")
        return media_id

    def upload_media_init(self, media_type, total_bytes, is_video=False, retry=0):
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

        try:
            req = requests.post(
                url=MEDIA_ENDPOINT_URL, params=request_data, headers=headers
            )
        except Exception as e:
            self.save_errors("ERRORED", f"UPLOAD MEDIA INIT - REQUEST URL: {str(e)}")
            return False

        RequestSocialLogService.create_request_social_log(
            social="X",
            social_post_id=self.social_post_id,
            user_id=self.user.id,
            type="upload_media_init",
            request=json.dumps(request_data),
            response=json.dumps(req.json()),
        )

        self.save_uploading(10)

        status_code = req.status_code
        if status_code == 401:
            if retry > 0:
                self.user_link.status = 0
                self.user_link.save()

                self.save_errors("ERRORED", "UPLOAD MEDIA INIT: Access token invalid")
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

        log_social_message(
            f"------------------X INIT RESPONSE: {req.json()}-----------------"
        )

        res_json = req.json()
        if not res_json["data"]:
            self.save_errors("ERRORED", "UPLOAD MEDIA INIT: Error Get Media ID")
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

            try:
                req = requests.post(
                    url=MEDIA_ENDPOINT_URL, data=data, files=files, headers=headers
                )
            except Exception as e:
                self.save_errors(
                    "ERRORED", f"UPLOAD MEDIA APPEND - REQUEST URL: {str(e)}"
                )
                return False

            try:
                response_json = req.json()
            except ValueError as e:
                log_social_message(f"JSONDecodeError: {e}")
                log_social_message(f"Response content: {req.content}")
                response_json = None

            RequestSocialLogService.create_request_social_log(
                social="X",
                social_post_id=self.social_post_id,
                user_id=self.user.id,
                type="upload_media_append",
                request=json.dumps(data),
                response=json.dumps(response_json) if response_json else req.text,
            )

            self.save_uploading(10 + (progress_by_chunk * (segment_id + 1)))

            status_code = req.status_code
            if status_code == 401:
                if retry > 0:
                    self.user_link.status = 0
                    self.user_link.save()

                    self.save_errors(
                        "ERRORED", "UPLOAD MEDIA APPEND: Access token invalid"
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
                    "ERRORED", f"UPLOAD MEDIA APPEND: {req.status_code} {req.text}"
                )
                return False

            segment_id += 1
            bytes_sent += len(chunk)

            log_social_message(f"{bytes_sent} of {total_bytes} bytes uploaded")

        log_social_message("Upload chunks complete.")
        return True

    def upload_finalize(self, media_id, retry=0):
        access_token = self.meta.get("access_token")

        # Finalizes uploads and starts video processing
        log_social_message("FINALIZE")

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
                "ERRORED", f"UPLOAD MEDIA FINALIZE - REQUEST URL: {str(e)}"
            )
            return False

        RequestSocialLogService.create_request_social_log(
            social="X",
            social_post_id=self.social_post_id,
            user_id=self.user.id,
            type="upload_media_finalize",
            request=json.dumps(request_data),
            response=json.dumps(req.json()),
        )

        status_code = req.status_code
        if status_code == 401:
            if retry > 0:
                self.user_link.status = 0
                self.user_link.save()

                self.save_errors(
                    "ERRORED", "UPLOAD MEDIA FINALIZE: Access token invalid"
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
                log_social_message(f"FINALIZE Res: {response_json}")
                self.processing_info = response_json["data"].get(
                    "processing_info", None
                )
                self.save_uploading(40)
                is_done = self.check_status(media_id=media_id)
                if is_done:
                    return True
                return False
            except requests.exceptions.JSONDecodeError as e:

                self.save_errors("ERRORED", f"UPLOAD MEDIA FINALIZE: {str(e)}")
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

        log_social_message("Media processing status is %s " % state)

        if state == "succeeded":
            return True

        if state == "failed":
            return False

        check_after_secs = self.processing_info["check_after_secs"]

        log_social_message("Checking after %s seconds" % str(check_after_secs))
        time.sleep(check_after_secs)

        log_social_message("STATUS")

        request_params = {"command": "STATUS", "media_id": media_id}

        try:
            req = requests.get(
                url=MEDIA_ENDPOINT_URL, params=request_params, headers=headers
            )
        except Exception as e:
            self.save_errors("ERRORED", f"UPLOAD MEDIA STATUS - REQUEST URL: {str(e)}")
            return False

        status_code = req.status_code
        if status_code == 401:
            if retry > 0:
                self.user_link.status = 0
                self.user_link.save()

                self.save_errors("ERRORED", "UPLOAD MEDIA STATUS: Access token invalid")
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
