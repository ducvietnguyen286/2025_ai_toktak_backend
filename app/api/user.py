# coding: utf8
import json
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.decorators import parameters
from app.lib.response import Response

from app.services.auth import AuthService
from app.services.user import UserService
from app.services.link import LinkService

ns = Namespace(name="user", description="User API")


@ns.route("/links")
class APIUserLinks(Resource):

    @jwt_required()
    def get(self):
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

        user_link = UserService.create_user_link(
            user_id=current_user.id, link_id=link_id, meta=json.dumps(info), status=1
        )
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
            "link_ids": {"type": "array"},
            "post_id": {"type": "integer"},
            "content": {"type": "string"},
        },
        required=["post_id"],
    )
    def post(self, args):
        current_user = AuthService.get_current_identity()
        is_all = args.get("is_all", 0)
        post_id = args.get("is_all", 0)
        link_ids = args.get("link_ids", [])
        content = args.get("content", "")

        if not link_ids:
            return Response(
                message="Không tìm thấy link",
                status=400,
            ).to_dict()

        if not content:
            return Response(
                message="Không tìm thấy nội dung",
                status=400,
            ).to_dict()

        for link_id in link_ids:
            user_link = UserService.find_user_link(link_id, current_user.id)
            if not user_link:
                return Response(
                    message="Không tìm thấy link",
                    status=400,
                ).to_dict()

            if user_link.status == 0:
                return Response(
                    message="Link chưa được kích hoạt",
                    status=400,
                ).to_dict()

        return Response(
            message="Tạo bài viết thành công",
        ).to_dict()
