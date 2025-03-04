# coding: utf8
import datetime
import json
import os
import traceback
from urllib.parse import urlencode
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
from app.services.user import UserService
from app.services.link import LinkService
from app.third_parties.facebook import FacebookTokenService
from app.third_parties.tiktok import TiktokTokenService
from app.third_parties.twitter import TwitterTokenService
from app.rabbitmq.producer import send_message
from app.third_parties.youtube import YoutubeTokenService

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
        properties={
            "link_id": {"type": "integer"},
            "social_id": {"type": "string"},
            "name": {"type": "string"},
            "avatar": {"type": "string"},
            "url": {"type": "string"},
        },
        required=["link_id", "social_id", "name", "avatar", "url"],
    )
    def post(self, args):
        current_user = AuthService.get_current_identity()
        link_id = args.get("link_id", 0)
        social_id = args.get("social_id", "")
        name = args.get("name", "")
        avatar = args.get("avatar", "")
        url = args.get("url", "")
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

            if link.type == "X":
                user_link.status = 0
                user_link.save()

                code = args.get("Code")
                is_active = TwitterTokenService().fetch_token(code, user_link)

            if link.type == "FACEBOOK":
                user_link.status = 0
                user_link.save()

                access_token = args.get("AccessToken")
                is_active = FacebookTokenService().exchange_token(
                    access_token=access_token, user_link=user_link
                )

            if link.type == "YOUTUBE":
                user_link.status = 0
                user_link.save()

                code = args.get("Code")
                is_active = YoutubeTokenService().exchange_code_for_token(
                    code=code, user_link=user_link
                )
        else:
            user_link.meta = json.dumps(info)
            user_link.status = 1
            user_link.save()

            if link.type == "X":
                user_link.status = 0
                user_link.save()

                code = args.get("Code")
                is_active = TwitterTokenService().fetch_token(code, user_link)
            if link.type == "FACEBOOK":
                user_link.status = 0
                user_link.save()

                access_token = args.get("AccessToken")
                is_active = FacebookTokenService().exchange_token(
                    access_token=access_token, user_link=user_link
                )

            if link.type == "YOUTUBE":
                user_link.status = 0
                user_link.save()

                code = args.get("Code")
                is_active = YoutubeTokenService().exchange_code_for_token(
                    code=code, user_link=user_link
                )

        if is_active:
            user_link.social_id = social_id
            user_link.name = name
            user_link.avatar = avatar
            user_link.url = url
            user_link.status = 1
            user_link.save()

        if not is_active:
            return Response(
                message="Không thể kích hoạt link",
                status=400,
            ).to_dict()

        return Response(
            data=user_link._to_json(),
            message="Thêm link thành công",
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

            if post.status != 1:
                return Response(
                    message="Bài viết chưa được tạo",
                    status=400,
                ).to_dict()

            post = PostService.find_post(post_id)

            batch_id = post.batch_id

            links = LinkService.get_not_json_links()
            link_pluck_by_id = {link.id: link for link in links}

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
                "total_link": total_link,
                "total_percent": 0,
                "status": "PROCESSING",
                "upload": [],
            }

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
                    status="PROCESSING",
                )

                progress["upload"].append(
                    {
                        "link_id": link_id,
                        "post_id": post.id,
                        "status": "PROCESSING",
                        "value": 0,
                    }
                )

                message = {
                    "action": "SEND_POST_TO_LINK",
                    "message": {
                        "link_id": link_id,
                        "post_id": post.id,
                        "user_id": current_user.id,
                        "social_post_id": social_post.id,
                        "page_id": page_id,
                        "is_all": is_all,
                    },
                }
                send_message(message)

            redis_client.set(f"toktak:progress:{batch_id}", json.dumps(progress))

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
            scope = "user.info.basic,video.publish,video.upload"

            params = {
                "client_key": TIKTOK_CLIENT_KEY,
                "scope": scope,
                "redirect_uri": TIKTOK_REDIRECT_URL,
                "state": state_token,
                "response_type": "code",
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
                UserService.create_user_link(
                    user_id=int_user_id,
                    link_id=int_link_id,
                    status=1,
                    meta=json.dumps(token),
                )
            else:
                user_link.meta = json.dumps(token)
                user_link.status = 1
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
