# coding: utf8
import base64
import datetime
import hashlib
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
import secrets

from app.rabbitmq.producer import send_message
from app.services.auth import AuthService
from app.services.post import PostService
from app.services.tiktok_callback import TiktokCallbackService
from app.services.user import UserService
from app.services.link import LinkService
from app.third_parties.twitter import TwitterTokenService

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
        },
        required=["link_id"],
    )
    def post(self, args):
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

        user_link = UserService.find_user_link(link_id, current_user.id)
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
        else:
            if link.type == "X":
                code = args.get("Code")
                is_active = TwitterTokenService().fetch_token(code, user_link)
            user_link.meta = json.dumps(info)
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
        },
        required=["post_id"],
    )
    def post(self, args):
        try:
            current_user = AuthService.get_current_identity()
            is_all = args.get("is_all", 0)
            post_id = args.get("post_id", 0)
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
                links = UserService.get_user_links(current_user.id)
                active_links = [link.link_id for link in links if link.status == 1]

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

            for link in active_links:
                message = {
                    "action": "SEND_POST_TO_LINK",
                    "message": {
                        "link_id": link,
                        "post_id": post.id,
                        "user_id": current_user.id,
                    },
                }
                send_message(message)

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


TIKTOK_REDIRECT_URL = (
    os.environ.get("CURRENT_DOMAIN") + "/api/v1/user/oauth/tiktok-callback"
)
TIKTOK_AUTHORIZATION_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY") or ""
TIKTOK_CLIENT_SECRET_KEY = os.environ.get("TIKTOK_CLIENT_SECRET")


@ns.route("/oauth/tiktok-login")
class APITiktokLogin(Resource):

    def get(self, *args, **kwargs):
        try:
            state_token, code_challenge = self.generate_state_token()
            scope = "video.publish,video.upload"

            params = {
                "client_key": TIKTOK_CLIENT_KEY,
                "response_type": "code",
                "scope": scope,
                "redirect_uri": TIKTOK_REDIRECT_URL,
                "state": state_token,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
            url = f"{TIKTOK_AUTHORIZATION_URL}?{urlencode(params)}"
            return redirect(url)
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            print(f"Error send post to link: {str(e)}")
            return False

    def generate_state_token(self):

        nonce = secrets.token_urlsafe(16)
        code_verifier = secrets.token_urlsafe(64)
        m = hashlib.sha256()
        m.update(code_verifier.encode("ascii"))
        code_challenge = (
            base64.urlsafe_b64encode(m.digest()).rstrip(b"=").decode("ascii")
        )
        payload = {
            "nonce": nonce,
            "code_verifier": code_verifier,
            "exp": (datetime.datetime.now() + datetime.timedelta(days=30)).timestamp(),
        }
        token = jwt.encode(payload, TIKTOK_CLIENT_SECRET_KEY, algorithm="HS256")
        return token, code_challenge


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

            code_verifier = payload.get("code_verifier")
            if not code_verifier:
                return Response(
                    message="Invalid or expired state token 3",
                    status=400,
                ).to_dict()

            if error:
                return Response(
                    message=error_description,
                    status=400,
                ).to_dict()
            TOKEN_URL = "https://open-api.tiktok.com/oauth/access_token/"

            data = {
                "client_key": TIKTOK_CLIENT_KEY,
                "client_secret": TIKTOK_CLIENT_SECRET_KEY,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": TIKTOK_REDIRECT_URL,
                "code_verifier": code_verifier,
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            response = requests.post(TOKEN_URL, data=data, headers=headers)

            try:
                token_data = response.json()
            except Exception as e:
                return f"Error parsing response: {e}", 500

            TiktokCallbackService().create(
                code=code,
                state=state,
                content=json.dumps(token_data),
                error=error,
                error_description=error_description,
            )

            return redirect(PAGE_PROFILE)
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
