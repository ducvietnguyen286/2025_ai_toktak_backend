import json
import os
import time
import traceback
import uuid

import requests
from app.enums.limit import LimitSNS
from app.services.post import PostService
from app.services.request_social_log import RequestSocialLogService
from app.services.social_post import SocialPostService
from app.services.user import UserService
from app.lib.logger import log_tiktok_message
from app.third_parties.base_service import BaseService
from app.extensions import redis_client

PROGRESS_CHANNEL = os.environ.get("REDIS_PROGRESS_CHANNEL") or "progessbar"


class TiktokTokenService:

    @staticmethod
    def fetch_user_info(user_link):
        try:
            log_tiktok_message(
                "------------------  FETCH TIKTOK USER INFO  ------------------"
            )
            meta = json.loads(user_link.meta)
            access_token = meta.get("access_token")

            URL_USER_INFO = f"https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id,avatar_url,display_name,username"

            response = requests.get(
                URL_USER_INFO, headers={"Authorization": f"Bearer {access_token}"}
            )
            res = response.json()

            RequestSocialLogService.create_request_social_log(
                social="TIKTOK",
                social_post_id=0,
                user_id=user_link.user_id,
                type="fetch_user_info",
                request="{}",
                response=json.dumps(res),
            )

            log_tiktok_message(f"Fetch user info response: {res}")

            data = res.get("data", {})
            user_data = data.get("user", {})

            return {
                "id": user_data.get("open_id") or "",
                "username": user_data.get("username") or "",
                "name": user_data.get("display_name") or "",
                "avatar": user_data.get("avatar_url") or "",
                "url": f"https://www.tiktok.com/@{user_data.get('username')}" or "",
            }
        except Exception as e:
            traceback.print_exc()
            log_tiktok_message(e)
            return None

    @staticmethod
    def refresh_token(link, user):
        try:
            log_tiktok_message(
                "------------------  REFRESH TIKTOK TOKEN  ------------------"
            )

            user_id = user.id

            redis_key_done = f"toktak:users:{user_id}:refreshtoken-done:TIKTOK"
            redis_key_check = f"toktak:users:{user_id}:refresh-token:TIKTOK"
            redis_key_result = f"toktak:users:{user_id}:refresh-token-result:TIKTOK"
            unique_value = f"{time.time()}_{user_id}_{uuid.uuid4()}"
            redis_key_check_count = f"toktak:users:{user_id}:logging:TIKTOK"

            redis_client.rpush(redis_key_check_count, unique_value)
            redis_client.expire(redis_key_check_count, 300)

            is_refresing = redis_client.get(redis_key_check)
            for i in range(3):
                time.sleep(1)
                count_client = redis_client.llen(redis_key_check_count)
                if count_client > 1:
                    unique_values = redis_client.lrange(redis_key_check_count, 0, -1)
                    if (
                        unique_values
                        and unique_values[-1].decode("utf-8") != unique_value
                    ):
                        time.sleep(2)
                        is_refresing = redis_client.get(redis_key_check)
                        if is_refresing:
                            break
                    else:
                        is_refresing = redis_client.get(redis_key_check)
                else:
                    is_refresing = redis_client.get(redis_key_check)

            is_done = ""
            check_refresh = is_refresing.decode("utf-8") if is_refresing else None

            if check_refresh:
                while True:
                    refresh_done = redis_client.get(redis_key_done)
                    refresh_done_str = (
                        refresh_done.decode("utf-8") if refresh_done else None
                    )
                    if refresh_done_str:
                        redis_client.delete(redis_key_check)
                        redis_client.delete(redis_key_done)
                        is_done = refresh_done_str
                        break

                    time.sleep(1)

            if is_done and is_done != "":
                result_redis = redis_client.get(redis_key_result)
                result_redis = json.loads(result_redis) if result_redis else None
                if is_done == "failled":
                    return {"status": "failled", "result": result_redis}
                return {"status": "success", "result": result_redis}

            redis_client.set(redis_key_check, 1, ex=300)

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
                redis_client.set(redis_key_done, "failled", ex=300)
                return f"Error parsing response: {e}", 500

            log_tiktok_message(f"Refresh token response: {token_data}")

            RequestSocialLogService.create_request_social_log(
                social="TIKTOK",
                social_post_id=0,
                user_id=user_link.user_id,
                type="refresh_token",
                request=json.dumps(r_data),
                response=json.dumps(token_data),
            )

            data_token = token_data.get("data")

            if not token_data or not data_token or not data_token.get("access_token"):
                redis_client.set(redis_key_done, "failled", ex=300)
                redis_client.set(redis_key_result, json.dumps(data_token), ex=300)
                return {"status": "failled", "result": data_token}

            meta.update(data_token)
            user_link.meta = json.dumps(meta)
            user_link.save()

            redis_client.set(redis_key_done, "success", ex=300)
            redis_client.set(redis_key_result, json.dumps(data_token), ex=300)

            return {"status": "success", "result": data_token}
        except Exception as e:
            traceback.print_exc()
            log_tiktok_message(e)
            return None


