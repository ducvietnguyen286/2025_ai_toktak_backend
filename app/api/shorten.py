import random
import string
import hashlib
import base64
from flask import request, redirect
from flask_restx import Namespace, Resource, fields
from app.extensions import redis_client
from app.models.shorten import ShortenURL
from app.services.shorten_services import ShortenServices

from app.lib.logger import logger
from app.lib.response import Response

ns = Namespace("shorten", description="URL Shortener API")

# Schema cho Request
shorten_model = ns.model(
    "ShortenURL",
    {
        "original_url": fields.String(
            required=True, description="Original URL to shorten"
        )
    },
)


def generate_short_code(url):
    """Tạo mã rút gọn bằng Base62 từ hash của URL"""
    hash_value = hashlib.md5(url.encode()).digest()
    short_code = base64.urlsafe_b64encode(hash_value)[:6].decode("utf-8")
    return short_code


@ns.route("/create")
class APICreateShortenURL(Resource):
    @ns.expect(shorten_model)
    def post(self):
        """Tạo một URL rút gọn"""

        try:
            domain_share_url = "https://s.toktak.ai/"
            data = request.json
            original_url = data.get("original_url")

            # Kiểm tra nếu URL đã tồn tại trong DB
            existing_entry = ShortenURL.query.filter_by(
                original_url=original_url
            ).first()

            logger.error(existing_entry)
            if not existing_entry:
                # Tạo short_code ngẫu nhiên và đảm bảo nó là duy nhất
                short_code = generate_short_code(original_url)
                while ShortenURL.query.filter_by(short_code=short_code).first():
                    short_code = generate_short_code(original_url)

                # Lưu vào Database
                ShortenServices.create_shorten(
                    original_url=original_url, short_code=short_code
                )

                # Lưu vào Redis Cache
                redis_client.set(
                    short_code, original_url, ex=86400
                )  # Cache trong 24 giờ

            return Response(
                message="URL을 잘못 입력했습니다.",
                data={
                    "original_url": existing_entry.original_url,
                    "short_url": f"{domain_share_url}{existing_entry.short_code}",
                    "short_code": existing_entry.short_code,
                },
                status=200,
            ).to_dict()

        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return Response(
                message="An error occurred while processing the request.",
                data={},
                status=500,
            ).to_dict()


@ns.route("/<string:short_code>")
class ApiRedirectURLShorten(Resource):
    def get(self, short_code):
        """Redirect đến URL gốc"""
        # Kiểm tra trong Redis cache trước
        original_url = redis_client.get(short_code)
        if original_url:
            return redirect(original_url.decode("utf-8"))

        # Nếu không có trong cache, kiểm tra DB
        url_entry = ShortenURL.query.filter_by(short_code=short_code).first()
        if url_entry:
            redis_client.set(short_code, url_entry.original_url, ex=86400)  # Cache lại
            return redirect(url_entry.original_url)

        return {"message": "Shortened URL not found"}, 404
