# coding: utf8
import datetime
import json
import os
import time
import traceback
from urllib.parse import urlencode
import uuid
from flask import redirect
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
import jwt
import requests
from app.decorators import parameters
from app.lib.logger import logger
from app.lib.response import Response
from app.extensions import redis_client
import secrets

from app.services.auth import AuthService
from app.services.batch import BatchService
from app.services.post import PostService
from app.services.request_social_log import RequestSocialLogService
from app.services.social_post import SocialPostService
from app.services.tiktok_callback import TiktokCallbackService
from app.services.notification import NotificationServices
from app.services.user import UserService
from app.services.link import LinkService
from app.services.user_link import UserLinkService
from app.third_parties.aliexpress import TokenAliExpress
from app.third_parties.facebook import FacebookTokenService
from app.third_parties.tiktok import TiktokTokenService
from app.third_parties.twitter import TwitterTokenService
from app.rabbitmq.producer import (
    send_facebook_message,
    send_instagram_message,
    send_thread_message,
    send_tiktok_message,
    send_twitter_message,
    send_youtube_message,
)
from app.third_parties.youtube import YoutubeTokenService
import const

ns = Namespace(name="user", description="User API")


@ns.route("/links")
class APIUserLinks(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={},
        required=[],
    )
    def get(self, args):
        current_user = AuthService.get_current_identity()
        if not current_user:
            return Response(
                status=401,
                message="Can't User login",
            ).to_dict()
        links = UserService.get_user_links(current_user.id)
        return Response(
            data=links,
            message="Đăng nhập thành công",
        ).to_dict()


@ns.route("/link/<int:id>")
class APIFindUserLink(Resource):

    @jwt_required()
    def get(self, id):
        current_user = AuthService.get_current_identity()
        link = UserService.find_user_link(id, current_user.id)
        if not link:
            return Response(
                message="Không tìm thấy link",
                status=400,
            ).to_dict()

        return Response(
            data=link._to_json(),
            message="Đăng nhập thành công",
        ).to_dict()


@ns.route("/new-link")
class APINewLink(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={"link_id": {"type": "integer"}},
        required=["link_id"],
    )
    def post(self, args):
        try:
            current_user = AuthService.get_current_identity()
            link_id = args.get("link_id", 0)
            link = LinkService.find_link(link_id)

            if not link:
                return Response(
                    message="Không tìm thấy link",
                    status=400,
                ).to_dict()

            link_need_info = link.need_info
            info = {}
            if link_need_info:
                link_need_info = json.loads(link_need_info)
                for key in link_need_info:
                    if key not in args:
                        return Response(
                            message=f"Thiếu thông tin cần thiết: {key}",
                            status=400,
                        ).to_dict()
                    info[key] = args[key]
            else:
                return Response(
                    message="Link chưa setup thông tin cần thiết",
                    status=400,
                ).to_dict()

            user_link = UserService.find_user_link_exist(link_id, current_user.id)
            is_active = True
            if not user_link:
                user_link = UserService.create_user_link(
                    user_id=current_user.id,
                    link_id=link_id,
                    meta=json.dumps(info),
                    status=1,
                )

                is_active = UserLinkService.update_user_link(link, user_link, args)

            else:
                user_link.meta = json.dumps(info)
                user_link.status = 1
                user_link.save()

                is_active = UserLinkService.update_user_link(link, user_link, args)

            if not is_active:
                NotificationServices.create_notification(
                    user_id=current_user.id,
                    title=f"{link.type}이름 연결에 실패했습니다. 계정 정보를 확인해주세요.",
                )

                return Response(
                    message=f"{link.type}이름 연결에 실패했습니다. 계정 정보를 확인해주세요.",
                    code=201,
                ).to_dict()

            NotificationServices.create_notification(
                user_id=current_user.id,
                title=f"{link.type}이름 연결이 완료되었습니다.",
            )

            return Response(
                data=user_link._to_json(),
                message="Thêm link thành công",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Lỗi kết nối",
                status=400,
            ).to_dict()


