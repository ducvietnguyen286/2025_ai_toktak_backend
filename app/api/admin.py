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
from app.services.notification import NotificationServices
from app.lib.string import get_level_images

ns = Namespace(name="admin", description="Admin API")



@ns.route("/login")
class APIAdminLoginByInput(Resource):

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

        user = AuthService.loginAdmin(email, password)
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

