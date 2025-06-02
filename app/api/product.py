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
import hashlib

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
    @parameters(
        type="object",
        properties={
            "product_url": {"type": "string"},
            "product_name": {"type": "string"},
            "product_image": {"type": "string"},
            "price": {"type": "string"},
        },
        required=["product_url", "product_name", "product_image", "price"],
    )
    def post(self, args):
        try:
            current_user = AuthService.get_current_identity()
            product_name = args.get("product_name", "")
            product_url = args.get("product_url", "")
            product_image = args.get("product_image", "")
            price = args.get("price", "")

            product_url_hash = hashlib.sha1(product_url.encode()).hexdigest()

            product_detail = ProductService.create_product(
                user_id=current_user.id,
                product_name=product_name,
                product_url=product_url,
                product_image=product_image,
                price=price,
                description="",
                product_url_hash=product_url_hash,
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
    @parameters(
        type="object",
        properties={
            "product_id": {"type": "integer"},
            "product_url": {"type": "string"},
            "product_name": {"type": "string"},
            "product_image": {"type": "string"},
            "price": {"type": "string"},
        },
        required=["product_url", "product_name", "product_image"],
    )
    def post(self, args):
        try:
            current_user = AuthService.get_current_identity()
            product_id = args.get("product_id", "")
            product_detail = ProductService.find_post_by_user_id(
                product_id, current_user.id
            )
            if product_detail:
                product_url = args.get("product_url", "")
                product_name = args.get("product_name", "")
                product_image = args.get("product_image", "")
                price = args.get("price", "")
                data_update = {
                    "product_url": product_url,
                    "product_name": product_name,
                    "product_image": product_image,
                    "price": price,
                }
                product_detail = ProductService.update_product(
                    product_id, **data_update
                )
            if not product_detail:
                return Response(
                    message="제품 정보 업데이트에 실패했습니다.", code=201
                ).to_dict()

            return Response(
                data=product_detail.to_dict(),
                message="제품 정보가 성공적으로 업데이트되었습니다.",
            ).to_dict()

        except Exception as e:
            logger.error(f"Update product  error: {str(e)}")
            return Response(
                message="제품 정보 업데이트에 실패했습니다.", code=201
            ).to_dict()


@ns.route("/product_delete")
class ProductDeleteAPI(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "product_ids": {"type": "string"},
        },
        required=["product_ids"],
    )
    def post(self, args):
        try:
            current_user = AuthService.get_current_identity()
            product_ids = args.get("product_ids", "")
            id_list = [int(id.strip()) for id in product_ids.split(",")]

            if not id_list:
                return Response(
                    message="Invalid product_ids format",
                    code=201,
                ).to_dict()

            product_update = ProductService.delete_product_by_user_id(
                id_list, current_user.id
            )
            if not product_update:
                return Response(
                    message="상품을 삭제하지 못했습니다.", code=201
                ).to_dict()

            return Response(
                data={},
                message="상품을 성공적으로 삭제했습니다.",
            ).to_dict()

        except Exception as e:
            logger.error(f"delete product  error: {str(e)}")
            return Response(message="상품을 삭제하지 못했습니다.", code=201).to_dict()


@ns.route("/multi_product_create")
class MultiProductCreateApi(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "products": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "product_url": {"type": "string"},
                        "product_name": {"type": "string"},
                        "product_image": {"type": "string"},
                        "price": {"type": "string"},
                    },
                    "required": [
                        "product_url",
                        "product_name",
                        "product_image",
                        "price",
                    ],
                },
            }
        },
        required=["products"],
    )
    def post(self, args):
        try:
            current_user = AuthService.get_current_identity()
            products = args.get("products", [])

            created_products = []

            for item in products:
                product_url = item.get("product_url", "")
                product_name = item.get("product_name", "")
                product_image = item.get("product_image", "")
                price = item.get("price", "")

                product_url_hash = hashlib.sha1(product_url.encode()).hexdigest()

                is_product_exist = ProductService.is_product_exist(
                    current_user.id, product_url_hash
                )
                if not is_product_exist:
                    product_detail = ProductService.create_product(
                        user_id=current_user.id,
                        product_name=product_name,
                        product_url=product_url,
                        product_image=product_image,
                        price=price,
                        description="",
                        product_url_hash=product_url_hash,
                        content=json.dumps([]),
                    )

                    if product_detail:
                        created_products.append(product_detail.to_dict())

            if not created_products:
                return Response(message="제품 생성에 실패했습니다.", code=201).to_dict()

            return Response(
                data=created_products,
                message="모든 제품이 성공적으로 추가되었습니다.",
            ).to_dict()

        except Exception as e:
            logger.error(f"Create multiple products error: {str(e)}")
            return Response(
                message="제품 추가 중 오류가 발생했습니다.", code=201
            ).to_dict()