class TiktokService(BaseService):

    def __init__(self, sync_id=""):
        self.sync_id = sync_id
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
        self.link_id = None
        self.social_post_id = 0
        self.service = "TIKTOK"
        self.key_log = ""

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
        self.social_post_id = self.social_post.id
        self.key_log = f"{self.post_id} - {self.social_post.session_key}"

        try:
            self.save_uploading(0)
            log_tiktok_message(
                f"------------ READY TO SEND POST: {post._to_json()} ----------------"
            )
            if post.type == "video":
                self.upload_video(post)
            if post.type == "image":
                self.upload_image(post.images)
            return True
        except Exception as e:
            self.save_errors("ERRORED", f"SEND POST {self.key_log}: {str(e)}")
            return True

    def upload_image(self, medias, retry=0):
        try:
            log_tiktok_message(f"Upload POST: {self.key_log} image to Tiktok")
            access_token = self.meta.get("access_token")
            medias = json.loads(medias)

            replace_url = "https://apitoktak.voda-play.com/"
            need_replace_url = "https://api.toktak.ai/"

            for media in medias:
                if media.startswith(need_replace_url):
                    media = media.replace(need_replace_url, replace_url)

            URL_IMAGE_UPLOAD = (
                "https://open.tiktokapis.com/v2/post/publish/content/init/"
            )

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            }

            payload = {
                "post_info": {
                    "title": self.post.title,
                    "description": self.post.description
                    + "\n\n  #tiktok "
                    + self.post.hashtag,
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

            try:
                upload_response = requests.post(
                    URL_IMAGE_UPLOAD, headers=headers, data=json.dumps(payload)
                )

            except Exception as e:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD IMAGE - REQUEST URL IMAGE: {str(e)}",
                    base_message=str(e),
                )
                return False

            parsed_response = upload_response.json()

            self.save_uploading(self.progress)

            self.save_request_log("upload_image", payload, parsed_response)

            error = parsed_response.get("error")
            error_code = error.get("code")
            if error_code == "access_token_invalid":
                if retry > 0:
                    self.save_errors(
                        "ERRORED",
                        f"POST {self.key_log} UPLOAD IMAGE - Access token invalid",
                        base_message="Access token invalid",
                    )

                    return False
                refreshed = TiktokTokenService.refresh_token(
                    link=self.link, user=self.user
                )
                if refreshed["status"] == "success":
                    new_meta = refreshed["result"]
                    self.meta = new_meta
                    return self.upload_image(medias=json.dumps(medias), retry=retry + 1)
                else:
                    self.save_errors(
                        "ERRORED",
                        f"POST {self.key_log} UPLOAD IMAGE - Access token invalid",
                        base_message="Access token invalid",
                    )
            elif error and error_code != "ok":
                error_message = error.get("message") or "Upload image error"
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD IMAGE: {error_message}",
                    base_message=error_message,
                )
                return False

            publish_id = parsed_response.get("data").get("publish_id")
            status_result = self.check_status(publish_id)
            status = status_result.get("status")
            if status:
                permalink = self.user_link.url
                self.save_publish("PUBLISHED", permalink)
                return True
            else:
                error_message = status.get("message")
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD IMAGE: {error_message}",
                    base_message=error_message,
                )

                return False

        except Exception as e:
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} UPLOAD IMAGE - ERROR: {str(e)}",
                base_message=str(e),
            )
            return False

    def upload_video(self, post):
        try:
            log_tiktok_message(
                f"------------POST {self.key_log} UPLOAD VIDEO TO TIKTOK----------------"
            )

            video_path = post.video_path
            time_waited = 0
            while not video_path and time_waited < 30:
                time.sleep(2)
                time_waited += 2
                post = PostService.find_post(post.id)
                video_path = post.video_path

            video_content = self.get_media_content_by_path(
                media_path=video_path, get_content=False
            )
            if not video_content:
                return False

            upload_info = self.upload_video_init(video_content)
            if not upload_info:
                return False
            info_data = upload_info.get("data")
            publish_id = info_data.get("publish_id")

            status_result = self.check_status(publish_id)
            status = status_result.get("status")
            if status:
                permalink = self.user_link.url
                self.save_publish("PUBLISHED", permalink)
                return True
            else:
                return False
        except Exception as e:
            self.save_errors("ERRORED", f"POST {self.key_log} UPLOAD VIDEO: {str(e)}")
            return False

    def upload_video_by_url(self, media_url, retry=0):
        try:
            log_tiktok_message(f"POST {self.key_log} Upload video to Tiktok")
            URL_VIDEO_UPLOAD = "https://open.tiktokapis.com/v2/post/publish/video/init/"
            access_token = self.meta.get("access_token")

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            }

            payload = {
                "post_info": {
                    "title": self.post.description
                    + "\n\n  #tiktok "
                    + self.post.hashtag,
                    "privacy_level": "SELF_ONLY",  # PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, FOLLOWER_OF_CREATOR, SELF_ONLY,
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                    "video_cover_timestamp_ms": 1000,
                },
                "source_info": {"source": "PULL_FROM_URL", "video_url": media_url},
            }
            try:
                upload_response = requests.post(
                    URL_VIDEO_UPLOAD, headers=headers, data=json.dumps(payload)
                )
            except Exception as e:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD VIDEO INIT - REQUEST URL VIDEO: {str(e)}",
                    base_message=str(e),
                )
                return False

            parsed_response = upload_response.json()

            self.save_uploading(self.progress)

            self.save_request_log("upload_video_by_url_init", payload, parsed_response)

            error = parsed_response.get("error")
            error_code = error.get("code")
            if error_code == "access_token_invalid":
                if retry > 0:
                    self.save_errors(
                        "ERRORED",
                        f"POST {self.key_log} UPLOAD VIDEO INIT: Access token invalid",
                        base_message="Access token invalid",
                    )

                    return False

                refreshed = TiktokTokenService.refresh_token(
                    link=self.link, user=self.user
                )
                if refreshed["status"] == "success":
                    new_meta = refreshed["result"]
                    self.meta = new_meta
                    return self.upload_video_by_url(
                        media_url=media_url, retry=retry + 1
                    )
                else:
                    self.save_errors(
                        "ERRORED",
                        f"POST {self.key_log} UPLOAD VIDEO INIT: Access token invalid",
                        base_message="Access token invalid",
                    )

                    return False
            elif error and error_code != "ok":
                error_message = error.get("message") or "Upload video INIT error"
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD VIDEO INIT - GET ERROR: {error_message}",
                    base_message=error_message,
                )
                return False

            info_data = parsed_response.get("data")
            publish_id = info_data.get("publish_id")

            status_result = self.check_status(publish_id)
            status = status_result.get("status")
            if status:
                log_tiktok_message(f"POST {self.key_log} Upload video success")
                permalink = self.user_link.url
                self.save_publish("PUBLISHED", permalink)
                return True
            else:
                error_message = status.get("message")
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD VIDEO: {error_message}",
                    base_message=error_message,
                )
                return False
        except Exception as e:
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} UPLOAD VIDEO: {str(e)}",
                base_message=str(e),
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
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} CHECK STATUS - REQUEST URL VIDEO: {str(e)}",
                base_message=str(e),
            )
            return {
                "status": False,
                "message": str(e),
            }
        res_json = response.json()

        self.save_request_log("check_status", payload, res_json)

        error = res_json.get("error")
        error_code = error.get("code")
        if error_code == "access_token_invalid":
            if retry > 0:

                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} CHECK STATUS: Access token invalid",
                    base_message="Access token invalid",
                )
                return {
                    "status": False,
                    "message": "Access token invalid",
                }

            refreshed = TiktokTokenService.refresh_token(link=self.link, user=self.user)
            if refreshed["status"] == "success":
                new_meta = refreshed["result"]
                self.meta = new_meta

                if count <= 6:
                    self.save_uploading(self.progress + (count * 10))

                time.sleep(LimitSNS.WAIT_SECOND_CHECK_STATUS.value)
                return self.check_status(publish_id, count=count, retry=retry + 1)
            else:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} CHECK STATUS: Access token invalid",
                    base_message="Access token invalid",
                )
                return {
                    "status": False,
                    "message": "Access token invalid",
                }

        elif error and error_code != "ok":
            error_message = error.get("message") or "Upload video CHECK STATUS error"
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} CHECK STATUS - GET ERROR: {error_message}",
                base_message=error_message,
            )
            return {
                "status": False,
                "message": error_message,
            }
        status = res_json.get("data").get("status")
        if status == "PUBLISH_COMPLETE":
            publicaly_available_post_id = res_json.get("data").get(
                "publicaly_available_post_id"
            )
            return {
                "status": True,
                "publicaly_available_post_id": publicaly_available_post_id,
            }
        if status == "FAILED":
            return {
                "status": False,
                "message": res_json.get("data").get("fail_reason"),
            }
        time.sleep(LimitSNS.WAIT_SECOND_CHECK_STATUS.value)
        return self.check_status(publish_id, count=count + 1, retry=retry)

    def upload_video_init(self, media, retry=0):
        access_token = self.meta.get("access_token")
        media_size = media.get("media_size", 0)
        media_type = media.get("media_type", "")
        media_content = media.get("content", "")

        URL_VIDEO_UPLOAD = "https://open.tiktokapis.com/v2/post/publish/video/init/"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

        chunk_size = 0

        if media_size < 20000000:
            chunk_size = media_size
        else:
            chunk_size = 10000000

        total_chunk = media_size // chunk_size
        if total_chunk <= 0:
            total_chunk = 1

        disable_comment = (
            self.social_post.disable_comment
            if self.social_post.disable_comment
            else False
        )
        privacy_level = (
            self.social_post.privacy_level
            if self.social_post.privacy_level
            else "SELF_ONLY"
        )
        auto_add_music = (
            self.social_post.auto_add_music
            if self.social_post.auto_add_music
            else False
        )
        disable_duet = (
            self.social_post.disable_duet if self.social_post.disable_duet else False
        )
        disable_stitch = (
            self.social_post.disable_stitch
            if self.social_post.disable_stitch
            else False
        )

        payload = {
            "post_info": {
                "title": self.post.description + "\n\n  #tiktok " + self.post.hashtag,
                "privacy_level": privacy_level,  # PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, FOLLOWER_OF_CREATOR, SELF_ONLY,
                "disable_duet": disable_duet,
                "disable_comment": disable_comment,
                "disable_stitch": disable_stitch,
                "auto_add_music": auto_add_music,
                "video_cover_timestamp_ms": 1000,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": media_size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunk,
            },
        }

        try:
            upload_response = requests.post(
                URL_VIDEO_UPLOAD, headers=headers, data=json.dumps(payload)
            )
        except Exception as e:
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} UPLOAD VIDEO INIT - REQUEST URL VIDEO: {str(e)}",
                base_message=str(e),
            )
            return False

        parsed_response = upload_response.json()

        self.save_uploading(self.progress)

        self.save_request_log("upload_video_init", payload, parsed_response)

        error = parsed_response.get("error")
        error_code = error.get("code")
        if error_code == "access_token_invalid":
            if retry > 0:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD VIDEO INIT: Access token invalid",
                    base_message="Access token invalid",
                )

                return False

            refreshed = TiktokTokenService.refresh_token(link=self.link, user=self.user)
            if refreshed["status"] == "success":
                new_meta = refreshed["result"]
                self.meta = new_meta
                return self.upload_video_init(media=media, retry=retry + 1)
            else:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD VIDEO INIT: Access token invalid",
                    base_message="Access token invalid",
                )

                return False
        elif error and error_code != "ok":
            error_message = error.get("message") or "Upload video INIT error"
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} UPLOAD VIDEO INIT - GET ERROR: {error_message}",
                base_message=error_message,
            )
            return False

        info_data = parsed_response.get("data")
        upload_url = info_data.get("upload_url")

        progress_per_chunk = 20 // total_chunk
        left_over = 20 % total_chunk

        is_last_chunk = False
        for i in range(total_chunk):

            is_last_chunk = i == total_chunk - 1

            if is_last_chunk:
                start_bytes = i * chunk_size
                end_bytes = media_size - 1
                current_chunk_size = media_size - (chunk_size * i)
            else:
                start_bytes = i * chunk_size
                end_bytes = min(start_bytes + chunk_size, media_size) - 1
                current_chunk_size = start_bytes - end_bytes + 1

            chunk_data = media_content[start_bytes:end_bytes]

            is_appened = self.upload_video_append(
                upload_url,
                chunk_data,
                current_chunk_size,
                start_bytes,
                end_bytes,
                media_size,
                media_type,
            )

            if not is_appened:
                return False

            self.save_uploading(
                self.progress
                + (progress_per_chunk * i)
                + (is_last_chunk and left_over or 0)
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
            headers = {
                "Content-Range": f"bytes {start_bytes}-{end_bytes}/{total_bytes}",
                "Content-Length": str(current_chunk_size),
                "Content-Type": media_type,
            }
            try:
                response = requests.put(upload_url, headers=headers, data=chunk_data)
            except Exception as e:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD VIDEO APPEND - REQUEST APPEND: {str(e)}",
                    base_message=str(e),
                )
                return False

            try:
                response_put = response.json()
            except ValueError:
                print(response.text)

            self.save_request_log("upload_video_chunk", headers, response_put)

            if response.status_code in (201, 206):
                return True
            else:
                error_message = f"Lỗi tải chunk {start_bytes}-{end_bytes}/{total_bytes}: {response.status_code}, {response.text}"
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD VIDEO APPEND - GET ERROR: {error_message}",
                    base_message=error_message,
                )
                return False
        except Exception as e:
            self.save_errors(
                "ERRORED",
                f"POST {self.key_log} UPLOAD VIDEO APPEND - ERROR: {str(e)}",
                base_message=str(e),
            )
            return False
