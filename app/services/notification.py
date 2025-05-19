from bson import ObjectId
from app.models.notification import Notification
from datetime import datetime, timedelta
from app.services.user import UserService
import const
from mongoengine import Q


class NotificationServices:

    @staticmethod
    def create_notification(*args, **kwargs):
        # user_id = kwargs.get("user_id")
        # if user_id:
        #     current_user = UserService.find_user(user_id)
        #     email = current_user.email if current_user else None
        #     if email:
        #         kwargs["email"] = email
        notification = Notification(*args, **kwargs)
        notification.save()
        return notification

    @staticmethod
    def find(id):
        return Notification.objects.get(id=ObjectId(id))

    @staticmethod
    def update_notification(id, *args, **kwargs):
        notification = Notification.objects.get(id=ObjectId(id))
        notification.update(**kwargs)
        return notification

    @staticmethod
    def find_notification_sns(post_id, notification_type):
        notification = Notification.objects(
            post_id=post_id,
            notification_type=notification_type,
        ).first()
        return notification

    @staticmethod
    def delete(id):
        return Notification.objects.get(id=ObjectId(id)).delete()

    @staticmethod
    def update_notification_by_batch_id(batch_id, *args, **kwargs):
        updated_rows = Notification.objects(batch_id=batch_id).update(**kwargs)
        return updated_rows

    @staticmethod
    def get_notifications(data_search):
        query = Notification.objects(user_id=data_search["user_id"])

        tp = data_search.get("type_post")
        if tp in ("video", "image", "blog"):
            query = query.filter(type=tp)

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
                query = query.filter(Q(created_at__gte=start))

        order = data_search.get("type_order", "id_desc")
        if order == "id_asc":
            query = query.order_by("id")
        else:
            query = query.order_by("-id")

        page = max(int(data_search.get("page", 1)), 1)
        per_page = max(int(data_search.get("per_page", 10)), 1)
        skip = (page - 1) * per_page

        total = query.count()
        items = query.skip(skip).limit(per_page)

        return {
            "items": list(items),
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }

    @staticmethod
    def delete_posts_by_ids(post_ids):
        try:
            deleted_count = Notification.objects(id__in=post_ids).delete()
            return deleted_count
        except Exception as ex:
            return 0

    @staticmethod
    def getTotalNotification(data_search):
        qs = Notification.objects(user_id=data_search["user_id"])
        typ = data_search.get("type_read")
        if typ == "0":
            qs = qs.filter(is_read=False)
        elif typ == "1":
            qs = qs.filter(is_read=True)

        return qs.count()

    @staticmethod
    def update_post_by_user_id(user_id, *args, **kwargs):
        updates = {f"set__{field}": value for field, value in kwargs.items()}
        updated_count = Notification.objects(user_id=user_id).update(**updates)
        return updated_count

    @staticmethod
    def get_admin_notifications(data_search):
        qs = Notification.objects

        t_notif = data_search.get("type_notification")
        if t_notif is not None and t_notif != "":
            t_notif = int(t_notif)
            if t_notif == 0:
                qs = qs.filter(status=const.NOTIFICATION_FALSE)
            elif t_notif == 1:
                qs = qs.filter(status=const.NOTIFICATION_SUCCESS)

        sk = data_search.get("search_key", "").strip()
        if sk:
            qs = qs.filter(Q(title__icontains=sk) | Q(description__icontains=sk))

        tp = data_search.get("type_post")
        if tp in ("video", "image", "blog"):
            qs = qs.filter(type=tp)

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
                qs = qs.filter(created_at__gte=start)

        order = data_search.get("type_order", "id_desc")
        if order == "id_asc":
            qs = qs.order_by("id")
        else:
            qs = qs.order_by("-id")

        page = max(int(data_search.get("page", 1)), 1)
        per_page = max(int(data_search.get("per_page", 10)), 1)
        skip = (page - 1) * per_page
        total = qs.count()
        items = qs.skip(skip).limit(per_page)

        return {
            "items": list(items),
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }

    @staticmethod
    def update_translated_notifications(translations: dict):
        if not translations:
            return 0

        ids = [
            ObjectId(i) if not isinstance(i, ObjectId) else i
            for i in translations.keys()
        ]

        qs = Notification.objects(id__in=ids)
        updated = 0

        for notif in qs:
            text = translations.get(str(notif.id)) or translations.get(notif.id)
            if text:
                notif.update(set__description_korea=text)
                updated += 1

        return updated