@ns.route("/send-posts")
class APISendPosts(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "post_ids": {"type": "array", "items": {"type": "integer"}},
        },
        required=["post_ids"],
    )
    def post(self, args):
        try:
            current_user = AuthService.get_current_identity()
            id_posts = args.get("post_ids", [])
            active_links = []
            user_links = UserService.get_original_user_links(current_user.id)
            active_links = [link.link_id for link in user_links if link.status == 1]
            if not active_links:
                return Response(
                    message="Không có link nào được kích hoạt",
                    status=400,
                ).to_dict()
            posts = PostService.get_posts__by_ids(id_posts)
            if not posts:
                return Response(
                    message="Không tìm thấy bài viết",
                    status=400,
                ).to_dict()
            links = LinkService.get_not_json_links()
            link_pluck_by_id = {link.id: link for link in links}

            post_ids = [post.id for post in posts]

            social_sync = SocialPostService.create_social_sync(
                user_id=current_user.id,
                in_post_ids=id_posts,
                post_ids=post_ids,
                status="PROCESSING",
            )

            sync_id = str(social_sync.id)

            social_post_ids = []
            upload = []
            for post in posts:
                batch_id = post.batch_id
                timestamp = int(time.time())
                unique_id = uuid.uuid4().hex

                session_key = f"{timestamp}_{unique_id}"

                for link_id in active_links:
                    link = link_pluck_by_id.get(link_id)
                    if not link:
                        continue
                    if post.type == "blog" and link.social_type != "BLOG":
                        continue
                    if (
                        post.type == "image" or post.type == "video"
                    ) and link.social_type != "SOCIAL":
                        continue
                    if post.type == "image" and link.type == "YOUTUBE":
                        continue

                    social_post = SocialPostService.create_social_post(
                        link_id=link_id,
                        user_id=current_user.id,
                        post_id=post.id,
                        batch_id=batch_id,
                        session_key=session_key,
                        sync_id=sync_id,
                        status="PROCESSING",
                    )

                    social_post_ids.append(social_post.id)

                    upload.append(
                        {
                            "title": link.title,
                            "link_id": link_id,
                            "post_id": post.id,
                            "status": "PROCESSING",
                            "social_link": "",
                            "value": 0,
                            "self_value": 0,
                        }
                    )

                    message = {
                        "action": "SEND_POST_TO_LINK",
                        "message": {
                            "sync_id": sync_id,
                            "link_id": link_id,
                            "post_id": post.id,
                            "user_id": current_user.id,
                            "social_post_id": str(social_post.id),
                            "page_id": "",
                            "is_all": 1,
                        },
                    }

                    if link.type == "FACEBOOK":
                        send_facebook_message(message)
                    if link.type == "TIKTOK":
                        send_tiktok_message(message)
                    if link.type == "X":
                        send_twitter_message(message)
                    if link.type == "YOUTUBE":
                        send_youtube_message(message)
                    if link.type == "THREAD":
                        send_thread_message(message)
                    if link.type == "INSTAGRAM":
                        send_instagram_message(message)

            progress = {
                "sync_id": sync_id,
                "post_ids": post_ids,
                "user_id": current_user.id,
                "total_post": len(posts),
                "total_percent": 0,
                "status": "PROCESSING",
                "upload": upload,
            }

            social_sync.social_post_ids = social_post_ids
            social_sync.save()

            PostService.update_posts_by_ids(post_ids, status=1)

            redis_client.set(f"toktak:progress-sync:{sync_id}", json.dumps(progress))

            return Response(
                data={
                    "sync_id": sync_id,
                    "upload": upload,
                },
                message="Tạo bài viết thành công. Vui lòng đợi trong giây lát",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Tạo bài viết that bai",
                status=400,
            ).to_dict()


