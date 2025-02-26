# coding: utf8
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.decorators import parameters
from app.lib.response import Response

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
        },
        required=["provider", "access_token"],
    )
    def post(self, args):
        provider = args.get("provider", "")
        access_token = args.get("access_token", "")

        user = AuthService.social_login(
            provider=provider,
            access_token=access_token,
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
        user = AuthService.get_current_identity()
        return Response(
            data=user._to_json(),
            message="Lấy thông tin người dùng thành công",
        ).to_dict()
