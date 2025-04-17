# coding: utf8
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.decorators import parameters, admin_required
from app.lib.response import Response
from app.services.user import UserService
from datetime import datetime

from app.lib.logger import logger
import json
from flask import request
from app.services.auth import AuthService
from app.services.notification import NotificationServices
from app.lib.string import get_level_images
import const

from app.services.social_post import SocialPostService

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


@ns.route("/users")
class APIUsers(Resource):

    @jwt_required()
    @admin_required()
    def get(self):
        page = request.args.get("page", const.DEFAULT_PAGE, type=int)
        per_page = request.args.get("per_page", const.DEFAULT_PER_PAGE, type=int)
        status = request.args.get("status", const.UPLOADED, type=int)
        type_order = request.args.get("type_order", "", type=str)
        type_post = request.args.get("type_post", "", type=str)
        time_range = request.args.get("time_range", "", type=str)
        search = request.args.get("search", "", type=str)
        member_type = request.args.get("member_type", "", type=str)
        data_search = {
            "page": page,
            "per_page": per_page,
            "status": status,
            "type_order": type_order,
            "type_post": type_post,
            "time_range": time_range,
            "search": search,
            "member_type": member_type,
        }
        users = UserService.admin_search_users(data_search)
        return {
            "status": True,
            "message": "Success",
            "total": users.total,
            "page": users.page,
            "per_page": users.per_page,
            "total_pages": users.pages,
            "data": [post._to_json() for post in users.items],
        }, 200


@ns.route("/delete_user")
class APIDeleteUser(Resource):
    @jwt_required()
    @admin_required()
    @parameters(
        type="object",
        properties={
            "user_ids": {"type": "string"},
        },
        required=["user_ids"],
    )
    def post(self, args):
        try:
            user_ids = args.get("user_ids", "")
            # Chuyển chuỗi user_ids thành list các integer
            if not user_ids:
                return Response(
                    message="No user_ids provided",
                    code=201,
                ).to_dict()

            # Tách chuỗi và convert sang list integer
            id_list = [int(id.strip()) for id in user_ids.split(",")]

            if not id_list:
                return Response(
                    message="Invalid user_ids format",
                    code=201,
                ).to_dict()

            process_delete = UserService.delete_users_by_ids(id_list)
            if process_delete == 1:
                message = "Delete user Success"
            else:
                message = "사용자 삭제 중 오류"
                return Response(
                    message=message,
                    code=201,
                ).to_dict()

            return Response(message=message, code=200, data=id_list).to_dict()

        except Exception as e:
            logger.error(f"Exception: Delete user Fail  :  {str(e)}")
            return Response(
                message="사용자 삭제 중 오류",
                code=201,
            ).to_dict()


@ns.route("/socialposts")
class APISocialPost(Resource):

    @jwt_required()
    @admin_required()
    def get(self):

        filters = request.args.to_dict()  # Convert query string to dict
        data = SocialPostService.getTotalRunning(filters)

        return Response(message="", code=200, data=data).to_dict()
