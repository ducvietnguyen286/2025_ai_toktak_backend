# coding: utf8
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.decorators import parameters
from app.lib.response import Response
from app.scraper import Scraper
from app.services.auth import AuthService

ns = Namespace(name="crawler", description="User API")


@ns.route("/shopee")
class APICrawlingShopee(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "url": {"type": "string"},
        },
        required=["url"],
    )
    def post(self, args):
        current_user = AuthService.get_current_identity()
        if not current_user:
            return Response(
                message="Không tìm thấy người dùng",
                status=400,
            ).to_dict()
        if current_user.id != 1:
            return Response(
                message="Không có quyền truy cập",
                status=403,
            ).to_dict()

        url = args.get("url", "")
        if not url:
            return Response(
                message="URL không hợp lệ",
                status=400,
            ).to_dict()
        data = Scraper().scraper({"url": url})
        return Response(
            data=data,
            message="Đăng nhập thành công",
        ).to_dict()
