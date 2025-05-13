from app.models.user import User
from app.models.referral_history import ReferralHistory
import const
from datetime import datetime, timedelta
from app.extensions import db
from sqlalchemy import and_, func, or_

class ReferralService:

    @staticmethod
    def use_referral_code(referral_code, login_user) -> dict:
        user = User.query.filter_by(referral_code=referral_code).first()
        if not user:
            return False

        usage_count = ReferralHistory.query.filter_by(referrer_user_id=user.id).count()

        if usage_count >= const.MAX_REFERRAL_USAGE:
            return False

        # Lưu lịch sử
        history = ReferralHistory(
            referrer_user_id=user.id,
            referred_user_id=login_user.id,
            referral_code=referral_code,
            status="PENDING",
        )
        history.save()
        return True

    @staticmethod
    def update_nice(user_id, **kwargs):
        usage_user = ReferralHistory.query.filter_by(referred_user_id=user_id).first()
        if not usage_user:
            return None

        return usage_user.update(**kwargs)

    @staticmethod
    def get_by_user_id(user_id):
        referral_histories = ReferralHistory.query.filter_by(
            referrer_user_id=user_id, status="DONE"
        ).all()

        total = len(referral_histories)
        total_days = 0

        for referral_detail in referral_histories:
            days = referral_detail.days
            total_days += days
        return {
            "referral_histories": [
                referral_detail.to_dict() for referral_detail in referral_histories
            ],
            "total": total,
            "total_days": total_days,
        }

    @staticmethod
    def get_admin_referral_history(data_search):
        # Query cơ bản với các điều kiện
        query = ReferralHistory.query

        search_key = data_search.get("search_key", "")

        if search_key != "":
            search_pattern = f"%{search_key}%"
            query = query.filter(
                or_(
                    ReferralHistory.referral_code.ilike(search_pattern),
                    ReferralHistory.referrer.has(User.email.ilike(search_pattern)),
                    ReferralHistory.referred_user.has(User.email.ilike(search_pattern)),
                )
            )
            
        if data_search["type_status"] == "PENDING":
            query = query.filter(ReferralHistory.status == "PENDING")
        elif data_search["type_status"] == "DONE":
            query = query.filter(ReferralHistory.status == "DONE") 

        # Xử lý type_order
        if data_search["type_order"] == "id_asc":
            query = query.order_by(ReferralHistory.id.asc())
        elif data_search["type_order"] == "id_desc":
            query = query.order_by(ReferralHistory.id.desc())
        else:
            query = query.order_by(ReferralHistory.id.desc())

        time_range = data_search.get("time_range")  # Thêm biến time_range
        # Lọc theo khoảng thời gian
        if time_range == "today":
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            query = query.filter(ReferralHistory.created_at >= start_date)

        elif time_range == "last_week":
            start_date = datetime.now() - timedelta(days=7)
            query = query.filter(ReferralHistory.created_at >= start_date)

        elif time_range == "last_month":
            start_date = datetime.now() - timedelta(days=30)
            query = query.filter(ReferralHistory.created_at >= start_date)

        elif time_range == "last_year":
            start_date = datetime.now() - timedelta(days=365)
            query = query.filter(ReferralHistory.created_at >= start_date)

        pagination = query.paginate(
            page=data_search["page"], per_page=data_search["per_page"], error_out=False
        )
        return pagination
    
    @staticmethod
    def admin_delete_by_ids(post_ids):
        try:
            ReferralHistory.query.filter(ReferralHistory.id.in_(post_ids)).delete(
                synchronize_session=False
            )
            db.session.commit()
        except Exception as ex:
            db.session.rollback()
            return 0
        return 1
