# coding: utf8
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.decorators import parameters
from app.lib.response import Response
from app.services.user import UserService
from datetime import datetime

from app.lib.logger import logger
import json

from app.services.auth import AuthService

ns = Namespace(name="auth", description="Auth API")


@ns.route("/login")
class APILogin(Resource):

    @parameters(
        type="object",
        properties={
            "email": {"type": "string"},
            "password": {"type": "string"},
        },
        required=["email", "password"],
    )
    def post(self, args):
        email = args.get("email", "")
        password = args.get("password", "")

        user = AuthService.login(email, password)
        tokens = AuthService.generate_token(user)
        tokens.update(
            {
                "type": "Bearer",
                "expires_in": 7200,
            }
        )

        return Response(
            data=tokens,
            message="Đăng nhập thành công",
        ).to_dict()


@ns.route("/social-login")
class APISocialLogin(Resource):

    @parameters(
        type="object",
        properties={
            "provider": {"type": "string", "enum": ["FACEBOOK", "GOOGLE"]},
            "access_token": {"type": "string"},
            "person_id": {"type": "string"},
        },
        required=["provider", "access_token"],
    )
    def post(self, args):
        provider = args.get("provider", "")
        access_token = args.get("access_token", "")
        person_id = args.get("person_id", "")

        user = AuthService.social_login(
            provider=provider,
            access_token=access_token,
            person_id=person_id,
        )
        tokens = AuthService.generate_token(user)
        tokens.update(
            {
                "type": "Bearer",
                "expires_in": 7200,
            }
        )

        return Response(
            data=tokens,
            message="Đăng nhập bằng mạng xã hội thành công",
        ).to_dict()


@ns.route("/register")
class APIRegister(Resource):

    @parameters(
        type="object",
        properties={
            "username": {"type": "string"},
            "email": {"type": "string"},
            "password": {"type": "string"},
        },
        required=["email", "password"],
    )
    def post(self, args):
        username = args.get("username", "")
        email = args.get("email", "")
        password = args.get("password", "")

        user = AuthService.register(email, password, username)
        tokens = AuthService.generate_token(user)
        tokens.update(
            {
                "type": "Bearer",
                "expires_in": 7200,
                "user": user._to_json(),
            }
        )

        return Response(
            data=tokens,
            message="Đăng ký thành công",
        ).to_dict()


@ns.route("/refresh-token")
class APIRefreshToken(Resource):

    @jwt_required(refresh=True)
    def post(self):
        tokens = AuthService.refresh_token()
        tokens.update(
            {
                "type": "Bearer",
                "expires_in": 7200,
            }
        )

        return Response(
            data=tokens,
            message="Lấy token mới thành công",
        ).to_dict()


@ns.route("/me")
class APIMe(Resource):

    @jwt_required()
    def get(self):
        user_login = AuthService.get_current_identity()
        
        user_login = AuthService.update(
            user_login.id,
            last_activated=datetime.now,
        )
        return Response(
            data=user_login._to_json(),
            message="사용자 정보를 성공적으로 가져왔습니다.",
        ).to_dict()


@ns.route("/login_by_input")
class APILoginByInput(Resource):

    @parameters(
        type="object",
        properties={
            "email": {"type": "string"},
            "password": {"type": "string"},
        },
        required=["email", "password"],
    )
    def post(self, args):
        email = args.get("email", "")
        password = args.get("password", "")

        user = AuthService.login(email, password)
        if not user:
            return Response(
                code=201,
                message="비밀번호가 정확하지 않습니다.",
            ).to_dict()

        tokens = AuthService.generate_token(user)
        tokens.update(
            {
                "type": "Bearer",
                "expires_in": 7200,
                "user": user._to_json(),
            }
        )

        return Response(
            data=tokens,
            message="Đăng nhập thành công",
        ).to_dict()


@ns.route("/update_user")
class APIMeUpdate(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "name": {"type": "string"},
            "phone": {"type": "string"},
            "contact": {"type": "string"},
            "company_name": {"type": "string"},
        },
        required=[],
    )
    def post(self, args):
        name = args.get("name", "")
        phone = args.get("phone", "")
        contact = args.get("contact", "")
        company_name = args.get("company_name", "")
        user_login = AuthService.get_current_identity()
        user_login = AuthService.update(
            user_login.id,
            name=name,
            phone=phone,
            contact=contact,
            company_name=company_name,
        )

        return Response(
            data=user_login._to_json(),
            message="Update thông tin thành công",
        ).to_dict()