@ns.route("/post-to-links")
class APIPostToLinks(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "is_all": {"type": "integer"},
            "link_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "uniqueItems": True,
            },
            "post_id": {"type": "integer"},
            "page_id": {"type": "string"},
        },
        required=["post_id"],
    )
    def post(self, args):
        try:
            current_user = AuthService.get_current_identity()
            is_all = args.get("is_all", 0)
            post_id = args.get("post_id", 0)
            page_id = args.get("page_id", "")
            link_ids = args.get("link_ids", [])

            if not link_ids and is_all == 0:
                return Response(
                    message="Thiếu thông tin link",
                    status=400,
                ).to_dict()

            active_links = []
            if is_all == 0 and len(link_ids) > 0:
                for link_id in link_ids:
                    user_link = UserService.find_user_link(link_id, current_user.id)
                    if not user_link:
                        continue
                    if user_link.status == 0:
                        continue
                    active_links.append(link_id)

            if is_all == 1:
                user_links = UserService.get_original_user_links(current_user.id)
                active_links = [link.link_id for link in user_links if link.status == 1]

            if not active_links:
                return Response(
                    message="Không có link nào được kích hoạt",
                    status=400,
                ).to_dict()

            post = PostService.find_post(post_id)
            if not post:
                return Response(
                    message="Không tìm thấy bài viết",
                    status=400,
                ).to_dict()

            # Update to Uploads
            PostService.update_post(post_id, status=const.DRAFT_STATUS)

            batch_id = post.batch_id

            batch_detail = BatchService.find_batch(batch_id)
            if batch_detail:
                BatchService.update_batch(batch_id, process_status="UPLOAD_SNS")

            links = LinkService.get_not_json_links()
            link_pluck_by_id = {link.id: link for link in links}

            posts = PostService.get_posts__by_batch_id(batch_id)

            total_post = 0
            post_checked = {}
            for post_to_check in posts:
                for link_id in active_links:
                    if post_checked.get(post_to_check.id):
                        continue
                    link = link_pluck_by_id.get(link_id)
                    if not link:
                        continue
                    if post_to_check.type == "blog" and link.social_type != "BLOG":
                        continue
                    if (
                        post_to_check.type == "image" or post_to_check.type == "video"
                    ) and link.social_type != "SOCIAL":
                        continue
                    if post_to_check.type == "image" and link.type == "YOUTUBE":
                        continue
                    post_checked[post_to_check.id] = post_to_check
                    total_post += 1

            total_link = 0
            for link_id in active_links:
                link = link_pluck_by_id.get(link_id)
                if not link:
                    continue
                if post.type == "blog" and link.social_type != "BLOG":
                    continue
                if (
                    post.type == "image" or post.type == "video"
                ) and link.social_type != "SOCIAL":
                    continue
                if post.type == "image" and link.type == "YOUTUBE":
                    continue
                total_link += 1

            progress = {
                "batch_id": batch_id,
                "post_id": post.id,
                "user_id": current_user.id,
                "total_link": total_link,
                "total_post": total_post,
                "total_percent": 0,
                "status": "PROCESSING",
                "upload": [],
            }

            timestamp = int(time.time())
            unique_id = uuid.uuid4().hex

            session_key = f"{timestamp}_{unique_id}"

            for link_id in active_links:
                link = link_pluck_by_id.get(link_id)
                if not link:
                    continue
                if post.type == "blog" and link.social_type != "BLOG":
                    continue
                if (
                    post.type == "image" or post.type == "video"
                ) and link.social_type != "SOCIAL":
                    continue

                if post.type == "image" and link.type == "YOUTUBE":
                    continue

                social_post = SocialPostService.create_social_post(
                    link_id=link_id,
                    user_id=current_user.id,
                    post_id=post.id,
                    batch_id=batch_id,
                    session_key=session_key,
                    status="PROCESSING",
                )

                print("Social post:", social_post)

                progress["upload"].append(
                    {
                        "title": link.title,
                        "link_id": link_id,
                        "post_id": post.id,
                        "status": "PROCESSING",
                        "social_link": "",
                        "value": 0,
                    }
                )

                message = {
                    "action": "SEND_POST_TO_LINK",
                    "message": {
                        "sync_id": "",
                        "link_id": link_id,
                        "post_id": post.id,
                        "user_id": current_user.id,
                        "social_post_id": str(social_post.id),
                        "page_id": page_id,
                        "is_all": is_all,
                    },
                }

                print("Message:", message)

                if link.type == "FACEBOOK":
                    send_facebook_message(message)
                if link.type == "TIKTOK":
                    send_tiktok_message(message)
                if link.type == "X":
                    send_twitter_message(message)
                if link.type == "YOUTUBE":
                    send_youtube_message(message)
                if link.type == "THREAD":
                    send_thread_message(message)
                if link.type == "INSTAGRAM":
                    send_instagram_message(message)

            key_progress = f"{batch_id}_{current_user.id}"

            redis_client.set(
                f"toktak:progress:{key_progress}:{post_id}",
                json.dumps(progress),
            )

            return Response(
                message="Tạo bài viết thành công. Vui lòng đợi trong giây lát",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Tạo bài viết that bai",
                status=400,
            ).to_dict()


