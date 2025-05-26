from bson import ObjectId
from app.models.notification import Notification
from datetime import datetime, timedelta
from app.services.user import UserService
import const
from app.lib.query import (
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
        return notification

    @staticmethod
    def find(id):
        return select_by_id(Notification, id)

    @staticmethod
    def update_notification(id, *args, **kwargs):
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
        notif = select_by_id(Notification, id)
        if notif:
            notif.delete()
            return True
        return False

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
        filters = []

        t_notif = data_search.get("type_notification")
        if t_notif is not None and t_notif != "":
            t_notif = int(t_notif)
            if t_notif == 0:
                filters.append(Notification.status == const.NOTIFICATION_FALSE)
            elif t_notif == 1:
                filters.append(Notification.status == const.NOTIFICATION_SUCCESS)

        sk = data_search.get("search_key", "").strip()
        if sk:
            filters.append(
                or_(
                    Notification.title.ilike(f"%{sk}%"),
                    Notification.description.ilike(f"%{sk}%"),
                )
            )

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
