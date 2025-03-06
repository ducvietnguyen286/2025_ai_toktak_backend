from io import BytesIO
import json
import os

import requests
from app.lib.logger import log_youtube_message
from app.services.request_social_log import RequestSocialLogService
from app.services.social_post import SocialPostService
from app.services.user import UserService
import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from app.third_parties.base_service import BaseService

PROGRESS_CHANNEL = os.environ.get("REDIS_PROGRESS_CHANNEL") or "progessbar"


TOKEN_URI = "https://oauth2.googleapis.com/token"
CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID") or ""
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET") or ""


class YoutubeTokenService:

    def fetch_channel_info(self, user_link):
        try:
            PAGE_URL = (
                f"https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true"
            )
            meta = json.loads(user_link.meta)
            access_token = meta.get("access_token")
            if not access_token:
                log_youtube_message("Error fetch_channel_info: access_token not found")
                return None

            response = requests.get(
                PAGE_URL, headers={"Authorization": f"Bearer {access_token}"}
            ).json()

            RequestSocialLogService.create_request_social_log(
                social="YOUTUBE",
                social_post_id="",
                user_id=user_link.user_id,
                type="fetch_channel_info",
                request=json.dumps({}),
                response=json.dumps(response),
            )

            if "items" not in response:
                log_youtube_message(f"Error fetch_channel_info: {response}")
                return None

            item = response["items"][0]

            return {
                "id": item["id"] or "",
                "name": item["snippet"]["title"] or "",
                "avatar": item["snippet"]["thumbnails"]["default"]["url"] or "",
                "url": f"https://www.youtube.com/{item['snippet']['customUrl']}" or "",
            }
        except Exception as e:
            log_youtube_message(f"Error fetch_channel_info: {str(e)}")
            return None

    def exchange_code_for_token(self, code, user_link):
        try:
            REDIRECT_URI = os.environ.get("YOUTUBE_REDIRECT_URI") or ""

            data = {
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            }

            response = requests.post(TOKEN_URI, data=data)
            response_data = response.json()

            RequestSocialLogService.create_request_social_log(
                social="YOUTUBE",
                social_post_id="",
                user_id=user_link.user_id,
                type="exchange_code_for_token",
                request=json.dumps(data),
                response=json.dumps(response_data),
            )

            if "access_token" not in response_data:
                log_youtube_message(f"Error exchange_code_for_token: {response_data}")
                return None

            meta = json.loads(user_link.meta)
            meta["access_token"] = response_data["access_token"]
            meta["refresh_token"] = response_data["refresh_token"]
            user_link.meta = json.dumps(meta)
            user_link.save()

            return True
        except Exception as e:
            log_youtube_message(f"Error exchange_code_for_token: {str(e)}")
            return False


