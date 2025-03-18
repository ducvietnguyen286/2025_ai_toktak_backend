from app.models.notification import Notification
from app.extensions import db
from datetime import datetime, timedelta


class NotificationServices:

    @staticmethod
    def create_notification(*args, **kwargs):
        notification = Notification(*args, **kwargs)
        notification.save()
        return notification

    @staticmethod
    def find(id):
        return Notification.query.get(id)

    @staticmethod
    def delete(id):
        return Notification.query.get(id).delete()

    @staticmethod
    def update_notification_by_batch_id(batch_id, *args, **kwargs):
        updated_rows = Notification.query.filter_by(batch_id=batch_id).update(
            kwargs
        )  # Cập nhật trực tiếp
        db.session.commit()  # Lưu vào database
        return updated_rows

    @staticmethod
    def get_notifications(data_search):
        # Query cơ bản với các điều kiện
        query = Notification.query.filter(
            Notification.user_id == data_search["user_id"],
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

        pagination = query.paginate(
            page=data_search["page"], per_page=data_search["per_page"], error_out=False
        )
        return pagination

    @staticmethod
    def delete_posts_by_ids(post_ids):
        try:
            Notification.query.filter(Notification.id.in_(post_ids)).delete(
                synchronize_session=False
            )
            db.session.commit()
        except Exception as ex:
            db.session.rollback()
            return 0
        return 1
