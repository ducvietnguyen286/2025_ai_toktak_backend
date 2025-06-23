# coding: utf8
import os
from flask_jwt_extended import get_jwt_identity, jwt_required
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
from app.services.group_product_services import GroupProductService
from app.extensions import db, redis_client

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
            from_date = request.args.get("from_date", "", type=str)
            to_date = request.args.get("to_date", "", type=str)
            group_id = request.args.get("group_id", 0, type=int)
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
                "from_date": from_date,
                "to_date": to_date,
                "group_id": group_id,
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
            subject = get_jwt_identity()
            if subject is None:
                return None

            user_id = int(subject)
            product_name = args.get("product_name", "")
            product_url = args.get("product_url", "")
            product_image = args.get("product_image", "")
            price = args.get("price", "")

            product_url_hash = hashlib.sha1(product_url.encode()).hexdigest()

            product_detail = ProductService.create_product(
                user_id=user_id,
                product_name=product_name,
                product_url=product_url,
                product_image=product_image,
                price=price,
                description="",
                product_url_hash=product_url_hash,
                content=json.dumps([]),
            )
            GroupProductService.delete_group_products_cache(user_id)
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


@ns.route("/multi_product_create")
class MultiProductCreateApi(Resource):
    @jwt_required()
    def post(self):
        try:
            user_id = AuthService.get_user_id()
            products = []
            idx = 0
            today = datetime.now()
            while True:
                prefix = f"[{idx}]"
                if f"{prefix}[id]" not in request.form:
                    break  # Dừng nếu hết sản phẩm
                prod = {
                    "id": request.form.get(f"{prefix}[id]"),
                    "product_name": request.form.get(f"{prefix}[product_name]", ""),
                    "product_url": request.form.get(f"{prefix}[product_url]", ""),
                    "price": request.form.get(f"{prefix}[price]", ""),
                    "order_no": request.form.get(f"{prefix}[order_no]", 0),
                }

                # Nhận file nếu có
                file = request.files.get(f"{prefix}[product_file]")
                if file:
                    # Lưu file lên server, đổi tên nếu cần
                    folder_path = f"static/voice/product_upload/{today.strftime('%Y_%m_%d')}/{user_id}"
                    os.makedirs(folder_path, exist_ok=True)
                    filename = file.filename
                    save_path = os.path.join(folder_path, filename)
                    file.save(save_path)
                    prod["product_image"] = save_path

                else:
                    prod["product_image"] = request.form.get(
                        f"{prefix}[product_image]", ""
                    )

                products.append(prod)
                idx += 1

            created_products = []
            for item in products:
                product_url = item.get("product_url", "")
                product_name = item.get("product_name", "")
                product_image = item.get("product_image", "")
                price = item.get("price", "")
                order_no = item.get("order_no", 0)

                product_url_hash = hashlib.sha1(product_url.encode()).hexdigest()

                is_product_exist = ProductService.is_product_exist(
                    user_id, product_url_hash
                )
                if not is_product_exist:
                    product_detail = ProductService.create_product(
                        user_id=user_id,
                        product_name=product_name,
                        product_url=product_url,
                        product_image=product_image,
                        price=price,
                        description="",
                        group_id=0,
                        order_no=0,
                        product_url_hash=product_url_hash,
                        content=json.dumps([]),
                    )

                    if product_detail:
                        created_products.append(product_detail.to_dict())

            if not created_products:
                return Response(message="제품 생성에 실패했습니다.", code=201).to_dict()

            GroupProductService.delete_group_products_cache(user_id)

            return Response(
                data=created_products,
                message="모든 제품이 성공적으로 추가되었습니다.",
            ).to_dict()

        except Exception as e:
            logger.error(f"Create multiple products error: {str(e)}")
            return Response(
                message="제품 추가 중 오류가 발생했습니다.", code=201
            ).to_dict()


