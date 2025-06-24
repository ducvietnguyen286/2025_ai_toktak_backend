import json
import os

import requests
import mimetypes

from app.enums.social import SocialMedia
from app.extensions import redis_client
from app.lib.header import generate_desktop_user_agent
from app.lib.logger import (
    log_thread_message,
    log_youtube_message,
    log_facebook_message,
    log_twitter_message,
    log_tiktok_message,
)
from app.services.notification import NotificationServices
from app.services.post import PostService
from app.services.request_social_log import RequestSocialLogService
import const
from app.tasks.social_post_tasks import update_social_data

PROGRESS_CHANNEL = os.environ.get("REDIS_PROGRESS_CHANNEL") or "progessbar"


class BaseService:
    def __init__(self):
        self.sync_id = ""
        self.batch_id = None
        self.link_id = None
        self.post_id = None
        self.user_id = None
        self.social_post = None
        self.service = None
        self.key_log = ""

    def get_media_content_by_path(self, media_path, get_content=True, is_photo=False):
        try:
            self.log_social_message(
                f"------------START {self.key_log} GET MEDIA : {media_path}----------------"
            )

            if not os.path.exists(media_path):
                self.log_social_message(
                    f"------------POST {self.key_log} MEDIA PATH NOT FOUND----------------"
                )
                return False

            with open(media_path, "rb") as file:
                content = file.read()
                if get_content:
                    return content

                mime_type, encoding = mimetypes.guess_type(media_path)
                file_size = os.path.getsize(media_path)

                return {
                    "content": content,
                    "media_size": file_size,
                    "media_type": mime_type,
                }
        except Exception as e:
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} SEND POST MEDIA - GET MEDIA PATH: {str(e)}",
            )

    def get_media_content(self, media_url, get_content=True, is_photo=False):
        session = requests.Session()

        self.log_social_message(
            f"------------POST {self.key_log} GET MEDIA : {media_url}----------------"
        )
        try:
            headers = {
                "Accept": "video/*" if not is_photo else "image/*",
                "User-Agent": generate_desktop_user_agent(),
            }
            with session.get(
                media_url, headers=headers, timeout=(10, 120), stream=True
            ) as response:
                self.log_social_message(
                    f"------------POST {self.key_log} START STREAMING----------------"
                )
                self.save_uploading(5)
                response.raise_for_status()

                media_size = int(response.headers.get("content-length"))
                media_type = response.headers.get("content-type")

                content = b"".join(
                    chunk for chunk in response.iter_content(chunk_size=2048)
                )
                if get_content:
                    return content
                self.log_social_message(
                    f"------------POST {self.key_log} GET MEDIA SUCCESSFULLY----------------"
                )
                return {
                    "content": content,
                    "media_size": media_size,
                    "media_type": media_type,
                }

        except Exception as e:
            self.log_social_message(
                f"----------------------- {self.key_log} TIMEOUT GET MEDIA ---------------------------"
            )
            # self.save_uploading(5)
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} SEND POST MEDIA - GET MEDIA URL: {str(e)}",
            )
            return False

    def send_notification(self, message="", description=""):
        type = self.service
        notification = NotificationServices.find_notification_sns(
            post_id=self.post_id, notification_type=type
        )
        if not notification:
            notification = NotificationServices.create_notification(
                user_id=self.user_id,
                batch_id=self.batch_id,
                post_id=self.post_id,
                notification_type=type,
                title=message,
                description=description,
                description_korea=description,
            )
        else:
            NotificationServices.update_notification(
                notification.id,
                status=const.NOTIFICATION_SUCCESS,
                title=message,
                description=description,
                description_korea=description,
            )

    def save_request_log(self, type, request, response):
        RequestSocialLogService.create_request_social_log(
            social=self.service,
            social_post_id=self.social_post_id,
            user_id=self.user.id,
            type=type,
            request=json.dumps(request),
            response=json.dumps(response),
        )
        RequestSocialLogService.increment_request_social_count(
            self.user.id, self.service
        )

    def publish_redis_channel(self, status, value, social_link=""):
        redis_client.publish(
            PROGRESS_CHANNEL,
            json.dumps(
                {
                    "sync_id": self.sync_id,
                    "batch_id": self.batch_id,
                    "link_id": self.link_id,
                    "post_id": self.post_id,
                    "social_link": social_link,
                    "status": status,
                    "value": value,
                }
            ),
        )

    def save_social_post_publish(self, status, social_link):
        update_social_data.delay(
            social_id=self.social_post.id,
            status=status,
            social_link=social_link,
            process_number=100,
        )

        PostService.update_post(self.post_id, status=1)
        RequestSocialLogService.increment_social_post_created(
            self.user.id, self.service
        )

    def save_social_post_error(
        self, status, message, base_message="", instagram_quote=""
    ):
        status = SocialMedia.ERRORED.value
        if self.service == SocialMedia.INSTAGRAM.value:
            status = SocialMedia.PUBLISHED.value

        update_social_data.delay(
            social_id=self.social_post.id,
            status=status,
            error_message=message,
            show_message=base_message,
            process_number=100,
        )

        PostService.update_post(self.post_id, status=1)

    def log_social_message(self, message):
        if self.service == "FACEBOOK":
            log_facebook_message(message)
        elif self.service == "X-TWITTER":
            log_twitter_message(message)
        elif self.service == "YOUTUBE":
            log_youtube_message(message)
        elif self.service == "TIKTOK":
            log_tiktok_message(message)
        elif self.service == "THREAD":
            log_thread_message(message)

    def save_errors(
        self,
        status,
        message,
        base_message="",
        instagram_quote="",
    ):
        # redis_key = f"toktak:has_error:boundio:{self.post_id}:{self.link_id}"
        # is_has_error = redis_client.get(redis_key)
        save_message = f"{self.service}: {message}"
        self.publish_redis_channel(status, 100)
        self.log_social_message(save_message)
        # if is_has_error:
        #     return
        self.save_social_post_error(
            status,
            save_message,
            base_message=base_message,
            instagram_quote=instagram_quote,
        )
        # redis_client.set(redis_key, 1, ex=10)

    def save_publish(self, status, social_link):
        self.save_social_post_publish(status, social_link)
        self.publish_redis_channel(status, 100, social_link)
        self.log_social_message(
            f"---- {self.service} --- {self.key_log} --- PUBLISHED ----"
        )

    def save_uploading(self, value):
        self.publish_redis_channel("UPLOADING", value)
        update_social_data.delay(
            social_id=self.social_post.id,
            status="UPLOADING",
            process_number=value,
        )
