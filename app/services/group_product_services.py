from app.models.user import User
from app.models.post import Post
from app.models.user_video_templates import UserVideoTemplates
from app.models.link import Link
from app.models.social_post import SocialPost
from app.models.groups_product import GroupProduct
from app.extensions import db, redis_client
from sqlalchemy import and_, func, or_
from flask import jsonify
from datetime import datetime, timedelta
from sqlalchemy.orm import aliased
from app.services.batch import BatchService
from app.services.image_template import ImageTemplateService
import os
import json
import const
import hashlib
from app.models.batch import Batch
from app.lib.logger import logger
from app.services.profileservices import ProfileServices
from app.models.product import Product
from app.services.product import ProductService


class GroupProductService:

    @staticmethod
    def create_group_product(**kwargs):
        group = GroupProduct(**kwargs)
        group.save()
        return group

    @staticmethod
    def find_group_product(group_id):
        return GroupProduct.query.get(group_id)

    @staticmethod
    def update_group_product(group_id, **kwargs):
        group = GroupProduct.query.get(group_id)
        if not group:
            return None
        group.update(**kwargs)
        return group

    @staticmethod
    def delete_group_product(group_id):
        group = GroupProduct.query.get(group_id)
        if group:
            group.delete()
            return True
        return False

    @staticmethod
    def get_groups_by_user_id(user_id):
        return (
            GroupProduct.query.filter_by(user_id=user_id)
            .order_by(GroupProduct.order_no)
            .all()
        )

    @staticmethod
    def get_groups_with_products(
        user_id, product_limit=10, search_key="", cache_timeout=86400
    ):
        if search_key != "":
            cache_key = f"group_products:{user_id}:{product_limit}:{search_key}"
        else:
            cache_key = f"group_products:{user_id}:{product_limit}"
        redis_client.delete(cache_key)
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data.decode("utf-8"))

        groups = (
            GroupProduct.query.filter_by(user_id=user_id)
            .order_by(GroupProduct.order_no)
            .all()
        )
        group_list = []

        data_search = {
            "page": 1,
            "per_page": product_limit,
            "search_key": search_key,
            "user_id": user_id,
            "group_id": 0,
            "type_order": "order_no_asc",
        }

        ungroupped_products = ProductService.get_products(data_search)

        total_ungroupped = ungroupped_products.total
        group_list.append(
            {
                "group": {
                    "id": 0,
                    "user_id": user_id,
                    "name": "",
                    "order_no": 0,
                    "description": "",
                },
                "products": [
                    product_detail.to_dict()
                    for product_detail in ungroupped_products.items
                ],
                "total_products": total_ungroupped,
            }
        )
        # Lấy group thật từ DB
        for group in groups:
            data_search = {
                "page": 1,
                "per_page": product_limit,
                "search_key": search_key,
                "user_id": user_id,
                "group_id": group.id,
                "type_order": "order_no_asc",
            }
            products = ProductService.get_products(data_search)

            total_products = products.total
            group_list.append(
                {
                    "group": group.to_dict(),
                    "products": [
                        product_detail.to_dict()
                        for product_detail in ungroupped_products.items
                    ],
                    "total_products": total_products,
                }
            )
        redis_client.setex(
            cache_key, cache_timeout, json.dumps(group_list, ensure_ascii=False)
        )
        return group_list

    @staticmethod
    def upsert_group(group_data, user_id):
        group_id = group_data["id"]
        is_new = isinstance(group_id, str) and "group-" in group_id
        group = None
        if not is_new:
            group = GroupProduct.query.filter_by(id=group_id, user_id=user_id).first()

        if group:
            group.name = group_data.get("title", group.name)
            group.order_no = group_data.get("order_no", group.order_no or 0)
            group.description = group_data.get("description", group.description or "")
            group.title_type = group_data.get("titleType", group.title_type or "")
            return group
        else:
            group = GroupProduct(
                user_id=user_id,
                name=group_data.get("title", ""),
                order_no=group_data.get("order_no", 0),
                description=group_data.get("description", ""),
                title_type=group_data.get("titleType", "right"),
            )
            db.session.add(group)
            db.session.flush()
            return group

    @staticmethod
    def upsert_product(product_data, user_id, group_id):
        product_info = product_data.get("product", {})
        prod_id = product_info.get("id", "")
        is_new = isinstance(prod_id, str) and "temp" in prod_id
        product = None
        if not is_new:
            product = Product.query.filter_by(id=prod_id, user_id=user_id).first()
        if product:
            product.product_name = product_info.get(
                "product_name", product.product_name
            )
            product.price = product_info.get("price", product.price)
            product.product_image = product_info.get(
                "product_image", product.product_image
            )
            product.product_url = product_info.get("product_url", product.product_url)
            product.group_id = group_id
            product.order_no = product_info.get("order_no", product.order_no or 0)
            return product
        else:
            product_url = product_info.get("product_url", "")
            product_url_hash = hashlib.sha1(product_url.encode()).hexdigest()

            product = Product(
                user_id=user_id,
                product_url_hash=product_url_hash,
                product_name=product_info.get("product_name", ""),
                price=product_info.get("price", ""),
                product_image=product_info.get("product_image", ""),
                product_url=product_info.get("product_url", ""),
                group_id=group_id,
                order_no=product_info.get("order_no", 0),
            )
            db.session.add(product)
            return product

    @staticmethod
    def delete_groups_and_products(group_ids, user_id):
        try:
            # Product.query.filter(
            #     Product.group_id.in_(group_ids), Product.user_id == user_id
            # ).update({Product.group_id: 0}, synchronize_session=False)
            Product.query.filter(
                Product.group_id.in_(group_ids), Product.user_id == user_id
            ).delete(synchronize_session=False)

            GroupProduct.query.filter(
                GroupProduct.id.in_(group_ids), GroupProduct.user_id == user_id
            ).delete(synchronize_session=False)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False

    @staticmethod
    def delete_group_products_cache(user_id):
        pattern = f"group_products:{user_id}:*"
        for key in redis_client.scan_iter(match=pattern):
            redis_client.delete(key)
