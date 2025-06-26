from app.models.notification import Notification
from app.models.user import User
from datetime import datetime, timedelta
from app.services.user import UserService
import const
import requests
import os
from app.lib.logger import logger
from app.lib.query import (
    delete_by_id,
    select_with_filter,
    select_by_id,
    select_with_pagination,
    select_with_filter_one,
    update_by_id,
)
from sqlalchemy import asc, desc, or_, update, delete
from sqlalchemy.orm import joinedload
from app.extensions import db


class NotificationServices:

    @staticmethod
    def create_notification(*args, **kwargs):
        notification = Notification(*args, **kwargs)
        notification.save()
        user_details = UserService.find_user_by_redis(kwargs.get("user_id"))
        if not user_details:
            return {"error": "user_not_found", "message": "User not found"}
        try:
            kwargs["email"] = user_details["email"]
            kwargs["name"] = user_details["name"]
            kwargs["notification_id"] = notification.id

            NOTIFICATION_API_URL = os.getenv("NOTIFICATION_API_BASE_URL")
            requests.post(
                f"{NOTIFICATION_API_URL}/notification/create-notification", json=kwargs
            )
        except Exception as e:
            logger.error(str(e))
        # notification = Notification(*args, **kwargs)
        # notification.save()
        return notification

    @staticmethod
    def find(id):
        return select_by_id(Notification, id)

    @staticmethod
    def update_notification(id, *args, **kwargs):
        try:
            api_kwargs = kwargs.copy()
            api_kwargs["notification_id"] = id
            NOTIFICATION_API_URL = os.getenv("NOTIFICATION_API_BASE_URL")
            requests.post(
                f"{NOTIFICATION_API_URL}/notification/update-notification-by-notification-id",
                json=api_kwargs,
            )
        except Exception as e:
            logger.error(str(e))

        return update_by_id(Notification, id, kwargs)

    @staticmethod
    def find_notification_sns(post_id, notification_type):
        return select_with_filter_one(
            Notification,
            filters=[
                Notification.post_id == post_id,
                Notification.notification_type == notification_type,
            ],
        )

    @staticmethod
    def delete(id):
        delete_by_id(Notification, id)
        return True

    @staticmethod
    def update_notification_by_batch_id(batch_id, *args, **kwargs):
        stmt = (
            update(Notification)
            .where(Notification.batch_id == batch_id)
            .values(**kwargs)
        )
        db.session.execute(stmt)
        db.session.commit()
        return True

    @staticmethod
    def get_notifications(data_search):
        filters = [Notification.user_id == data_search["user_id"]]

        tp = data_search.get("type_post")
        if tp in ("video", "image", "blog"):
            filters.append(Notification.notification_type == tp)

        tr = data_search.get("time_range")
        if tr:
            now = datetime.utcnow()
            if tr == "today":
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif tr == "last_week":
                start = now - timedelta(days=7)
            elif tr == "last_month":
                start = now - timedelta(days=30)
            elif tr == "last_year":
                start = now - timedelta(days=365)
            else:
                start = None

            if start:
                filters.append(Notification.created_at >= start)

        order = data_search.get("type_order", "id_desc")
        order_by = (
            [asc(Notification.id)] if order == "id_asc" else [desc(Notification.id)]
        )

        return select_with_pagination(
            Notification,
            page=max(int(data_search.get("page", 1)), 1),
            per_page=max(int(data_search.get("per_page", 10)), 1),
            filters=filters,
            order_by=order_by,
            eager_opts=[joinedload(Notification.user)],
        )

    @staticmethod
    def delete_posts_by_ids(post_ids):
        try:
            deleted = (
                db.session.query(Notification)
                .filter(Notification.id.in_(post_ids))
                .delete(synchronize_session=False)
            )
            db.session.commit()
            return deleted
        except Exception:
            return 0

    @staticmethod
    def getTotalNotification(data_search):
        query = db.session.query(Notification).filter_by(user_id=data_search["user_id"])
        typ = data_search.get("type_read")
        if typ == "0":
            query = query.filter_by(is_read=False)
        elif typ == "1":
            query = query.filter_by(is_read=True)
        return query.count()

    @staticmethod
    def update_post_by_user_id(user_id, *args, **kwargs):
        updated = (
            db.session.query(Notification).filter_by(user_id=user_id).update(kwargs)
        )
        db.session.commit()
        return updated

    @staticmethod
    def get_admin_notifications(data_search):
        # Query cơ bản với các điều kiện
        query = Notification.query
        type_notification = int(data_search.get("type_notification", ""))
        if type_notification == 0:
            query = query.filter(Notification.status == const.NOTIFICATION_FALSE)
        elif type_notification == 1:
            query = query.filter(Notification.status == const.NOTIFICATION_SUCCESS)

        search_key = data_search.get("search_key", "")

        if search_key != "":
            search_pattern = f"%{search_key}%"
            query = query.filter(
                or_(
                    Notification.title.ilike(search_pattern),
                    Notification.description.ilike(search_pattern),
                    Notification.user.has(User.email.ilike(search_pattern)),
                )
            )

        # Xử lý type_order
        if data_search["type_order"] == "id_asc":
            query = query.order_by(Notification.id.asc())
        elif data_search["type_order"] == "id_desc":
            query = query.order_by(Notification.id.desc())
        else:
            query = query.order_by(Notification.id.desc())

        # Xử lý type_post
        if data_search["type_post"] == "video":
            query = query.filter(Notification.type == "video")
        elif data_search["type_post"] == "image":
            query = query.filter(Notification.type == "image")
        elif data_search["type_post"] == "blog":
            query = query.filter(Notification.type == "blog")

        time_range = data_search.get("time_range")  # Thêm biến time_range
        # Lọc theo khoảng thời gian
        if time_range == "today":
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            query = query.filter(Notification.created_at >= start_date)

        elif time_range == "last_week":
            start_date = datetime.now() - timedelta(days=7)
            query = query.filter(Notification.created_at >= start_date)

        elif time_range == "last_month":
            start_date = datetime.now() - timedelta(days=30)
            query = query.filter(Notification.created_at >= start_date)

        elif time_range == "last_year":
            start_date = datetime.now() - timedelta(days=365)
            query = query.filter(Notification.created_at >= start_date)

        elif time_range == "from_to":
            if "from_date" in data_search:
                from_date = datetime.strptime(data_search["from_date"], "%Y-%m-%d")
                query = query.filter(Notification.created_at >= from_date)
            if "to_date" in data_search:
                to_date = datetime.strptime(
                    data_search["to_date"], "%Y-%m-%d"
                ) + timedelta(days=1)
                query = query.filter(Notification.created_at < to_date)

        pagination = query.paginate(
            page=data_search["page"], per_page=data_search["per_page"], error_out=False
        )
        return pagination

    @staticmethod
    def update_translated_notifications(translations: dict):
        if not translations:
            return 0

        updated = 0
        for id, desc_kr in translations.items():
            notif = db.session.get(Notification, id)
            if notif:
                notif.description_korea = desc_kr
                updated += 1
        db.session.commit()
        return updated

    @staticmethod
    def create_notification_with_task(session=None, **kwargs):
        if session is None:
            session = db.session  # fallback cho Flask request context
        notification = Notification(**kwargs)
        session.add(notification)
        session.commit()
        return notification

    @staticmethod
    def create_or_update_notification_by_type_and_batch(render_id, **kwargs):
        # Tìm notification cũ
        notification = Notification.objects(render_id=render_id).first()
        if notification:
            NotificationServices.update_notification(notification.id, **kwargs)
        else:
            # Tạo mới nếu chưa có
            NotificationServices.create_notification(**kwargs)
