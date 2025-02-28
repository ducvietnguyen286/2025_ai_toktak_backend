from io import BytesIO
import json
import os

import requests
from app.lib.logger import log_social_message
from app.services.request_social_log import RequestSocialLogService
from app.services.social_post import SocialPostService
from app.services.user import UserService
import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request


TOKEN_URI = "https://oauth2.googleapis.com/token"
CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID") or ""
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET") or ""


class YoutubeTokenService:

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
                user_id=user_link.user_id,
                type="exchange_code_for_token",
                request=json.dumps(data),
                response=json.dumps(response_data),
            )

            if "access_token" not in response_data:
                log_social_message(f"Error exchange_code_for_token: {response_data}")
                return None

            meta = json.loads(user_link.meta)
            meta["access_token"] = response_data["access_token"]
            meta["refresh_token"] = response_data["refresh_token"]
            user_link.meta = json.dumps(meta)
            user_link.save()

            return True
        except Exception as e:
            log_social_message(f"Error exchange_code_for_token: {str(e)}")
            return False


class YoutubeService:
    def __init__(self):
        self.user_link = None
        self.user = None
        self.link = None
        self.meta = None
        self.social_post = None

    def send_post(self, post, link, social_post_id):
        user_id = post.user_id
        self.user = UserService.find_user(user_id)
        self.link = link
        self.user_link = UserService.find_user_link(link_id=link.id, user_id=user_id)
        self.meta = json.loads(self.user_link.meta)
        self.social_post = SocialPostService.find_social_post(social_post_id)

        if post.type == "video":
            self.send_post_video(post)

    def get_youtube_service_from_token(self, user_link):
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

            if credentials.expired:
                try:
                    credentials.refresh(Request())
                    meta["access_token"] = credentials.token
                    user_link.meta = json.dumps(meta)
                    user_link.save()
                except Exception as e:
                    user_link.status = 0
                    user_link.save()
                    log_social_message(
                        "Error get_youtube_service_from_token: Refresh token failed"
                    )
                    return None

            return build("youtube", "v3", credentials=credentials)
        except HttpError as e:
            log_social_message(f"Error get_youtube_service_from_token: {str(e)}")
            return None

    def send_post_video(self, post):
        youtube = self.get_youtube_service_from_token(self.user_link)
        if not youtube:
            return None

        post_title = post.title
        post_description = post.content + " " + post.hashtag + " #shorts"
        tags = post.hashtag
        tags = tags.split(" ") if tags else []

        video_url = post.video_url
        video_content = requests.get(video_url).content

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
        try:
            media = MediaIoBaseUpload(
                video_io, mimetype="video/mp4", chunksize=-1, resumable=True
            )
            request = youtube.videos().insert(
                part="snippet,status", body=body, media_body=media
            )
        except Exception as e:
            log_social_message(f"Error send_post_video: {str(e)}")
            return

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print("Đang upload: {}%".format(int(status.progress() * 100)))
        print("Upload hoàn tất! Video ID: {}".format(response.get("id")))

        RequestSocialLogService.create_request_social_log(
            social="YOUTUBE",
            user_id=self.user_id,
            type="upload_video",
            request=json.dumps(body),
            response=json.dumps(response),
        )

        if "error" in response:
            self.social_post.status = "ERRORED"
            self.social_post.error_message = response["error"]["message"]
            self.social_post.save()
        else:
            try:
                video_id = response["id"]
            except Exception as e:
                try:
                    video_id = response.get("id")
                except Exception as e:
                    log_social_message(f"Error send_post_video: {str(e)}")
                    return None

            permalink = f"https://www.youtube.com/watch?v={video_id}"
            self.social_post.status = "PUBLISHED"
            self.social_post.social_link = permalink
            self.social_post.save()

        return response
