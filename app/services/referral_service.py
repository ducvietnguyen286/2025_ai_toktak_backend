from app.models.user import User
from app.models.referral_history import ReferralHistory
import const
from datetime import datetime, timedelta
from app.extensions import db
from sqlalchemy import and_, func, or_
from app.lib.string import mask_string_with_x
from app.services.user import UserService
from const import MAX_REFERRAL_USAGE


class ReferralService:

    @staticmethod
    def find_by_referred_user_id(referred_user_id) -> dict:
        referral_history_detail = ReferralHistory.query.filter_by(
            referred_user_id=referred_user_id
        ).first()
        return referral_history_detail


    @staticmethod
    def find_by_referrer_user_id_done(referrer_user_id) -> int:
        total = ReferralHistory.query.filter(
            ReferralHistory.referrer_user_id == referrer_user_id,
            ReferralHistory.status == "DONE",
        ).count()
        return total


    @staticmethod
    def use_referral_code(referral_code, login_user) -> dict:
        user = User.query.filter_by(referral_code=referral_code).first()
        if not user:
            return False

        # check xem đã có history chưa
        user_history = ReferralService.find_by_referred_user_id(login_user.id)
        if user_history:
            return False

        referrer_user_id = user.id
        usage_count = ReferralService.find_by_referrer_user_id_done(referrer_user_id)
        if usage_count >= MAX_REFERRAL_USAGE:
            return False

        # Lưu lịch sử
        history = ReferralHistory(
            referrer_user_id=user.id,
            referred_user_id=login_user.id,
            referral_code=referral_code,
            status="PENDING",
        )
        history.save()

        referrer_update_data = {
            "referrer_user_id": user.id,
        }
        UserService.update_user_with_out_session(login_user.id, **referrer_update_data)

        return True

    @staticmethod
    def update_nice(user_id, **kwargs):
        usage_user = ReferralHistory.query.filter_by(referred_user_id=user_id).first()
        if not usage_user:
            return None
        usage_user.update(**kwargs)
        return usage_user

    @staticmethod
    def get_by_user_id(user_id):
        referral_histories = ReferralHistory.query.filter_by(
            referrer_user_id=user_id, status="DONE"
        ).all()

        total = len(referral_histories)
        total_days = 0
        result = []
        for referral_detail in referral_histories:
            days = referral_detail.days
            total_days += days

            item = referral_detail.to_dict()

            item["display_name"] = mask_string_with_x(
                item["referred_user_name"], item["updated_at_view"]
            )
            item.pop("referred_user_name", None)
            item.pop("referred_user_email", None)
            result.append(item)

        return {
            "referral_histories": result,
            "total": total,
            "total_days": min(total_days, 90),
            "max_days": 90,
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
        
        elif time_range == "from_to":
            if "from_date" in data_search:
                from_date = datetime.strptime(data_search["from_date"], "%Y-%m-%d")
                query = query.filter(ReferralHistory.created_at >= from_date)
            if "to_date" in data_search:
                to_date = datetime.strptime(
                    data_search["to_date"], "%Y-%m-%d"
                ) + timedelta(days=1)
                query = query.filter(ReferralHistory.created_at < to_date)

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

    @staticmethod
    def find_all_related_referrals(user_id):
        return ReferralHistory.query.filter(
            or_(
                ReferralHistory.referrer_user_id == user_id,
                ReferralHistory.referred_user_id == user_id,
            ),
            ReferralHistory.status == "DONE",
        ).all()