@ns.route("/product_update_multi")
class ProductMultiUpdateAPI(Resource):
    @jwt_required()
    def post(self):
        try:
            user_id = AuthService.get_user_id()
            products = []
            idx = 0
            today = datetime.now()
            while True:
                prefix = f"[{idx}]"
                if f"{prefix}[id]" not in request.form:
                    break  # Dừng nếu hết sản phẩm
                prod = {
                    "id": request.form.get(f"{prefix}[id]"),
                    "product_name": request.form.get(f"{prefix}[product_name]", ""),
                    "product_url": request.form.get(f"{prefix}[product_url]", ""),
                    "price": request.form.get(f"{prefix}[price]", ""),
                    "order_no": request.form.get(f"{prefix}[order_no]", 0),
                    "group_id": request.form.get(f"{prefix}[group_id]", 0),
                }

                # Nhận file nếu có
                file = request.files.get(f"{prefix}[product_file]")
                if file:
                    # Lưu file lên server, đổi tên nếu cần
                    folder_path = f"static/voice/product_upload/{today.strftime('%Y_%m_%d')}/{user_id}"
                    os.makedirs(folder_path, exist_ok=True)
                    filename = file.filename
                    save_path = os.path.join(folder_path, filename)
                    file.save(save_path)
                    prod["product_image"] = save_path

                else:
                    prod["product_image"] = request.form.get(
                        f"{prefix}[product_image]", ""
                    )

                products.append(prod)
                idx += 1

            for prod in products:
                product_id = prod.get("id", "")
                product_detail = ProductService.find_post_by_user_id(
                    product_id, user_id
                )
                if product_detail:
                    product_url = prod.get("product_url", "")
                    product_name = prod.get("product_name", "")
                    product_image = prod.get("product_image", "")
                    order_no = prod.get("order_no", 0)
                    price = prod.get("price", "")
                    group_id = prod.get("group_id", 0)
                    data_update = {
                        "product_url": product_url,
                        "product_name": product_name,
                        "product_image": product_image,
                        "order_no": order_no,
                        "group_id": group_id,
                        "price": price,
                    }
                    product_detail = ProductService.update_product(
                        product_id, **data_update
                    )

            GroupProductService.delete_group_products_cache(user_id)
            return Response(
                message="제품 정보가 성공적으로 업데이트되었습니다.",
            ).to_dict()

        except Exception as e:
            logger.error(f"Update product  error: {str(e)}")
            return Response(
                message="제품 정보 업데이트에 실패했습니다.", code=201
            ).to_dict()


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
            user_id = AuthService.get_user_id()
            product_id = args.get("product_id", "")
            product_detail = ProductService.find_post_by_user_id(product_id, user_id)
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

            GroupProductService.delete_group_products_cache(user_id)
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
        required=[],
    )
    def post(self, args):
        try:
            user_id = AuthService.get_user_id()
            product_ids = args.get("product_ids", "")
            id_list = [int(id.strip()) for id in product_ids.split(",") if id.strip()]

            if not id_list:
                return Response(
                    message="Invalid product_ids format",
                    code=201,
                ).to_dict()

            product_update = ProductService.delete_product_by_user_id(id_list, user_id)
            if not product_update:
                return Response(
                    message="상품을 삭제하지 못했습니다.", code=201
                ).to_dict()

            GroupProductService.delete_group_products_cache(user_id)
            return Response(
                data={},
                message="상품을 성공적으로 삭제했습니다.",
            ).to_dict()

        except Exception as e:
            logger.error(f"delete product  error: {str(e)}")
            return Response(message="상품을 삭제하지 못했습니다.", code=201).to_dict()


@ns.route("/group_create")
class GroupCreateApi(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "group_name": {"type": "string"},
            "order_no": {"type": "integer"},
        },
        required=["group_name"],
    )
    def post(self, args):
        try:
            user_id = AuthService.get_user_id()
            group_name = args.get("group_name")
            order_no = args.get("order_no", 0)

            group = GroupProductService.create_group_product(
                user_id=user_id,
                name=group_name,
                order_no=order_no,
            )
            if not group:
                return Response(
                    message="그룹 생성에 실패했습니다.",
                    message_en="Failed to create group.",
                    code=500,
                ).to_dict()

            GroupProductService.delete_group_products_cache(user_id)
            return Response(
                data=group.to_dict(),
                message="그룹이 성공적으로 생성되었습니다.",
                message_en="Group created successfully.",
                code=200,
            ).to_dict()
        except Exception as e:
            logger.error(f"Create group error: {str(e)}")
            return Response(
                message="그룹 생성 중 오류가 발생했습니다.",
                message_en="An error occurred while creating the group.",
                code=500,
            ).to_dict()


