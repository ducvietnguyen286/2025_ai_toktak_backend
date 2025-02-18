# coding: utf8
from flask_restx import Namespace, Resource
from app.decorators import parameters
from app.lib.response import Response
from app.scraper import Scraper
import traceback

ns = Namespace(name="auth", description="Auth API")


@ns.route("/login")
class APILogin(Resource):

    @parameters(
        type="object",
        properties={
            "url": {"type": "string"},
        },
        required=["url"],
    )
    def post(self, args):
        try:
            url = args.get("url", "")
            data = Scraper().scraper({"url": url})
            return Response(
                data=data,
                message="Dịch thuật thành công",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            return Response(
                message="Dịch thuật thất bại",
                status=400,
            ).to_dict()
