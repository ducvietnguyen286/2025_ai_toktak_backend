import json
import os
import time
import traceback

import requests
from app.services.request_social_log import RequestSocialLogService
from app.services.social_post import SocialPostService
from app.services.user import UserService
from app.lib.logger import log_social_message
from app.extensions import redis_client

PROGRESS_CHANNEL = os.environ.get("REDIS_PROGRESS_CHANNEL") or "progessbar"


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
            meta.update(data_token)
            user_link.meta = json.dumps(meta)
            user_link.save()

            return token_data
        except Exception as e:
            traceback.print_exc()
            log_social_message(e)
            return None


class TiktokService:

    def __init__(self):
        self.user_link = None
        self.user = None
        self.link = None
        self.meta = None
        self.processing_info = None
        self.post = None
        self.social_post = None
        self.user_id = None
        self.progress = 10
        self.batch_id = None

    def send_post(self, post, link, user_id, social_post_id):
        self.user_id = user_id
        self.user = UserService.find_user(user_id)
        self.link = link
        self.user_link = UserService.find_user_link(link_id=link.id, user_id=user_id)
        self.meta = json.loads(self.user_link.meta)
        self.post = post
        self.social_post = SocialPostService.find_social_post(social_post_id)
        self.link_id = link.id
        self.post_id = post.id
        self.batch_id = post.batch_id

        try:

            if post.type == "video":
                self.upload_video(post.video_url)
            if post.type == "image":
                self.upload_image(post.images)
        except Exception as e:
            log_social_message(f"Error send post to Tiktok {str(e)}")
            self.social_post.status = "ERRORED"
            self.social_post.error_message = str(e)
            self.social_post.save()

            redis_client.publish(
                PROGRESS_CHANNEL,
                json.dumps(
                    {
                        "batch_id": self.batch_id,
                        "link_id": self.link_id,
                        "post_id": self.post_id,
                        "status": "ERRORED",
                        "value": 100,
                    }
                ),
            )
            return False

    def upload_image(self, medias, retry=0):
        try:
            log_social_message("Upload image to Tiktok")
            access_token = self.meta.get("access_token")
            medias = json.loads(medias)

            URL_IMAGE_UPLOAD = (
                "https://open.tiktokapis.com/v2/post/publish/content/init/"
            )

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            }

            log_social_message(headers)

            payload = {
                "post_info": {
                    "title": self.post.title,
                    "description": self.post.content + "  #tiktok " + self.post.hashtag,
                    "privacy_level": "SELF_ONLY",  # PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, FOLLOWER_OF_CREATOR, SELF_ONLY,
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                    "video_cover_timestamp_ms": 1000,
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "photo_cover_index": len(medias) - 1,
                    "photo_images": medias,
                },
                "post_mode": "DIRECT_POST",
                "media_type": "PHOTO",
            }

            log_social_message(f"Payload: {payload}")

            try:
                upload_response = requests.post(
                    URL_IMAGE_UPLOAD, headers=headers, data=json.dumps(payload)
                )

            except Exception as e:
                self.social_post.status = "ERRORED"
                self.social_post.error_message = str(e)
                self.social_post.save()

                redis_client.publish(
                    PROGRESS_CHANNEL,
                    json.dumps(
                        {
                            "batch_id": self.batch_id,
                            "link_id": self.link_id,
                            "post_id": self.post_id,
                            "status": "ERRORED",
                            "value": 100,
                        }
                    ),
                )
                raise Exception("Error upload image to Tiktok")
            parsed_response = upload_response.json()

            redis_client.publish(
                PROGRESS_CHANNEL,
                json.dumps(
                    {
                        "batch_id": self.batch_id,
                        "link_id": self.link_id,
                        "post_id": self.post_id,
                        "status": "UPLOADING",
                        "value": self.progress,
                    }
                ),
            )

            self.social_post.status = "UPLOADING"
            self.social_post.save()

            RequestSocialLogService.create_request_social_log(
                social="TIKTOK",
                user_id=self.user_id,
                type="upload_image",
                request=json.dumps(payload),
                response=json.dumps(parsed_response),
            )

            log_social_message(f"Upload image to Tiktok response: {parsed_response}")

            error = parsed_response.get("error")
            error_code = error.get("code")
            if error_code == "access_token_invalid":
                if retry > 0:
                    self.social_post.status = "ERRORED"
                    self.social_post.error_message = "Access token invalid"
                    self.social_post.save()

                    self.user_link.status = 0
                    self.user_link.save()

                    redis_client.publish(
                        PROGRESS_CHANNEL,
                        json.dumps(
                            {
                                "batch_id": self.batch_id,
                                "link_id": self.link_id,
                                "post_id": self.post_id,
                                "status": "ERRORED",
                                "value": 10,
                            }
                        ),
                    )

                    raise Exception("Retry limit exceeded")
                TiktokTokenService.refresh_token(link=self.link, user=self.user)
                self.user_link = UserService.find_user_link(
                    link_id=self.link.id, user_id=self.user.id
                )
                self.meta = json.loads(self.user_link.meta)
                return self.upload_image(medias=medias, retry=retry + 1)

            publish_id = parsed_response.get("data").get("publish_id")
            status = self.check_status(publish_id)
            if status.get("status"):
                log_social_message("Upload image success")
                self.social_post.status = "PUBLISHED"
                self.social_post.social_link = "profile"
                self.social_post.save()

                redis_client.publish(
                    PROGRESS_CHANNEL,
                    json.dumps(
                        {
                            "batch_id": self.batch_id,
                            "link_id": self.link_id,
                            "post_id": self.post_id,
                            "status": "PUBLISHED",
                            "value": 100,
                        }
                    ),
                )
                return True
            else:
                log_social_message(f"Upload image failed: {status.get('message')}")
                error_message = status.get("message")
                self.social_post.status = "ERRORED"
                self.social_post.error_message = error_message
                self.social_post.save()

                redis_client.publish(
                    PROGRESS_CHANNEL,
                    json.dumps(
                        {
                            "batch_id": self.batch_id,
                            "link_id": self.link_id,
                            "post_id": self.post_id,
                            "status": "ERRORED",
                            "value": 100,
                        }
                    ),
                )
                return False

        except Exception as e:
            log_social_message(f"Error upload image to Tiktok: {str(e)}")

            self.social_post.status = "ERRORED"
            self.social_post.error_message = error_message
            self.social_post.save()

            redis_client.publish(
                PROGRESS_CHANNEL,
                json.dumps(
                    {
                        "batch_id": self.batch_id,
                        "link_id": self.link_id,
                        "post_id": self.post_id,
                        "status": "ERRORED",
                        "value": 100,
                    }
                ),
            )

            return False

    def upload_video(self, media):
        try:
            log_social_message("Upload video to Tiktok")
            # FILE INFO
            response = requests.get(media)

            upload_info = self.upload_video_init(response)
            log_social_message(f"Upload video info: {upload_info}")
            log_social_message(f"Upload video to Tiktok: {media}")
            info_data = upload_info.get("data")
            publish_id = info_data.get("publish_id")

            status = self.check_status(publish_id)
            if status.get("status"):
                log_social_message("Upload video success")
                self.social_post.status = "PUBLISHED"
                self.social_post.social_link = "profile"
                self.social_post.save()
                redis_client.publish(
                    PROGRESS_CHANNEL,
                    json.dumps(
                        {
                            "batch_id": self.batch_id,
                            "link_id": self.link_id,
                            "post_id": self.post_id,
                            "status": "PUBLISHED",
                            "value": 100,
                        }
                    ),
                )
                return True
            else:
                log_social_message(f"Upload video failed: {status.get('message')}")
                error_message = status.get("message")
                self.social_post.status = "ERRORED"
                self.social_post.error_message = error_message
                self.social_post.save()

                redis_client.publish(
                    PROGRESS_CHANNEL,
                    json.dumps(
                        {
                            "batch_id": self.batch_id,
                            "link_id": self.link_id,
                            "post_id": self.post_id,
                            "status": "ERRORED",
                            "value": 100,
                        }
                    ),
                )
                return False
        except Exception as e:
            log_social_message(f"Error upload video to Tiktok: {str(e)}")
            self.social_post.status = "ERRORED"
            self.social_post.error_message = str(e)
            self.social_post.save()

            redis_client.publish(
                PROGRESS_CHANNEL,
                json.dumps(
                    {
                        "batch_id": self.batch_id,
                        "link_id": self.link_id,
                        "post_id": self.post_id,
                        "status": "ERRORED",
                        "value": 100,
                    }
                ),
            )
            return False

    def check_status(self, publish_id, count=1, retry=0):
        access_token = self.meta.get("access_token")
        URL_VIDEO_STATUS = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {"publish_id": publish_id}
        try:
            response = requests.post(
                URL_VIDEO_STATUS, headers=headers, data=json.dumps(payload)
            )
        except Exception as e:
            self.social_post.status = "ERRORED"
            self.social_post.error_message = str(e)
            self.social_post.save()

            redis_client.publish(
                PROGRESS_CHANNEL,
                json.dumps(
                    {
                        "batch_id": self.batch_id,
                        "link_id": self.link_id,
                        "post_id": self.post_id,
                        "status": "ERRORED",
                        "value": 100,
                    }
                ),
            )
            log_social_message(f"Error check status Tiktok: {str(e)}")
            raise Exception("Error check status Tiktok")
        res_json = response.json()

        log_social_message(f"Check status: {res_json}")

        error = res_json.get("error")
        error_code = error.get("code")
        if error_code == "access_token_invalid":
            if retry > 0:
                self.social_post.status = "ERRORED"
                self.social_post.error_message = "Access token invalid"
                self.social_post.save()

                self.user_link.status = 0
                self.user_link.save()

                redis_client.publish(
                    PROGRESS_CHANNEL,
                    json.dumps(
                        {
                            "batch_id": self.batch_id,
                            "link_id": self.link_id,
                            "post_id": self.post_id,
                            "status": "ERRORED",
                            "value": 100,
                        }
                    ),
                )

                raise Exception("Retry limit exceeded")

            TiktokTokenService.refresh_token(link=self.link, user=self.user)
            self.user_link = UserService.find_user_link(
                link_id=self.link.id, user_id=self.user.id
            )
            self.meta = json.loads(self.user_link.meta)

            if count <= 6:
                redis_client.publish(
                    PROGRESS_CHANNEL,
                    json.dumps(
                        {
                            "batch_id": self.batch_id,
                            "link_id": self.link_id,
                            "post_id": self.post_id,
                            "status": "UPLOADING",
                            "value": self.progress + (count * 10),
                        }
                    ),
                )

            time.sleep(3)
            return self.check_status(publish_id, count=count, retry=retry + 1)
        status = res_json.get("data").get("status")
        if status == "PUBLISH_COMPLETE":
            return {"status": True}
        if status == "FAILED":
            return {
                "status": False,
                "message": res_json.get("data").get("fail_reason"),
            }
        time.sleep(3)
        return self.check_status(publish_id, count=count + 1, retry=retry)

    def upload_video_init(self, media, retry=0):
        log_social_message("Upload video to Tiktok INIT")
        access_token = self.meta.get("access_token")
        media_size = int(media.headers.get("content-length"))
        media_type = media.headers.get("content-type")

        URL_VIDEO_UPLOAD = "https://open.tiktokapis.com/v2/post/publish/video/init/"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

        log_social_message(headers)

        chunk_size = 0

        if media_size < 20000000:
            chunk_size = media_size
        else:
            chunk_size = 10000000

        total_chunk = media_size // chunk_size
        if total_chunk <= 0:
            total_chunk = 1

        payload = {
            "post_info": {
                "title": self.post.content + "  #tiktok " + self.post.hashtag,
                "privacy_level": "SELF_ONLY",  # PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, FOLLOWER_OF_CREATOR, SELF_ONLY,
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "video_cover_timestamp_ms": 1000,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": media_size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunk,
            },
        }

        log_social_message(f"Payload: {payload}")
        try:
            upload_response = requests.post(
                URL_VIDEO_UPLOAD, headers=headers, data=json.dumps(payload)
            )
        except Exception as e:
            self.social_post.status = "ERRORED"
            self.social_post.error_message = str(e)
            self.social_post.save()

            redis_client.publish(
                PROGRESS_CHANNEL,
                json.dumps(
                    {
                        "batch_id": self.batch_id,
                        "link_id": self.link_id,
                        "post_id": self.post_id,
                        "status": "ERRORED",
                        "value": 100,
                    }
                ),
            )

            log_social_message(f"Error upload video to Tiktok: {str(e)}")
            raise Exception("Error upload video to Tiktok")

        parsed_response = upload_response.json()

        self.social_post.status = "UPLOADING"
        self.social_post.save()

        redis_client.publish(
            PROGRESS_CHANNEL,
            json.dumps(
                {
                    "batch_id": self.batch_id,
                    "link_id": self.link_id,
                    "post_id": self.post_id,
                    "status": "UPLOADING",
                    "value": self.progress,
                }
            ),
        )

        RequestSocialLogService.create_request_social_log(
            social="TIKTOK",
            user_id=self.user_id,
            type="upload_video",
            request=json.dumps(payload),
            response=json.dumps(parsed_response),
        )

        log_social_message(f"Upload video to Tiktok INIT response: {parsed_response}")

        error = parsed_response.get("error")
        error_code = error.get("code")
        if error_code == "access_token_invalid":
            if retry > 0:
                self.social_post.status = "ERRORED"
                self.social_post.error_message = "Access token invalid"
                self.social_post.save()

                self.user_link.status = 0
                self.user_link.save()

                redis_client.publish(
                    PROGRESS_CHANNEL,
                    json.dumps(
                        {
                            "batch_id": self.batch_id,
                            "link_id": self.link_id,
                            "post_id": self.post_id,
                            "status": "ERRORED",
                            "value": 100,
                        }
                    ),
                )
                raise Exception("Retry limit exceeded")

            TiktokTokenService.refresh_token(link=self.link, user=self.user)
            self.user_link = UserService.find_user_link(
                link_id=self.link.id, user_id=self.user.id
            )
            self.meta = json.loads(self.user_link.meta)
            return self.upload_video_init(media=media, retry=retry + 1)

        info_data = parsed_response.get("data")
        upload_url = info_data.get("upload_url")

        log_social_message(f"Chunk size: {chunk_size}")
        log_social_message(f"Total chunk: {total_chunk}")

        progress_per_chunk = 20 // total_chunk
        left_over = 20 % total_chunk

        is_last_chunk = False
        for i in range(total_chunk):

            is_last_chunk = i == total_chunk - 1

            log_social_message(f"Upload video to Tiktok APPEND {i}")
            if is_last_chunk:
                start_bytes = i * chunk_size
                end_bytes = media_size - 1
                current_chunk_size = media_size - (chunk_size * i)
            else:
                start_bytes = i * chunk_size
                end_bytes = min(start_bytes + chunk_size, media_size) - 1
                current_chunk_size = start_bytes - end_bytes + 1

            chunk_data = media.content[start_bytes:end_bytes]

            self.upload_video_append(
                upload_url,
                chunk_data,
                current_chunk_size,
                start_bytes,
                end_bytes,
                media_size,
                media_type,
            )

            redis_client.publish(
                PROGRESS_CHANNEL,
                json.dumps(
                    {
                        "batch_id": self.batch_id,
                        "link_id": self.link_id,
                        "post_id": self.post_id,
                        "status": "UPLOADING",
                        "value": self.progress
                        + (progress_per_chunk * (i + 1))
                        + (i == total_chunk - 1 and left_over or 0),
                    }
                ),
            )

        return parsed_response

    def upload_video_append(
        self,
        upload_url,
        chunk_data,
        current_chunk_size,
        start_bytes,
        end_bytes,
        total_bytes,
        media_type,
    ):
        try:
            log_social_message("Upload video to Tiktok APPEND")

            headers = {
                "Content-Range": f"bytes {start_bytes}-{end_bytes}/{total_bytes}",
                "Content-Length": str(current_chunk_size),
                "Content-Type": media_type,
            }
            try:
                response = requests.put(upload_url, headers=headers, data=chunk_data)
            except Exception as e:
                self.social_post.status = "ERRORED"
                self.social_post.error_message = str(e)
                self.social_post.save()

                redis_client.publish(
                    PROGRESS_CHANNEL,
                    json.dumps(
                        {
                            "batch_id": self.batch_id,
                            "link_id": self.link_id,
                            "post_id": self.post_id,
                            "status": "ERRORED",
                            "value": 100,
                        }
                    ),
                )

                log_social_message(f"Error upload video to Tiktok: {str(e)}")
                raise Exception("Error upload video to Tiktok")
            response_put = response.json()

            RequestSocialLogService.create_request_social_log(
                social="TIKTOK",
                user_id=self.user_id,
                type="upload_video_chunk",
                request=json.dumps(headers),
                response=json.dumps(response_put),
            )

            log_social_message(f"Upload video to Tiktok APPEND headers: {headers}")
            log_social_message(
                f"Upload video to Tiktok APPEND response: {response_put}"
            )
            log_social_message("Upload video")

            if response.status_code in (201, 206):
                print(
                    f"Chunk {start_bytes}-{end_bytes}/{total_bytes} tải lên thành công. Status code: {response.status_code}"
                )
            else:
                print(
                    f"Lỗi tải chunk {start_bytes}-{end_bytes}/{total_bytes}: {response.status_code}, {response.text}"
                )

            return response_put
        except Exception as e:
            log_social_message(f"Error upload video to Tiktok: {str(e)}")