@ns.route("/group_update_detail/<int:group_id>")
class GroupUpdateApi(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "group_name": {"type": "string"},
            "order_no": {"type": "integer"},
        },
        required=[],
    )
    def put(self, args, group_id):
        try:
            user_id = AuthService.get_user_id()
            group_name = args.get("group_name")
            order_no = args.get("order_no")

            group = GroupProductService.update_group_product(
                group_id,
                name=group_name,
                order_no=order_no,
            )
            if not group:
                return Response(
                    message="그룹을 찾을 수 없습니다.",
                    message_en="Group not found.",
                    code=404,
                ).to_dict()

            return Response(
                data=group.to_dict(),
                message="그룹이 성공적으로 수정되었습니다.",
                message_en="Group updated successfully.",
                code=200,
            ).to_dict()
        except Exception as e:
            logger.error(f"Update group error: {str(e)}")
            return Response(
                message="그룹 수정 중 오류가 발생했습니다.",
                message_en="An error occurred while updating the group.",
                code=500,
            ).to_dict()


@ns.route("/group_delete/<int:group_id>")
class GroupDeleteApi(Resource):
    @jwt_required()
    def delete(self, group_id):
        try:
            user_id = AuthService.get_user_id()

            success = GroupProductService.delete_group_product(group_id)
            GroupProductService.delete_group_products_cache(user_id)
            if not success:
                return Response(
                    message="그룹을 찾을 수 없습니다.",
                    message_en="Group not found.",
                    code=404,
                ).to_dict()

            return Response(
                message="그룹이 성공적으로 삭제되었습니다.",
                message_en="Group deleted successfully.",
                code=200,
            ).to_dict()
        except Exception as e:
            logger.error(f"Delete group error: {str(e)}")
            return Response(
                message="그룹 삭제 중 오류가 발생했습니다.",
                message_en="An error occurred while deleting the group.",
                code=500,
            ).to_dict()


@ns.route("/group_list")
class GroupListApi(Resource):
    @jwt_required()
    def get(self):
        try:
            user_id = AuthService.get_user_id()
            groups = GroupProductService.get_groups_by_user_id(user_id)
            return Response(
                data=[g.to_dict() for g in groups],
                message="그룹 리스트를 성공적으로 불러왔습니다.",
                message_en="Group list loaded successfully.",
                code=200,
            ).to_dict()
        except Exception as e:
            logger.error(f"List group error: {str(e)}")
            return Response(
                message="그룹 리스트 불러오기 중 오류가 발생했습니다.",
                message_en="An error occurred while loading group list.",
                code=500,
            ).to_dict()


@ns.route("/user_group_products")
class GroupListWithProductsApi(Resource):
    def get(self):
        try:
            search_key = request.args.get("search_key", "", type=str)
            user_id = request.args.get("user_id", "", type=str)
            try:
                product_limit = int(request.args.get("per_page", 20))
                if product_limit < 1:
                    product_limit = 20
            except Exception:
                product_limit = 20

            data = GroupProductService.get_groups_with_products(
                user_id=user_id,
                product_limit=product_limit,
                search_key=search_key,
                cache_timeout=60,
            )
            return Response(
                data=data,
                message="그룹 및 제품 리스트를 성공적으로 불러왔습니다.",
                message_en="Groups and products list loaded successfully.",
                code=200,
            ).to_dict()
        except Exception as e:
            logger.error(f"Group list with products error: {str(e)}")
            return Response(
                message="그룹 및 제품 리스트 불러오기 중 오류가 발생했습니다.",
                message_en="An error occurred while loading groups and products.",
                code=500,
            ).to_dict()


