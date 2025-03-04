import json
import os
from app.extensions import redis_client
from app.lib.logger import log_social_message

PROGRESS_CHANNEL = os.environ.get("REDIS_PROGRESS_CHANNEL") or "progessbar"


class BaseService:
    def __init__(self):
        self.batch_id = None
        self.link_id = None
        self.post_id = None
        self.social_post = None
        self.service = None

    def publish_redis_channel(self, status, value):
        redis_client.publish(
            PROGRESS_CHANNEL,
            json.dumps(
                {
                    "batch_id": self.batch_id,
                    "link_id": self.link_id,
                    "post_id": self.post_id,
                    "status": status,
                    "value": value,
                }
            ),
        )

    def save_social_post_publish(self, status, social_link):
        self.social_post.status = status
        self.social_post.social_link = social_link
        self.social_post.save()

    def save_social_post_error(self, status, message):
        self.social_post.status = status
        self.social_post.error_message = message
        self.social_post.save()

    def save_errors(self, status, message):
        redis_key = f"toktak:has_error:boundio:{self.post_id}:{self.link_id}"
        is_has_error = redis_client.get(redis_key)
        save_message = f"{self.service}: {message}"
        if is_has_error:
            log_social_message(save_message)
            return
        self.save_social_post_error(status, save_message)
        self.publish_redis_channel(status, 100)
        redis_client.set(redis_key, 1, ex=60)

    def save_publish(self, status, social_link):
        self.save_social_post_publish(status, social_link)
        self.publish_redis_channel(status, 100)

    def save_uploading(self, value):
        self.publish_redis_channel("UPLOADING", value)
        self.social_post.status = "UPLOADING"
        self.social_post.save()