@ns.route("/user_profile")
class APIUserProfile(Resource):

    @jwt_required()
    def get(self):
        user = AuthService.get_current_identity()
        level = user.level
        total_link = UserService.get_user_links(user.id)
        logger.info(f"level : {level} total_link :  {len(total_link)} ")
        if level != len(total_link):
            level = len(total_link)
            level_info = get_level_images(level)
            user = AuthService.update(
                user.id,
                level=level,
                level_info=json.dumps(level_info),
            )

        return Response(
            data=user._to_json(),
            message="Lấy thông tin người dùng thành công",
        ).to_dict()


def get_level_images(level):
    """
    Trả về danh sách ảnh theo cấp độ với một ảnh ngẫu nhiên được đánh dấu active.
    """
    base_url = "https://admin.lang.canvasee.com/img/level/"
    images = []

    if level == 0:
        images = [
            {"url": f"{base_url}level_0.png", "active": ""},
            {"url": f"{base_url}level_0_next.png", "active": ""},
        ]
    elif level == 1:
        images = [
            {"url": f"{base_url}level_1.png", "active": ""},
            {"url": f"{base_url}level_1_next.png", "active": "active"},
        ]
    elif level == 2:
        images = [
            {"url": f"{base_url}level_1.png", "active": ""},
            {"url": f"{base_url}level_2.png", "active": ""},
            {"url": f"{base_url}level_2_next.png", "active": "active"},
        ]
    elif level == 3:
        images = [
            {"url": f"{base_url}level_1.png", "active": ""},
            {"url": f"{base_url}level_2.png", "active": ""},
            {"url": f"{base_url}level_3.png", "active": ""},
            {"url": f"{base_url}level_3_next.png", "active": "active"},
        ]
    elif level == 4:
        images = [
            {"url": f"{base_url}level_1.png", "active": ""},
            {"url": f"{base_url}level_2.png", "active": ""},
            {"url": f"{base_url}level_3.png", "active": ""},
            {"url": f"{base_url}level_4.png", "active": ""},
            {"url": f"{base_url}level_4_next.png", "active": "active"},
        ]
    elif level == 5:
        images = [
            {"url": f"{base_url}level_1.png", "active": ""},
            {"url": f"{base_url}level_2.png", "active": ""},
            {"url": f"{base_url}level_3.png", "active": ""},
            {"url": f"{base_url}level_4.png", "active": ""},
            {"url": f"{base_url}level_5.png", "active": ""},
            {"url": f"{base_url}level_5_next.png", "active": "active"},
        ]
    elif level == 6:
        images = [
            {"url": f"{base_url}level_1.png", "active": ""},
            {"url": f"{base_url}level_2.png", "active": ""},
            {"url": f"{base_url}level_3.png", "active": ""},
            {"url": f"{base_url}level_4.png", "active": ""},
            {"url": f"{base_url}level_5.png", "active": ""},
            {"url": f"{base_url}level_6.png", "active": ""},
            {"url": f"{base_url}level_6_next.png", "active": "active"},
        ]
    elif level == 7:
        images = [
            {"url": f"{base_url}level_1.png", "active": ""},
            {"url": f"{base_url}level_2.png", "active": ""},
            {"url": f"{base_url}level_3.png", "active": ""},
            {"url": f"{base_url}level_4.png", "active": ""},
            {"url": f"{base_url}level_5.png", "active": ""},
            {"url": f"{base_url}level_6.png", "active": ""},
            {"url": f"{base_url}level_7.png", "active": "active"},
        ]

    return images


@ns.route("/delete_account")
class APIDeleteAccount(Resource):
    @jwt_required()
    def post(self):

        user_login = AuthService.get_current_identity()
        if not user_login:
            return Response(
                message="시스템에 로그인해주세요.",
                code=201,
            ).to_dict()

        AuthService.deleteAccount(user_login.id)

        return Response(
            data={},
            message="계정을 성공적으로 삭제했습니다.",
        ).to_dict()
