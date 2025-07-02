from app.lib.string import parse_date
from app.models.coupon_code import CouponCode
from app.models.user import User
from app.models.user_link import UserLink
from datetime import datetime, timedelta
from app.models.post import Post
from app.models.batch import Batch
from app.models.social_account import SocialAccount
from app.models.notification import Notification
from app.models.memberprofile import MemberProfile
from app.models.referral_history import ReferralHistory
from app.models.payment import Payment
from app.models.payment_detail import PaymentDetail
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
from app.extensions import redis_client
import json
from dateutil.relativedelta import relativedelta

from app.models.user_history import UserHistory


class UserService:

    @staticmethod
    def create_user(*args, **kwargs):
        user_detail = User(*args, **kwargs)
        user_detail.save()
        return user_detail

    @staticmethod
    def get_user_coupons(user_id):
        list_coupons = select_with_filter(
            CouponCode,
            [CouponCode.is_active == 1, CouponCode.used_by == user_id],
            [CouponCode.used_at.desc()],
        )
        coupons = []
        for coupon in list_coupons:
            coupon_dict = coupon.coupon._to_json()
            coupon_code = coupon._to_json()
            coupon_code["coupon_name"] = coupon_dict["name"]
            coupon_code["type"] = "coupon"
            coupons.append(coupon_code)

        first_coupon = select_with_filter_one(
            CouponCode,
            [
                CouponCode.is_active == 1,
                CouponCode.used_by == user_id,
                CouponCode.expired_at >= datetime.now(),
            ],
            [CouponCode.used_at.asc()],
        )

        latest_coupon = select_with_filter_one(
            CouponCode,
            [
                CouponCode.is_active == 1,
                CouponCode.used_by == user_id,
                CouponCode.expired_at >= datetime.now(),
            ],
            [CouponCode.used_at.desc()],
        )

        coupon = latest_coupon.coupon._to_json() if latest_coupon else None
        latest_coupon = latest_coupon._to_json() if latest_coupon else None
        first_coupon = first_coupon._to_json() if first_coupon else None
        if latest_coupon:
            latest_coupon["coupon_name"] = coupon["name"] if coupon else None
        return latest_coupon, first_coupon, coupons

    @staticmethod
    def get_latest_coupon(user_id):
        first_coupon = select_with_filter_one(
            CouponCode,
            [
                CouponCode.is_active == 1,
                CouponCode.used_by == user_id,
                CouponCode.expired_at >= datetime.now(),
            ],
            [CouponCode.used_at.asc()],
        )
        latest_coupon = select_with_filter_one(
            CouponCode,
            [
                CouponCode.is_active == 1,
                CouponCode.used_by == user_id,
                CouponCode.expired_at >= datetime.now(),
            ],
            [CouponCode.used_at.desc()],
        )

        coupon = latest_coupon.coupon._to_json() if latest_coupon else None
        latest_coupon = latest_coupon._to_json() if latest_coupon else None
        first_coupon = first_coupon._to_json() if first_coupon else None
        if latest_coupon:
            latest_coupon["coupon_name"] = coupon["name"] if coupon else None
        return first_coupon, latest_coupon

    @staticmethod
    def find_user(id):
        user = select_by_id(User, id)
        return user

    @staticmethod
    def find_users(ids):
        users = select_with_filter(
            User,
            [User.id.in_(ids)],
            [],
        )
        return users

    @staticmethod
    def get_users():
        users = select_with_filter(
            User,
            [User.status == 1],
            [User.created_at.desc()],
        )
        return [user._to_json() for user in users]

    @staticmethod
    def all_users():
        users = select_with_filter(
            User,
            [],
            [User.created_at.desc()],
        )
        return [user._to_json() for user in users]

    @staticmethod
    def update_user(id, *args, **kwargs):
        user = update_by_id(User, id, data=kwargs)
        return user

    @staticmethod
    def update_user_by_id__session(id, *args, **kwargs):
        user = update_by_id(User, id, data=kwargs)
        # user = update_by_id(User, id, **kwargs)
        return user

    @staticmethod
    def delete_user(id):
        try:
            delete_stmt = delete(User).where(User.id == id)
            db.session.execute(delete_stmt)
            db.session.commit()
        except Exception as ex:
            db.session.rollback()
            return 0
        return 1

    @staticmethod
    def create_user_link(*args, **kwargs):
        user_link = UserLink(**kwargs)
        user_link.save()
        return user_link

    @staticmethod
    def update_user_link(id, *args, **kwargs):
        update_by_id(UserLink, id, data=kwargs)
        return True

    @staticmethod
    def update_by_link_multiple_user_links(link_id=0, *args, **kwargs):
        UserLink.query.filter(UserLink.link_id == link_id).update(
            kwargs, synchronize_session=False
        )
        db.session.commit()

    @staticmethod
    def find_user_link(link_id=0, user_id=0):
        user_link = (
            UserLink.query.where(UserLink.user_id == user_id)
            .where(UserLink.link_id == link_id)
            .first()
        )
        return user_link if user_link else None

    @staticmethod
    def find_user_link_by_id(user_link_id=0):
        return select_by_id(UserLink, user_link_id)

    @staticmethod
    def find_user_link_exist(link_id=0, user_id=0):
        user_link = select_with_filter_one(
            UserLink,
            [UserLink.user_id == user_id, UserLink.link_id == link_id],
            [],
        )
        return user_link

    @staticmethod
    def get_by_link_user_links(link_id=0, user_id=0):
        user_links = (
            UserLink.query.where(UserLink.status == 1)
            .where(UserLink.user_id == user_id)
            .where(UserLink.link_id == link_id)
            .all()
        )
        return [user_link._to_json() for user_link in user_links]

    @staticmethod
    def get_user_links(user_id=0):
        user_links = (
            UserLink.query.where(UserLink.status == 1)
            .where(UserLink.user_id == user_id)
            .all()
        )
        return [user_link._to_json() for user_link in user_links]

    @staticmethod
    def get_total_link(user_id, with_out_link=const.NAVER_LINK_BLOG):
        count = (
            UserLink.query.where(UserLink.status == 1)
            .where(UserLink.user_id == user_id)
            .where(UserLink.link_id != with_out_link)
            .count()
        )
        return count

    @staticmethod
    def get_original_user_links(user_id=0):
        user_links = (
            UserLink.query.where(UserLink.status == 1)
            .where(UserLink.user_id == user_id)
            .all()
        )
        return user_links

    @staticmethod
    def delete_user_link(user_link_id=0):
        user_link = UserLink.query.get(user_link_id)
        if not user_link:
            return None
        user_link.delete()
        return user_link

    @staticmethod
    def admin_search_users(data_search):
        # Query cơ bản với các điều kiện
        query = User.query.filter(User.user_type == const.USER)

        if "search" in data_search and data_search["search"]:
            search_term = f"%{data_search['search']}%"
            query = query.filter(
                or_(
                    User.email.ilike(search_term),
                    User.name.ilike(search_term),
                    User.username.ilike(search_term),
                    User.phone.ilike(search_term),
                    User.contact.ilike(search_term),
                    User.company_name.ilike(search_term),
                    User.referral_code.ilike(search_term),
                )
            )
        if "member_type" in data_search and data_search["member_type"]:
            query = query.filter(User.subscription == data_search["member_type"])

        # Xử lý type_order
        if data_search["type_order"] == "id_asc":
            query = query.order_by(User.id.asc())
        elif data_search["type_order"] == "id_desc":
            query = query.order_by(User.id.desc())
        else:
            query = query.order_by(User.id.desc())

        time_range = data_search.get("time_range")  # Thêm biến time_range
        # Lọc theo khoảng thời gian
        if time_range == "today":
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            query = query.filter(User.created_at >= start_date)

        elif time_range == "last_week":
            start_date = datetime.now() - timedelta(days=7)
            query = query.filter(User.created_at >= start_date)

        elif time_range == "last_month":
            start_date = datetime.now() - timedelta(days=30)
            query = query.filter(User.created_at >= start_date)

        elif time_range == "last_year":
            start_date = datetime.now() - timedelta(days=365)
            query = query.filter(User.created_at >= start_date)
        elif time_range == "from_to":
            if "from_date" in data_search:
                from_date = datetime.strptime(data_search["from_date"], "%Y-%m-%d")
                query = query.filter(User.created_at >= from_date)
            if "to_date" in data_search:
                to_date = datetime.strptime(
                    data_search["to_date"], "%Y-%m-%d"
                ) + timedelta(days=1)
                query = query.filter(User.created_at < to_date)

        pagination = query.paginate(
            page=data_search["page"], per_page=data_search["per_page"], error_out=False
        )
        return pagination

    @staticmethod
    def delete_users_by_ids(user_ids):
        try:
            Post.query.filter(Post.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )
            Batch.query.filter(Batch.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )
            Notification.query.filter(Notification.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )

            SocialAccount.query.filter(SocialAccount.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )
            UserLink.query.filter(UserLink.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )

            MemberProfile.query.filter(MemberProfile.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )
            ReferralHistory.query.filter(
                ReferralHistory.referrer_user_id.in_(user_ids)
            ).delete(synchronize_session=False)

            ReferralHistory.query.filter(
                ReferralHistory.referred_user_id.in_(user_ids)
            ).delete(synchronize_session=False)

            PaymentDetail.query.filter(PaymentDetail.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )

            Payment.query.filter(Payment.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )

            UserHistory.query.filter(UserHistory.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )

            User.query.filter(User.id.in_(user_ids)).delete(synchronize_session=False)

            db.session.commit()
        except Exception as ex:
            logger.error(f"Exception: Delete user Fail  :  {str(ex)}")
            db.session.rollback()
            return 0
        return 1

    def get_user_info_detail(user_id):
        user_login = select_by_id(User, user_id)
        if not user_login:
            return None

        subscription_name = user_login.subscription
        if user_login.subscription == "FREE":
            subscription_name = "무료 체험"
        elif user_login.subscription == "STANDARD":
            subscription_name = "기업형 스탠다드 플랜"

        first_coupon, latest_coupon = UserService.get_latest_coupon(user_login.id)

        start_used = None
        if first_coupon:
            start_used = first_coupon.get("used_at")
        elif latest_coupon:
            start_used = latest_coupon.get("used_at")

        last_used = latest_coupon.get("expired_at") if latest_coupon else None

        used_date_range = ""
        if start_used and last_used:
            start_used = parse_date(start_used)
            last_used = parse_date(last_used)
            used_date_range = (
                f"{start_used.strftime('%Y.%m.%d')}~{last_used.strftime('%Y.%m.%d')}"
            )

        user_dict = user_login._to_json()
        user_dict["subscription_name"] = subscription_name
        user_dict["latest_coupon"] = latest_coupon
        user_dict["used_date_range"] = used_date_range
        return user_dict

    @staticmethod
    def check_phone_verify_nice(mobileno):
        user = User.query.filter(User.phone == mobileno, User.is_auth_nice == 1).first()
        return user

    @staticmethod
    def find_user_by_referral_code(referral_code):
        user = User.query.filter(User.referral_code == referral_code).first()
        return user

    @staticmethod
    def create_user_history(*args, **kwargs):
        user_history_detail = UserHistory(*args, **kwargs)
        user_history_detail.save()
        return user_history_detail

    @staticmethod
    def get_all_user_history_by_user_id(user_id):
        user_histories = (
            UserHistory.query.filter(UserHistory.user_id == user_id)
            .order_by(UserHistory.id.desc())
            .all()
        )
        return [user_history._to_json() for user_history in user_histories]

    @staticmethod
    def get_total_batch_total(user_id):
        batch_total = (
            UserHistory.query.with_entities(func.sum(UserHistory.value))
            .filter(UserHistory.user_id == user_id)
            .scalar()
        )
        return batch_total or 0

    @staticmethod
    def find_user_history_coupon_kol(current_user_id, type_2):
        user = UserHistory.query.filter_by(
            type="USED_COUPON", user_id=current_user_id, type_2=type_2
        ).first()
        return user if user else None

    @staticmethod
    def find_user_history_valid(current_user_id):
        current_date = datetime.now().date()
        histories = UserHistory.query.filter(
            UserHistory.type == "referral",
            UserHistory.type_2 == "STANDARD",
            UserHistory.user_id == current_user_id,
            # UserHistory.object_start_time <= current_date,
            UserHistory.object_end_time >= current_date,
        )

        total = histories.count()
        max_end_time = histories.with_entities(
            func.max(UserHistory.object_end_time)
        ).scalar()
        batch_remain = (
            histories.with_entities(func.sum(UserHistory.value)).scalar() or 0
        )

        return {
            "total": total,
            "batch_remain": batch_remain,
            "max_object_end_time": (
                max_end_time.strftime("%Y-%m-%d") if max_end_time else None
            ),
            "histories": [history_detail._to_json() for history_detail in histories],
        }

    @staticmethod
    def report_user_by_type(data_search):

        histories = UserHistory.query
        type = data_search.get("type", "")
        type_2 = data_search.get("type_2", "")

        if type != "":
            histories = histories.filter(UserHistory.type == type)
        if type_2 != "":
            histories = histories.filter(UserHistory.type_2 == type_2)
        time_range = data_search.get("time_range", "")
        if time_range == "today":
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            histories = histories.filter(UserHistory.created_at >= start_date)

        elif time_range == "last_week":
            start_date = datetime.now() - timedelta(days=7)
            histories = histories.filter(UserHistory.created_at >= start_date)

        elif time_range == "last_month":
            start_date = datetime.now() - timedelta(days=30)
            histories = histories.filter(UserHistory.created_at >= start_date)

        elif time_range == "last_year":
            start_date = datetime.now() - timedelta(days=365)
            histories = histories.filter(UserHistory.created_at >= start_date)

        elif time_range == "from_to":
            if "from_date" in data_search:
                from_date = datetime.strptime(data_search["from_date"], "%Y-%m-%d")
                histories = histories.filter(UserHistory.created_at >= from_date)
            if "to_date" in data_search:
                to_date = datetime.strptime(
                    data_search["to_date"], "%Y-%m-%d"
                ) + timedelta(days=1)
                histories = histories.filter(UserHistory.created_at < to_date)

        total = histories.count()

        return total

    @staticmethod
    def report_user_by_subscription(data_search):
        histories = User.query
        subscription = data_search.get("subscription", "")

        if subscription != "":
            histories = histories.filter(User.subscription == subscription)

        time_range = data_search.get("time_range", "")
        if time_range == "today":
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            histories = histories.filter(User.created_at >= start_date)

        elif time_range == "last_week":
            start_date = datetime.now() - timedelta(days=7)
            histories = histories.filter(User.created_at >= start_date)

        elif time_range == "last_month":
            start_date = datetime.now() - timedelta(days=30)
            histories = histories.filter(User.created_at >= start_date)

        elif time_range == "last_year":
            start_date = datetime.now() - timedelta(days=365)
            histories = histories.filter(User.created_at >= start_date)

        elif time_range == "from_to":
            if "from_date" in data_search:
                from_date = datetime.strptime(data_search["from_date"], "%Y-%m-%d")
                histories = histories.filter(User.created_at >= from_date)
            if "to_date" in data_search:
                to_date = datetime.strptime(
                    data_search["to_date"], "%Y-%m-%d"
                ) + timedelta(days=1)
                histories = histories.filter(User.created_at < to_date)

        total = histories.count()

        return total

    @staticmethod
    def update_user_with_out_session(id, *args, **kwargs):
        user = User.query.get(id)
        if not user:
            return None
        user.update(**kwargs)
        return user

    @staticmethod
    def find_user_by_redis(user_id):
        redis_key = f'{const.REDIS_KEY_TOKTAK.get("user_info_me", "user:me")}:{user_id}'
        try:
            user_json = redis_client.get(redis_key)
            if user_json:
                if isinstance(user_json, bytes):
                    user_json = user_json.decode("utf-8")
                user_data = json.loads(user_json)
                return user_data
        except Exception as e:
            logger.warning(f"Cannot get user from Redis: {e}")

        # 2. Nếu không có, lấy từ DB
        user = User.query.get(user_id)
        if user:
            # 3. Cache lại vào Redis
            try:
                user_json = json.dumps(
                    user._to_json() if hasattr(user, "_to_json") else user.to_dict()
                )
                redis_client.setex(redis_key, 86400, user_json)
            except Exception as e:
                logger.warning(f"Cannot save user to Redis: {e}")
            # Nếu muốn trả về dict
            return user._to_json() if hasattr(user, "_to_json") else user.to_dict()
        return None

    @staticmethod
    def find_user_with_out_session(id):
        user = User.query.get(id)
        if not user:
            return None
        return user

    @staticmethod
    def report_users_dashboard(data_search):

        histories = User.query

        time_range = data_search.get("time_range", "")
        if time_range == "today":
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            histories = histories.filter(User.created_at >= start_date)

        elif time_range == "last_week":
            start_date = datetime.now() - timedelta(days=7)
            histories = histories.filter(User.created_at >= start_date)

        elif time_range == "last_month":
            start_date = datetime.now() - timedelta(days=30)
            histories = histories.filter(User.created_at >= start_date)

        elif time_range == "last_year":
            start_date = datetime.now() - timedelta(days=365)
            histories = histories.filter(User.created_at >= start_date)

        elif time_range == "from_to":
            if "from_date" in data_search:
                from_date = datetime.strptime(data_search["from_date"], "%Y-%m-%d")
                histories = histories.filter(User.created_at >= from_date)
            if "to_date" in data_search:
                to_date = datetime.strptime(
                    data_search["to_date"], "%Y-%m-%d"
                ) + timedelta(days=1)
                histories = histories.filter(User.created_at < to_date)

        total = histories.count()

        return total
