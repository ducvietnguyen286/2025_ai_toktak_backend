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
    def get_groups_with_products(user_id, product_limit=20, cache_timeout=86400):
        cache_key = f"group_products:{user_id}:{product_limit}"
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        groups = (
            GroupProduct.query.filter_by(user_id=user_id)
            .order_by(GroupProduct.order_no)
            .all()
        )
        group_list = []
        for group in groups:
            products = (
                Product.query.filter_by(group_id=group.id)
                .order_by(Product.order_no)
                .limit(product_limit)
                .all()
            )
            total_products = Product.query.filter_by(group_id=group.id).count()
            group_list.append(
                {
                    "group": group.to_dict(),
                    "products": [p.to_dict() for p in products],
                    "total_products": total_products,
                }
            )

        redis_client.setex(
            cache_key, cache_timeout, json.dumps(group_list, ensure_ascii=False)
        )
        return group_list