@ns.route("/get-facebook-page")
class APIGetFacebookPage(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={},
        required=[],
    )
    def get(self, args):
        current_user = AuthService.get_current_identity()
        user_links = UserService.get_original_user_links(current_user.id)
        link = LinkService.find_link_by_type("FACEBOOK")
        if not link:
            return Response(
                message="Không tìm thấy link Facebook",
                status=400,
            ).to_dict()
        facebook_links = []
        for user_link in user_links:
            if user_link.link_id == link.id:
                facebook_links.append(user_link)
        if not facebook_links:
            return Response(
                message="Không có link Facebook",
                status=400,
            ).to_dict()
        list_pages = []
        for link in facebook_links:
            token_pages = FacebookTokenService().fetch_page_token(link)
            if not token_pages:
                continue
            for page in token_pages:
                list_pages.append(
                    {
                        "id": page.get("id"),
                        "name": page.get("name"),
                        "picture": page.get("picture"),
                    }
                )
        return Response(
            data=list_pages,
            message="Lấy link Facebook thành công",
        ).to_dict()


TIKTOK_REDIRECT_URL = (
    os.environ.get("CURRENT_DOMAIN") + "/api/v1/user/oauth/tiktok-callback"
)
TIKTOK_AUTHORIZATION_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY") or ""
TIKTOK_CLIENT_SECRET_KEY = os.environ.get("TIKTOK_CLIENT_SECRET") or ""


@ns.route("/oauth/tiktok-login")
class APITiktokLogin(Resource):

    @parameters(
        type="object",
        properties={
            "user_id": {"type": "string"},
            "link_id": {"type": "string"},
        },
        required=["user_id", "link_id"],
    )
    def get(self, args):
        try:
            user_id = args.get("user_id")
            link_id = args.get("link_id")
            state_token = self.generate_state_token(user_id, link_id)
            scope = "user.info.basic,user.info.profile,video.publish,video.upload"

            params = {
                "client_key": TIKTOK_CLIENT_KEY,
                "scope": scope,
                "redirect_uri": TIKTOK_REDIRECT_URL,
                "state": state_token,
                "response_type": "code",
                "disable_auto_auth": 1,
            }
            url = f"{TIKTOK_AUTHORIZATION_URL}?{urlencode(params)}"

            logger.info(f"Redirect to Tiktok: {url}")

            return redirect(url)
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            print(f"Error send post to link: {str(e)}")
            return False

    def generate_state_token(self, user_id, link_id):

        nonce = secrets.token_urlsafe(16)
        payload = {
            "nonce": nonce,
            "user_id": user_id,
            "link_id": link_id,
            "exp": (datetime.datetime.now() + datetime.timedelta(days=30)).timestamp(),
        }
        token = jwt.encode(payload, TIKTOK_CLIENT_SECRET_KEY, algorithm="HS256")
        return token


