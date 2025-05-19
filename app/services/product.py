from app.models.user import User
from app.models.post import Post
from app.models.user_video_templates import UserVideoTemplates
from app.models.link import Link
from app.models.social_post import SocialPost
from app.models.product import Product
from app.extensions import db
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


class ProductService:

    @staticmethod
    def create_product(*args, **kwargs):
        product = Product(*args, **kwargs)
        product.save()
        return product

    @staticmethod
    def find_post(id):
        return Product.query.get(id)

    @staticmethod
    def update_product(id, *args, **kwargs):
        product_detail = Product.query.get(id)
        if not product_detail:
            return None
        product_detail.update(**kwargs)
        return product_detail

    @staticmethod
    def delete_product(id):
        return Product.query.get(id).delete()

    @staticmethod
    def get_products_by_user_id(user_id):
        products = Product.query.where(Post.user_id == user_id).all()
        return products

    @staticmethod
    def get_products(data_search):
        # Query cơ bản với các điều kiện
        query = Product.query

        search_key = data_search.get("search_key", "")

        if search_key != "":
            search_pattern = f"%{search_key}%"
            query = query.filter(
                or_(
                    Product.product_name.ilike(search_pattern),
                    Product.description.ilike(search_pattern),
                    Product.user.has(User.email.ilike(search_pattern)),
                )
            )

        if "user_id" in data_search and data_search["user_id"]:
            query = query.filter(Product.user_id == data_search["user_id"])

        # Xử lý type_order
        if data_search["type_order"] == "id_asc":
            query = query.order_by(Product.id.asc())
        elif data_search["type_order"] == "id_desc":
            query = query.order_by(Product.id.desc())
        else:
            query = query.order_by(Product.id.desc())

        time_range = data_search.get("time_range")
        if time_range == "today":
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            query = query.filter(Product.created_at >= start_date)

        elif time_range == "last_week":
            start_date = datetime.now() - timedelta(days=7)
            query = query.filter(Product.created_at >= start_date)

        elif time_range == "last_month":
            start_date = datetime.now() - timedelta(days=30)
            query = query.filter(Product.created_at >= start_date)

        elif time_range == "last_year":
            start_date = datetime.now() - timedelta(days=365)
            query = query.filter(Product.created_at >= start_date)

        pagination = query.paginate(
            page=data_search["page"], per_page=data_search["per_page"], error_out=False
        )
        return pagination

    @staticmethod
    def delete_posts_by_ids(post_ids):
        try:
            Product.query.filter(Product.id.in_(post_ids)).delete(
                synchronize_session=False
            )
            db.session.commit()
        except Exception as ex:
            db.session.rollback()
            return 0
        return 1

    @staticmethod
    def delete_product_by_user_id(product_ids, user_id):

        products_to_delete = Product.query.filter(
            and_(Product.id.in_(product_ids), Product.user_id == user_id)
        )

        # Đếm số lượng để biết có xóa gì không
        if products_to_delete.count() == 0:
            return False  # Không có sản phẩm để xóa

        # Thực hiện xóa
        products_to_delete.delete(synchronize_session=False)
        db.session.commit()
        return True

    @staticmethod
    def find_post_by_user_id(id, user_id):
        return Product.query.filter_by(id=id, user_id=user_id).first()

    @staticmethod
    def is_product_exist(user_id, product_url_hash):
        try:
            existing_product = Product.query.filter_by(
                user_id=user_id, product_url_hash=product_url_hash
            ).first()
            return existing_product is not None
        except Exception as ex:
            return None
        return None

    @staticmethod
    def create_sns_product(user_id, batch_id):
        try:
            batch_detail = BatchService.find_batch(batch_id)
            if not batch_detail:
                logger.error(
                    f"Can't create Product   user_id :  {str(user_id)} , batch_id : {batch_id}"
                )
                return
            product_url = batch_detail.url
            product_url_hash = hashlib.sha1(product_url.encode()).hexdigest()

            is_product_exist = ProductService.is_product_exist(
                user_id, product_url_hash
            )
            show_price = 1
            if not is_product_exist:
                profile = ProfileServices.profile_by_user_id(user_id)
                if profile:
                    try:
                        design_settings = json.loads(profile.design_settings)
                        if isinstance(design_settings, dict):
                            show_price = design_settings.get("show_price", 1)
                    except Exception as e:
                        show_price = 1

                data_content = json.loads(batch_detail.content)
                ProductService.create_product(
                    user_id=user_id,
                    product_name=data_content.get("name", ""),
                    description=data_content.get("description", ""),
                    shorten_link=data_content.get("shorten_link", ""),
                    price=data_content.get("price", "") if show_price == 1 else "",
                    product_url=batch_detail.url,
                    product_image=batch_detail.thumbnail,
                    product_url_hash=product_url_hash,
                    content=batch_detail.content,
                )
        except Exception as ex:
            logger.error(f"Exception: create_sns_product   :  {str(ex)}")
            return None
        return True