class YoutubeService(BaseService):
    def __init__(self):
        self.user_link = None
        self.user = None
        self.link = None
        self.meta = None
        self.social_post = None
        self.user_id = None
        self.link_id = None
        self.post_id = None
        self.batch_id = None
        self.social_post_id = ""
        self.service = "YOUTUBE"
        self.key_log = ""

    def send_post(self, post, link, user_id, social_post_id):
        self.user_id = user_id
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
            log_youtube_message(
                f"------------ READY TO SEND POST: {post._to_json()} ----------------"
            )
            if post.type == "video":
                self.send_post_video(post)
            return True
        except Exception as e:
            self.save_errors("ERRORED", f"SEND POST {self.key_log}: {str(e)}")
            return True

    def get_youtube_service_from_token(self, user_link):
        log_youtube_message(
            f"----------------------- GET {self.key_log} YOUTUBE SERVICE ---------------------------"
        )
        try:
            meta = json.loads(user_link.meta)
            access_token = meta.get("access_token")
            refresh_token = meta.get("refresh_token")

            SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

            credentials = google.oauth2.credentials.Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri=TOKEN_URI,
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                scopes=SCOPES,
            )

            RequestSocialLogService.create_request_social_log(
                social="YOUTUBE",
                social_post_id=self.social_post_id,
                user_id=user_link.user_id,
                type="get_youtube_service_from_token",
                request=json.dumps(
                    {"access_token": access_token, "refresh_token": refresh_token}
                ),
                response=json.dumps(json.loads(credentials.to_json())),
            )

            if credentials.expired:
                try:
                    credentials.refresh(Request())
                    meta["access_token"] = credentials.token
                    user_link.meta = json.dumps(meta)
                    user_link.save()
                except Exception as e:
                    user_link.status = 0
                    user_link.save()

                    self.save_errors(
                        "ERRORED",
                        f"POST {self.key_log} GET SERVICE - EXPIRED: {str(e)}",
                    )

                    return None

            log_youtube_message(
                f"---------- END {self.key_log} GET YOUTUBE SERVICE --------------"
            )

            return build("youtube", "v3", credentials=credentials)
        except HttpError as e:
            self.save_errors("ERRORED", f"POST {self.key_log} GET SERVICE: {str(e)}")
            return False

    def send_post_video(self, post):
        try:
            youtube = self.get_youtube_service_from_token(self.user_link)
            if not youtube:
                log_youtube_message(
                    f"----------------------- {self.key_log} ERROR: SEND YOUTUBE ERROR ---------------------------"
                )
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} SEND POST VIDEO: Can't get youtube service",
                )
                return False

            post_title = post.title
            post_description = post.description + " " + post.hashtag + " #shorts"
            tags = post.hashtag
            tags = tags.split(" ") if tags else []

            video_url = post.video_url
            try:
                video_content = requests.get(video_url, timeout=20).content
            except Exception as e:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} UPLOAD VIDEO - REQUEST URL VIDEO {media}: {str(e)}",
                )
                return False

            video_io = BytesIO(video_content)
            video_io.seek(0)

            body = {
                "snippet": {
                    "title": post_title,
                    "description": post_description,
                    "tags": tags,
                    "categoryId": 22,  # Ví dụ: "22" cho 'People & Blogs'
                },
                "status": {
                    "privacyStatus": "private"  # "public", "private" hoặc "unlisted"
                },
            }

            log_youtube_message(
                f"----------------------- POST {self.key_log} YOUTUBE START: {post_title}  ---------------------------"
            )

            try:
                media = MediaIoBaseUpload(
                    video_io, mimetype="video/mp4", chunksize=-1, resumable=True
                )
                request = youtube.videos().insert(
                    part="snippet,status", body=body, media_body=media
                )
            except Exception as e:
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} SEND POST VIDEO - REQUEST SEND: {str(e)}",
                )
                return False

            self.save_uploading(10)

            try:
                response = None
                i = 1
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        log_youtube_message(
                            "YOUTUBE Đang upload: {}%".format(
                                int(status.progress() * 100)
                            )
                        )
                    if i <= 7:
                        self.save_uploading(10 + (i * 10))
                    i += 1
            except Exception as e:

                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} SEND POST VIDEO - UPLOAD CHUNK: {str(e)}",
                )
                return False

            log_youtube_message(
                f"----------------------- YOUTUBE UPLOADED {self.key_log}  : RES {response}  ---------------------------"
            )

            RequestSocialLogService.create_request_social_log(
                social="YOUTUBE",
                social_post_id=self.social_post_id,
                user_id=self.user_id,
                type="upload_video",
                request=json.dumps(body),
                response=json.dumps(response),
            )

            if "error" in response:
                message_error = response["error"]["message"]
                self.save_errors(
                    "ERRORED",
                    f"POST {self.key_log} SEND POST VIDEO - GET RESPONSE ERROR: {message_error}",
                )
                return False
            else:
                video_id = ""
                try:
                    video_id = response["id"]
                except Exception as e:
                    try:
                        video_id = response.get("id")
                    except Exception as e:
                        self.save_errors(
                            "ERRORED",
                            f"POST {self.key_log} SEND POST VIDEO - GET VIDEO ID: {str(e)}",
                        )
                        return False

                if not video_id:
                    self.save_errors(
                        "ERRORED", f"POST {self.key_log} SEND POST VIDEO - GET VIDEO ID"
                    )
                    return False

                permalink = f"https://www.youtube.com/watch?v={video_id}"

                self.save_publish("PUBLISHED", permalink)

            return response
        except Exception as e:
            self.save_errors(
                "ERRORED", f"POST {self.key_log} SEND POST VIDEO - ERROR: {str(e)}"
            )
            return False