@ns.route("/oauth/tiktok-callback")
class APIGetCallbackTiktok(Resource):

    @parameters(
        type="object",
        properties={
            "code": {"type": "string"},
            "state": {"type": "string"},
            "error": {"type": "string"},
            "error_description": {"type": "string"},
        },
        required=["code", "state"],
    )
    def get(self, args):
        try:
            code = args.get("code")
            state = args.get("state")
            error = args.get("error") or ""
            error_description = args.get("error_description") or ""
            PAGE_PROFILE = "https://voda-play.com/profile"

            if not state:
                return Response(
                    message="Invalid or expired state token 1",
                    status=400,
                ).to_dict()

            payload = self.verify_state_token(state)

            if not payload:
                return Response(
                    message="Invalid or expired state token 2",
                    status=400,
                ).to_dict()

            if error:
                return Response(
                    message=error_description,
                    status=400,
                ).to_dict()

            TiktokCallbackService().create_tiktok_callback(
                code=code,
                state=state,
                response="{}",
                error=error,
                error_description=error_description,
            )

            TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

            r_data = {
                "client_key": TIKTOK_CLIENT_KEY,
                "client_secret": TIKTOK_CLIENT_SECRET_KEY,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": TIKTOK_REDIRECT_URL,
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            response = requests.post(TOKEN_URL, data=r_data, headers=headers)

            try:
                token_data = response.json()
            except Exception as e:
                return f"Error parsing response: {e}", 500

            user_id = payload.get("user_id")
            link_id = payload.get("link_id")
            int_user_id = int(user_id)
            int_link_id = int(link_id)
            user_link = UserService.find_user_link_exist(int_link_id, int_user_id)

            RequestSocialLogService.create_request_social_log(
                social="TIKTOK",
                user_id=int_user_id,
                type="authorization_code",
                request=json.dumps(r_data),
                response=json.dumps(token_data),
            )

            message = token_data.get("message")

            if message and message == "error":
                error_data = token_data.get("data")
                error = error_data.get("error_code")
                error_description = error_data.get("description")
                return redirect(
                    PAGE_PROFILE
                    + "?error="
                    + error
                    + "&error_description="
                    + error_description
                )

            print("Token data:", token_data)

            token = token_data.get("data")
            if not token:
                token = token_data

            if not user_link:
                user_link = UserService.create_user_link(
                    user_id=int_user_id,
                    link_id=int_link_id,
                    status=1,
                    meta=json.dumps(token),
                )
            else:
                user_link.meta = json.dumps(token)
                user_link.status = 1
                user_link.save()

            user_info = TiktokTokenService().fetch_user_info(user_link)
            logger.info(f"-----------TIKTOK DATA: {user_info}-------------")
            if user_info:
                social_id = user_info.get("id") or ""
                username = user_info.get("username") or ""
                name = user_info.get("name") or ""
                avatar = user_info.get("avatar") or ""
                url = user_info.get("url") or ""

                user_link.social_id = social_id
                user_link.username = username
                user_link.name = name
                user_link.avatar = avatar
                user_link.url = url
                user_link.save()

            return redirect(PAGE_PROFILE + "?success=1")
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            print(f"Error send post to link: {str(e)}")
            return "Can't connect to Tiktok", 500

    def verify_state_token(self, token):
        try:
            payload = jwt.decode(token, TIKTOK_CLIENT_SECRET_KEY, algorithms=["HS256"])
            return payload
        except Exception as e:
            print(f"Error verify state token: {str(e)}")
            return None


@ns.route("/oauth/tiktok-refresh-token")
class APIRefreshTiktokToken(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "link_id": {"type": "integer"},
        },
        required=["link_id"],
    )
    def post(self, args):
        try:
            current_user = AuthService.get_current_identity()
            link_id = args.get("link_id")
            link = LinkService.find_link(link_id)
            if not link:
                return Response(
                    message="Không tìm thấy link",
                    status=400,
                ).to_dict()

            refresh_token = TiktokTokenService().refresh_token(link, current_user)
            print("Refresh token:", refresh_token)
            if not refresh_token:
                return Response(
                    message="Không tìm thấy refresh token",
                    status=400,
                ).to_dict()

            return Response(data=refresh_token, message="Refresh token").to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Lỗi kết nối",
                status=400,
            ).to_dict()


@ns.route("/oauth/ali-login")
class APITiktokLogin(Resource):

    @parameters(
        type="object",
        properties={
            "user_id": {"type": "string"},
        },
        required=["user_id"],
    )
    def get(self, args):
        try:
            user_id = args.get("user_id")
            state_token = self.generate_state_token(user_id)

            ALI_APP_KEY = os.environ.get("ALI_APP_KEY") or ""
            ALI_REDIRECT_URL = os.environ.get("ALI_REDIRECT_URL") or ""

            params = {
                "client_id": ALI_APP_KEY,
                "redirect_uri": ALI_REDIRECT_URL,
                "state": state_token,
                "response_type": "code",
            }
            url = f"https://api-sg.aliexpress.com/oauth/authorize?{urlencode(params)}"

            logger.info(f"Redirect to Ali: {url}")

            return redirect(url)
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            print(f"Error send post to link: {str(e)}")
            return False

    def generate_state_token(self, user_id):
        nonce = secrets.token_urlsafe(16)
        ALI_APP_SECRET = os.environ.get("ALI_APP_SECRET") or ""
        payload = {
            "nonce": nonce,
            "user_id": user_id,
            "exp": (datetime.datetime.now() + datetime.timedelta(days=7)).timestamp(),
        }
        token = jwt.encode(payload, ALI_APP_SECRET, algorithm="HS256")
        return token


