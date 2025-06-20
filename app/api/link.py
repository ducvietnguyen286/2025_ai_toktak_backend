# coding: utf8
import json
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.decorators import parameters
from app.lib.response import Response

from app.services.auth import AuthService
from app.services.link import LinkService

ns = Namespace(name="link", description="User API")


@ns.route("/list")
class APIListLink(Resource):

    @jwt_required()
    def get(self):
        links = LinkService.get_links()
        return Response(
            data=links,
            message="Đăng nhập thành công",
        ).to_dict()


@ns.route("/<int:id>")
class APIFindLink(Resource):

    @jwt_required()
    def get(self, id):
        link = LinkService.find_link(id)
        if not link:
            return Response(
                message="Không tìm thấy link",
                status=400,
            ).to_dict()

        return Response(
            data=link,
            message="Đăng nhập thành công",
        ).to_dict()


@ns.route("/create")
class APICreateLink(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "avatar": {"type": "string"},
            "title": {"type": "string"},
            "need_info": {"type": "object"},
            "type": {"type": "integer"},
        },
        required=["avatar", "title", "need_info", "type"],
    )
    def post(self, args):
        user_id = AuthService.get_user_id()
        avatar = args.get("avatar", "")
        title = args.get("title", "")
        need_info = args.get("need_info", {})
        type = args.get("type", 0)
        link = LinkService.create_link(avatar, title, need_info, type, user_id)
        return Response(
            data=link,
            message="Tạo link thành công",
        ).to_dict()


@ns.route("/update/<int:id>")
class APIUpdateLink(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "avatar": {"type": "string"},
            "title": {"type": "string"},
            "need_info": {"type": "object"},
            "type": {"type": "integer"},
        },
        required=[],
    )
    def put(self, args):
        link = LinkService.update_link(id, *args)
        return Response(
            data=link,
            message="Tạo link thành công",
        ).to_dict()
