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
from app.extensions import db
from app.lib.logger import logger
from sqlalchemy import or_
import const
from dateutil.relativedelta import relativedelta


class UserService:

    @staticmethod
    def create_user(*args, **kwargs):
        user_detail = User(*args, **kwargs)
        user_detail.save()
        return user_detail
    
    @staticmethod
    def get_user_coupons(user_id):
        list_coupons = (
            CouponCode.query.filter(
                CouponCode.is_active == 1, CouponCode.used_by == user_id
            )
            .order_by(CouponCode.used_at.desc())
            .all()
        )
        coupons = []
        for coupon in list_coupons:
            coupon_dict = coupon.coupon._to_json()
            coupon_code = coupon._to_json()
            coupon_code["coupon_name"] = coupon_dict["name"]
            coupons.append(coupon_code)

        first_coupon = (
            CouponCode.query.filter(
                CouponCode.is_active == 1,
                CouponCode.used_by == user_id,
                CouponCode.expired_at >= datetime.now(),
            )
            .order_by(CouponCode.used_at.asc())
            .first()
        )

        latest_coupon = (
            CouponCode.query.filter(
                CouponCode.is_active == 1,
                CouponCode.used_by == user_id,
                CouponCode.expired_at >= datetime.now(),
            )
            .order_by(CouponCode.used_at.desc())
            .first()
        )
        coupon = latest_coupon.coupon._to_json() if latest_coupon else None
        latest_coupon = latest_coupon._to_json() if latest_coupon else None
        first_coupon = first_coupon._to_json() if first_coupon else None
        if latest_coupon:
            latest_coupon["coupon_name"] = coupon["name"] if coupon else None
        return latest_coupon, first_coupon, coupons

    @staticmethod
    def get_latest_coupon(user_id):
        first_coupon = (
            CouponCode.query.filter(
                CouponCode.is_active == 1,
                CouponCode.used_by == user_id,
                CouponCode.expired_at >= datetime.now(),
            )
            .order_by(CouponCode.used_at.asc())
            .first()
        )
        latest_coupon = (
            CouponCode.query.filter(
                CouponCode.is_active == 1,
                CouponCode.used_by == user_id,
                CouponCode.expired_at >= datetime.now(),
            )
            .order_by(CouponCode.used_at.desc())
            .first()
        )
        coupon = latest_coupon.coupon._to_json() if latest_coupon else None
        latest_coupon = latest_coupon._to_json() if latest_coupon else None
        first_coupon = first_coupon._to_json() if first_coupon else None
        if latest_coupon:
            latest_coupon["coupon_name"] = coupon["name"] if coupon else None
        return first_coupon, latest_coupon

    @staticmethod
    def find_user(id):
        return User.query.get(id)

    @staticmethod
    def get_users():
        users = User.query.where(User.status == 1).all()
        return [user._to_json() for user in users]

    @staticmethod
    def all_users():
        users = User.query.all()
        return [user._to_json() for user in users]

    @staticmethod
    def update_user(id, *args, **kwargs):
        user = User.query.get(id)
        if not user:
            return None
        user.update(**kwargs)
        return user

    @staticmethod
    def delete_user(id):
        return User.query.get(id).delete()

    @staticmethod
    def create_user_link(*args, **kwargs):
        user_link = UserLink(**kwargs)
        user_link.save()
        return user_link

    @staticmethod
    def update_by_link_multiple_user_links(link_id=0, *args, **kwargs):
        UserLink.query.filter(UserLink.link_id == link_id).update(
            kwargs, synchronize_session=False
        )
        db.session.commit()

    @staticmethod
    def find_user_link(link_id=0, user_id=0):
        user_link = (
            UserLink.query.where(UserLink.user_id == user_id).where(
                UserLink.link_id == link_id
            )
            # .where(UserLink.status == 1)
            .first()
        )
        return user_link

    @staticmethod
    def find_user_link_by_id(user_link_id=0):
        user_link = UserLink.query.get(user_link_id)
        return user_link

    @staticmethod
    def find_user_link_exist(link_id=0, user_id=0):
        user_link = (
            UserLink.query.where(UserLink.user_id == user_id)
            .where(UserLink.link_id == link_id)
            .all()
        )
        return user_link[0] if user_link else None

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

            User.query.filter(User.id.in_(user_ids)).delete(synchronize_session=False)

            db.session.commit()
        except Exception as ex:
            logger.error(f"Exception: Delete user Fail  :  {str(ex)}")
            db.session.rollback()
            return 0
        return 1

    def get_user_info_detail(user_id):
        user_login = User.query.get(user_id)
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
            start_used = datetime.strptime(start_used, "%Y-%m-%dT%H:%M:%SZ")
            last_used = datetime.strptime(last_used, "%Y-%m-%dT%H:%M:%SZ")
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
        return None
        user = User.query.filter(User.phone == mobileno, User.is_auth_nice == 1).first()

        return user
    
    @staticmethod
    def auto_extend_free_subscriptions():
        now = datetime.now()

        expired_users = User.query.filter(
            User.subscription == 'FREE',
            User.subscription_expired <= now
        ).all()

        extended = 0
        for user in expired_users:
            new_expiry = now + relativedelta(months=1)
            user.subscription_expired = new_expiry
            user.batch_total = 10
            user.batch_remain = 10
            extended += 1

        db.session.commit()
        return extended
