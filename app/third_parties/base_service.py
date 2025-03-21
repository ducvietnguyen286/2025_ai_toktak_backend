import json
import os

import requests
from urllib3 import Retry
from requests.adapters import HTTPAdapter

from app.extensions import redis_client
from app.lib.header import generate_desktop_user_agent
from app.lib.logger import (
    log_thread_message,
    log_youtube_message,
    log_facebook_message,
    log_twitter_message,
    log_tiktok_message,
)
from app.services.request_social_log import RequestSocialLogService

PROGRESS_CHANNEL = os.environ.get("REDIS_PROGRESS_CHANNEL") or "progessbar"


class BaseService:
    def __init__(self):
        self.sync_id = ""
        self.batch_id = None
        self.link_id = None
        self.post_id = None
        self.social_post = None
        self.service = None
        self.key_log = ""

    def get_media_content_by_path(self, media_path, get_content=True, is_photo=False):
        try:
            with open(media_path, "rb") as file:
                content = file.read()
                if get_content:
                    return content
                return {
                    "content": content,
                    "media_size": len(content),
                    "media_type": "image/*" if is_photo else "video/*",
                }
        except Exception as e:
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} SEND POST MEDIA - GET MEDIA PATH: {str(e)}",
            )

    def get_media_content(self, media_url, get_content=True, is_photo=False):
        session = requests.Session()
        # retries = Retry(
        #     total=5, backoff_factor=5, status_forcelist=[500, 502, 503, 504]
        # )
        # session.mount("http://", HTTPAdapter(max_retries=retries))
        # session.mount("https://", HTTPAdapter(max_retries=retries))

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
            try:
                media_content = session.get(media_url, timeout=(10, 60))
                self.log_social_message(
                    f"------------POST {self.key_log} GET MEDIA SUCCESSFULLY----------------"
                )
                if get_content:
                    return media_content.content

                media_size = int(media_content.headers.get("content-length"))
                media_type = media_content.headers.get("content-type")

                return {
                    "content": media_content.content,
                    "media_size": media_size,
                    "media_type": media_type,
                }
            except Exception as e:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} SEND POST MEDIA - GET MEDIA URL: {str(e)}",
                )
                return False

    def save_request_log(self, type, request, response):
        RequestSocialLogService.create_request_social_log(
            social=self.service,
            social_post_id=self.social_post_id,
            user_id=self.user.id,
            type=type,
            request=json.dumps(request),
            response=json.dumps(response),
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
        self.social_post.status = status
        self.social_post.social_link = social_link
        self.social_post.process_number = 100
        self.social_post.save()

    def save_social_post_error(self, status, message):
        self.social_post.status = status
        self.social_post.error_message = message
        self.social_post.process_number = 100
        self.social_post.save()

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

    def save_errors(self, status, message):
        # redis_key = f"toktak:has_error:boundio:{self.post_id}:{self.link_id}"
        # is_has_error = redis_client.get(redis_key)
        save_message = f"{self.service}: {message}"
        self.publish_redis_channel(status, 100)
        self.log_social_message(save_message)
        # if is_has_error:
        #     return
        self.save_social_post_error(status, save_message)
        # redis_client.set(redis_key, 1, ex=10)

    def save_publish(self, status, social_link):
        self.save_social_post_publish(status, social_link)
        self.publish_redis_channel(status, 100, social_link)
        self.log_social_message(
            f"---- {self.service} --- {self.key_log} --- PUBLISHED ----"
        )

    def save_uploading(self, value):
        self.publish_redis_channel("UPLOADING", value)
        self.social_post.status = "UPLOADING"
        self.social_post.process_number = value
        self.social_post.save()
