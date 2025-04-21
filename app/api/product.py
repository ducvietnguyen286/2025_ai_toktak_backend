# coding: utf8
import os
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

from app.services.product import ProductService

ns = Namespace(name="product", description="Member profile operations")

UPLOAD_FOLDER = "static/voice/products"


@ns.route("/user_products")
class UserProductApi(Resource):
    def get(self):
        try:
            page = request.args.get("page", const.DEFAULT_PAGE, type=int)
            per_page = request.args.get("per_page", const.DEFAULT_PER_PAGE, type=int)
            status = request.args.get("status", const.UPLOADED, type=int)
            type_order = request.args.get("type_order", "", type=str)
            type_post = request.args.get("type_post", "", type=str)
            time_range = request.args.get("time_range", "", type=str)
            type_notification = request.args.get("type_notification", "", type=str)
            search_key = request.args.get("search_key", "", type=str)
            user_id = request.args.get("user_id", "", type=str)
            data_search = {
                "page": page,
                "per_page": per_page,
                "status": status,
                "type_order": type_order,
                "type_post": type_post,
                "time_range": time_range,
                "type_notification": type_notification,
                "search_key": search_key,
                "user_id": user_id,
            }
            products = ProductService.get_products(data_search)
            return {
                "status": True,
                "message": "Success",
                "total": products.total,
                "page": products.page,
                "per_page": products.per_page,
                "total_pages": products.pages,
                "data": [post.to_dict() for post in products.items],
            }, 200
        except Exception as e:
            logger.error(
                f"Exception: 제품을 검색하는 중 오류가 발생했습니다.  :  {str(e)}"
            )
            return Response(
                message="제품을 검색하는 중 오류가 발생했습니다.",
                code=201,
            ).to_dict()


@ns.route("/product_create")
class ProductCreateApi(Resource):
    @jwt_required()
    def post(self):
        try:
            current_user = AuthService.get_current_identity()
            form = request.form
            file = request.files.get("product_image")

            product_image_path = ""

            current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
            if file:
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                filename = f"{current_user.id}_product_{int(datetime.utcnow().timestamp())}_{file.filename}"
                path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(path)
                output_caption_file = path.replace("static/", "").replace("\\", "/")
                product_image_path = f"{current_domain}/{output_caption_file}"

            product_detail = ProductService.create_product(
                user_id=current_user.id,
                product_name=form.get("product_name"),
                description=form.get("description"),
                price=form.get("price"),
                product_image=product_image_path,
                content=json.dumps([]),
            )
            if not product_detail:
                return Response(
                    message="프로필이 존재하지 않습니다", code=201
                ).to_dict()

            return Response(
                data=product_detail.to_dict(),
                message="제품이 성공적으로 추가되었습니다.",
            ).to_dict()

        except Exception as e:
            logger.error(f"Create product error: {str(e)}")
            return Response(message="제품 추가에 실패했습니다.", code=201).to_dict()


@ns.route("/product_update")
class ProductUpdateAPI(Resource):
    @jwt_required()
    def post(self):
        try:
            current_user = AuthService.get_current_identity()
            form = request.form
            file = request.files.get("product_image")
            product_id = form.get("product_id")

            # Lấy dữ liệu text fields
            data_update = {
                "product_name": form.get("product_name"),
                "description": form.get("description"),
                "price": form.get("price"),
            }

            current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
            # Nếu có file ảnh => lưu ảnh
            if file:
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                filename = f"{current_user.id}_product_{int(datetime.utcnow().timestamp())}_{file.filename}"
                path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(path)
                output_caption_file = path.replace("static/", "").replace("\\", "/")
                product_image_path = f"{current_domain}/{output_caption_file}"

                data_update["product_image"] = product_image_path
            product_update = ProductService.update_product(product_id, **data_update)
            if not product_update:
                return Response(
                    message="제품 정보 업데이트에 실패했습니다.", code=201
                ).to_dict()

            return Response(
                data=product_update.to_dict(),
                message="제품 정보가 성공적으로 업데이트되었습니다.",
            ).to_dict()

        except Exception as e:
            logger.error(f"Update product  error: {str(e)}")
            return Response(
                message="제품 정보 업데이트에 실패했습니다.", code=201
            ).to_dict()
