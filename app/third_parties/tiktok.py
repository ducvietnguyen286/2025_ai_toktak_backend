import json
import os
import traceback

import requests
from app.services.request_social_log import RequestSocialLogService
from app.services.user import UserService
from app.lib.logger import log_social_message


class TiktokTokenService:

    @staticmethod
    def refresh_token(link, user):
        try:
            log_social_message(
                "------------------  REFRESH TIKTOK TOKEN  ------------------"
            )
            user_link = UserService.find_user_link(link_id=link.id, user_id=user.id)
            meta = json.loads(user_link.meta)
            refresh_token = meta.get("refresh_token")

            REFRESH_URL = "https://open-api.tiktok.com/oauth/refresh_token/"
            TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY") or ""

            r_data = {
                "client_key": TIKTOK_CLIENT_KEY,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            response = requests.post(REFRESH_URL, data=r_data, headers=headers)

            try:
                token_data = response.json()
            except Exception as e:
                return f"Error parsing response: {e}", 500

            log_social_message(f"Refresh token response: {token_data}")

            RequestSocialLogService.create_request_social_log(
                social="TIKTOK",
                user_id=user_link.user_id,
                type="refresh_token",
                request=json.dumps(r_data),
                response=json.dumps(token_data),
            )

            data_token = token_data.get("data")

            meta = user_link.meta
            meta = json.loads(meta)
            meta.update(token_data)
            user_link.meta = json.dumps(data_token)
            user_link.save()

            return token_data
        except Exception as e:
            traceback.print_exc()
            log_social_message(e)


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

    def publish_video(self, post):
        pass

    def upload_video(self, media):
        try:
            log_social_message("Upload video to Tiktok")
            # FILE INFO
            response = requests.get(media)

            upload_info = self.upload_video_init(response)
            log_social_message(f"Upload video info: {upload_info}")
            log_social_message(f"Upload video to Tiktok: {media}")
            info_data = upload_info.get("data")

            upload_url = info_data.get("upload_url")
            publish_id = info_data.get("publish_id")

            self.upload_video_append(upload_url, response)

            self.check_status(publish_id)
            log_social_message("Upload video success")
            return True
        except Exception as e:
            log_social_message(f"Error upload video to Tiktok: {str(e)}")
            return False

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
        error = res_json.get("error")
        error_code = error.get("code")
        if error_code == "access_token_invalid":
            TiktokTokenService.refresh_token(link=self.link, user=self.user)
            self.user_link = UserService.find_user_link(
                link_id=self.link.id, user_id=self.user.id
            )
            self.meta = json.loads(self.user_link.meta)
            return self.check_status(publish_id)
        status = res_json.get("data").get("status")
        if status == "PUBLISH_COMPLETE":
            return True
        return self.check_status(publish_id)

    def upload_video_append(upload_url, response):
        try:
            log_social_message("Upload video to Tiktok APPEND")
            media_type = response.headers.get("content-type")
            media_size = float(response.headers.get("content-length"))

            video_file = response.content
            headers = {
                "Content-Range": f"bytes 0-{media_size - 1}/{media_size}",
                "Content-Type": media_type,
            }
            response = requests.put(upload_url, headers=headers, data=video_file)
            log_social_message("Upload video")
            return response.json()
        except Exception as e:
            log_social_message(f"Error upload video to Tiktok: {str(e)}")

    def upload_video_init(self, media):
        log_social_message("Upload video to Tiktok INIT")
        access_token = self.meta.get("access_token")
        media_size = int(media.headers.get("content-length"))

        URL_VIDEO_UPLOAD = (
            "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

        log_social_message(headers)

        chunk_size = 10000000

        payload = {
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_url": media_size,
                "chunk_size": chunk_size,
                "total_chunk_count": media_size // chunk_size + 1,
            }
        }

        log_social_message(f"Payload: {payload}")

        upload_response = requests.post(URL_VIDEO_UPLOAD, headers=headers, data=payload)
        parsed_response = upload_response.json()

        log_social_message(f"Upload video to Tiktok INIT response: {parsed_response}")

        error = parsed_response.get("error")
        error_code = error.get("code")
        if error_code == "access_token_invalid":
            TiktokTokenService.refresh_token(link=self.link, user=self.user)
            self.user_link = UserService.find_user_link(
                link_id=self.link.id, user_id=self.user.id
            )
            self.meta = json.loads(self.user_link.meta)
            return self.upload_video_init(media=media)
        return parsed_response
