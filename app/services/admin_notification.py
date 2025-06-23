from app.lib.string import parse_date
from datetime import datetime, timedelta
from app.models.admin_notification import AdminNotification

from app.extensions import db
from app.lib.logger import logger
from sqlalchemy import select, update, delete, or_, func
from app.lib.query import (
    select_with_filter,
    select_by_id,
    select_with_filter_one,
    update_by_id,
)
import const
from dateutil.relativedelta import relativedelta

class AdminNotificationService:

    @staticmethod
    def create_user(*args, **kwargs):
        admin_notification = AdminNotification(*args, **kwargs)
        admin_notification.save()
        return admin_notification

    @staticmethod
    def admin_search_admin_notifications(data_search):
        # Query cơ bản với các điều kiện
        query = AdminNotification.query

        if "search" in data_search and data_search["search"]:
            search_term = f"%{data_search['search']}%"
            query = query.filter(
                or_(
                    AdminNotification.title.ilike(search_term),
                    AdminNotification.description.ilike(search_term),
                )
            )
        if "member_type" in data_search and data_search["member_type"]:
            query = query.filter(AdminNotification.subscription == data_search["member_type"])

        # Xử lý type_order
        if data_search["type_order"] == "id_asc":
            query = query.order_by(AdminNotification.id.asc())
        elif data_search["type_order"] == "id_desc":
            query = query.order_by(AdminNotification.id.desc())
        else:
            query = query.order_by(AdminNotification.id.desc())

        time_range = data_search.get("time_range")  # Thêm biến time_range
        # Lọc theo khoảng thời gian
        if time_range == "today":
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            query = query.filter(AdminNotification.created_at >= start_date)

        elif time_range == "last_week":
            start_date = datetime.now() - timedelta(days=7)
            query = query.filter(AdminNotification.created_at >= start_date)

        elif time_range == "last_month":
            start_date = datetime.now() - timedelta(days=30)
            query = query.filter(AdminNotification.created_at >= start_date)

        elif time_range == "last_year":
            start_date = datetime.now() - timedelta(days=365)
            query = query.filter(AdminNotification.created_at >= start_date)
        elif time_range == "from_to":
            if "from_date" in data_search:
                from_date = datetime.strptime(data_search["from_date"], "%Y-%m-%d")
                query = query.filter(AdminNotification.created_at >= from_date)
            if "to_date" in data_search:
                to_date = datetime.strptime(
                    data_search["to_date"], "%Y-%m-%d"
                ) + timedelta(days=1)
                query = query.filter(AdminNotification.created_at < to_date)

        pagination = query.paginate(
            page=data_search["page"], per_page=data_search["per_page"], error_out=False
        )
        return pagination

    @staticmethod
    def delete_admin_notification_by_ids(user_ids):
        try:
             
            AdminNotification.query.filter(AdminNotification.id.in_(user_ids)).delete(synchronize_session=False)

            db.session.commit()
        except Exception as ex:
            logger.error(f"Exception: Delete user Fail  :  {str(ex)}")
            db.session.rollback()
            return 0
        return 1

      