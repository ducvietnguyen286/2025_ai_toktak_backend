# coding: utf8
import json
from flask_restx import Namespace, Resource
from app.ais.chatgpt import call_chatgpt_create_caption
from app.decorators import parameters
from app.lib.response import Response
from app.scraper import Scraper
import traceback

ns = Namespace(name="maker", description="Maker API")


@ns.route("/make-videos")
class APIMaker(Resource):

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
            images = data.get("images", [])
            caption = {}
            if images:
                response = call_chatgpt_create_caption(images)
                if response:
                    parse_caption = json.loads(response)
                    caption = parse_caption.get("response", {})
            return Response(
                data=caption,
                message="Dịch thuật thành công",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            return Response(
                message="Dịch thuật thất bại",
                status=400,
            ).to_dict()