@ns.route("/oauth/ali-callback")
class APIAliCallback(Resource):

    @parameters(
        type="object",
        properties={
            "code": {"type": "string"},
            "state": {"type": "string"},
        },
        required=["code", "state"],
    )
    def get(self, args):
        try:
            code = args.get("code")
            state = args.get("state")

            PAGE_PROFILE = "https://voda-play.com/profile"

            if not state:
                return Response(
                    message="Invalid or expired state token 1",
                    status=400,
                ).to_dict()

            payload = self.verify_state_token(state)

            if not payload:
                return Response(
                    message="Invalid or expired state token 2",
                    status=400,
                ).to_dict()

            user_id = payload.get("user_id")
            user = UserService.find_user(user_id)
            if not user:
                return Response(
                    message="Không tìm thấy người dùng",
                    status=400,
                ).to_dict()

            access_response = TokenAliExpress().get_access_token(code)
            if not access_response:
                return Response(
                    message="Lỗi kết nối",
                    status=400,
                ).to_dict()

            user.ali_express_info = json.dumps(access_response)
            user.ali_express_active = 1
            user.save()

            return Response(
                data=access_response,
                message="AliExpress login success",
            ).to_dict()

            return redirect(PAGE_PROFILE + "?success=1")
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Lỗi kết nối",
                status=400,
            ).to_dict()

    def verify_state_token(self, token):
        try:
            ALI_APP_SECRET = os.environ.get("ALI_APP_SECRET") or ""
            payload = jwt.decode(token, ALI_APP_SECRET, algorithms=["HS256"])
            return payload
        except Exception as e:
            print(f"Error verify state token: {str(e)}")
            return None


@ns.route("/check-sns-link")
class APICheckSNSLink(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "batchId": {"type": ["string", "null"]},
        },
        required=[],
    )
    def post(self, args):
        try:
            batchId = args.get("batchId", None)
            current_user = AuthService.get_current_identity()
            if not current_user:
                return Response(
                    message="로그인하여 계속 진행하십시오.",
                    code=201,
                ).to_dict()

            if current_user.subscription == "FREE":
                return Response(
                    message="쿠폰을 입력하여 계속 진행하십시오.",
                    code=201,
                ).to_dict()

            if batchId:
                current_month = time.strftime("%Y-%m", time.localtime())
                if current_user.batch_of_month != current_month:
                    current_user.batch_of_month = current_month
                    current_user.batch_total = 0
                    current_user.save()
                else:
                    if (
                        current_user.batch_total
                        >= const.LIMIT_BATCH[current_user.subscription]
                    ):
                        return Response(
                            message="Bạn đã tạo quá số lượng batch cho phép.",
                            code=201,
                        ).to_dict()
                BatchService.update_batch(batchId, user_id=current_user.id)
                PostService.update_post_by_batch_id(batchId, user_id=current_user.id)

                user_links = UserService.get_original_user_links(current_user.id)
                active_links = [link.link_id for link in user_links if link.status == 1]

                if not active_links:
                    return Response(
                        message="SNS 연동이 필요해요",
                        code=201,
                    ).to_dict()

                batch_detail = BatchService.find_batch(batchId)
                if not batch_detail:
                    return Response(
                        message="Batch not found",
                        code=201,
                    ).to_dict()

            return Response(
                message="Check Active Link Success",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Check Active",
                code=201,
            ).to_dict()


@ns.route("/user_detail")
class APIUserDetail(Resource):
    @jwt_required()
    def post(self):
        try:
            current_user = AuthService.get_current_identity()
            if not current_user:
                return Response(
                    message="Please login",
                    code=201,
                ).to_dict()

            return Response(
                data=current_user.to_dict(),
                message="Check User Success",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Check Active",
                code=201,
            ).to_dict()


@ns.route("/delete-link-sns")
class APIDeleteLink(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "link_id": {"type": "integer"},
        },
        required=["link_id"],
    )
    def post(self, args):
        try:
            current_user = AuthService.get_current_identity()
            link_id = args.get("link_id", 0)

            user_link = UserService.find_user_link(link_id, current_user.id)
            if not user_link:
                return Response(
                    message="링크 삭제에 실패했습니다.",
                    data={"user_id": current_user.id},
                    code=201,
                ).to_dict()
            else:
                user_link.delete()

            return Response(
                data={},
                message="링크 삭제에 성공했습니다.",
            ).to_dict()
        except Exception as ex:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(ex)))
            return Response(
                message="링크 삭제에 실패했습니다.",
                code=202,
            ).to_dict()