@ns.route("/multi_group_create")
class MultiGroupCreateApi(Resource):
    @jwt_required()
    def post(self):
        try:
            user_id = AuthService.get_user_id()

            data = request.get_json()
            groups = data.get("products", [])
            result = {"groups": [], "products": []}

            for group_data in groups:
                # Lưu hoặc update group
                group = GroupProductService.upsert_group(group_data, user_id)
                result["groups"].append(group.to_dict())

                # Lưu các product con trong group
                order_no = 0
                for product_data in group_data.get("children", []):
                    prod = GroupProductService.upsert_product(
                        product_data, user_id, group.id
                    )
                    result["products"].append(prod.to_dict())

            db.session.commit()
            GroupProductService.delete_group_products_cache(user_id)
            return Response(
                data=result,
                message="그룹과 상품이 성공적으로 저장되었습니다.",
                message_en="Groups and products saved successfully.",
                code=200,
            ).to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Create group error: {str(e)}")
            return Response(
                message="저장 중 오류가 발생했습니다.",
                message_en="An error occurred while saving data.",
                code=500,
            ).to_dict()

    @ns.route("/group_delete")
    class GroupDeleteApi(Resource):
        @jwt_required()
        def post(self):
            try:
                data = request.get_json() or {}
                ids_raw = data.get("group_ids", "")  # "1,2,3" hoặc [1,2,3]
                user_id = AuthService.get_user_id()

                # Chuẩn hóa list group_id
                if isinstance(ids_raw, str):
                    group_ids = [
                        int(i.strip()) for i in ids_raw.split(",") if i.strip()
                    ]
                elif isinstance(ids_raw, list):
                    group_ids = [int(i) for i in ids_raw if str(i).strip()]
                else:
                    return Response(
                        message="ids 형식이 잘못되었습니다.",
                        message_en="Invalid ids format.",
                        code=400,
                    ).to_dict()

                # Gọi service
                try:
                    GroupProductService.delete_groups_and_products(group_ids, user_id)
                    GroupProductService.delete_group_products_cache(user_id)
                except Exception as e:
                    logger.error(f"Error deleting groups: {str(e)}")
                    return Response(
                        message="그룹 삭제 중 오류가 발생했습니다.",
                        message_en="An error occurred while deleting groups.",
                        code=500,
                    ).to_dict()

                return Response(
                    message="그룹과 해당 상품이 성공적으로 삭제되었습니다.",
                    message_en="Groups and their products deleted successfully.",
                    code=200,
                ).to_dict()
            except Exception as e:
                logger.error(f"Group delete API error: {str(e)}")
                return Response(
                    message="요청 처리 중 오류가 발생했습니다.",
                    message_en="An error occurred while processing the request.",
                    code=500,
                ).to_dict()

    @ns.route("/group_update")
    class MultiGroupUpdateApi(Resource):
        @jwt_required()
        def post(self):
            try:
                user_id = AuthService.get_user_id()

                data = request.get_json()
                groups = data.get("products", [])
                result = {"groups": [], "products": []}

                for group_data in groups:
                    # Lưu hoặc update group
                    group = GroupProductService.upsert_group(group_data, user_id)
                    result["groups"].append(group.to_dict())

                    # Lưu các product con trong group
                    for product_data in group_data.get("children", []):
                        prod = GroupProductService.upsert_product(
                            product_data, user_id, group.id
                        )
                        result["products"].append(prod.to_dict())

                db.session.commit()
                GroupProductService.delete_group_products_cache(user_id)
                return Response(
                    data=result,
                    message="그룹과 상품이 성공적으로 저장되었습니다.",
                    message_en="Groups and products saved successfully.",
                    code=200,
                ).to_dict()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Create group error: {str(e)}")
                return Response(
                    message="저장 중 오류가 발생했습니다.",
                    message_en="An error occurred while saving data.",
                    code=500,
                ).to_dict()

    @ns.route("/group_delete")
    class GroupDeleteApi(Resource):
        @jwt_required()
        def post(self):
            try:
                data = request.get_json() or {}
                ids_raw = data.get("ids", "")  # "1,2,3" hoặc [1,2,3]
                user_id = AuthService.get_user_id()

                # Chuẩn hóa list group_id
                if isinstance(ids_raw, str):
                    group_ids = [
                        int(i.strip()) for i in ids_raw.split(",") if i.strip()
                    ]
                elif isinstance(ids_raw, list):
                    group_ids = [int(i) for i in ids_raw if str(i).strip()]
                else:
                    return Response(
                        message="ids 형식이 잘못되었습니다.",
                        message_en="Invalid ids format.",
                        code=400,
                    ).to_dict()

                # Gọi service
                try:
                    GroupProductService.delete_groups_and_products(group_ids, user_id)
                    GroupProductService.delete_group_products_cache(user_id)
                except Exception as e:
                    logger.error(f"Error deleting groups: {str(e)}")
                    return Response(
                        message="그룹 삭제 중 오류가 발생했습니다.",
                        message_en="An error occurred while deleting groups.",
                        code=500,
                    ).to_dict()

                return Response(
                    message="그룹과 해당 상품이 성공적으로 삭제되었습니다.",
                    message_en="Groups and their products deleted successfully.",
                    code=200,
                ).to_dict()
            except Exception as e:
                logger.error(f"Group delete API error: {str(e)}")
                return Response(
                    message="요청 처리 중 오류가 발생했습니다.",
                    message_en="An error occurred while processing the request.",
                    code=500,
                ).to_dict()
