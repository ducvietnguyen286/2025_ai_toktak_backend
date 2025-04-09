from app.models.coupon_code import CouponCode
from app.models.user import User
from app.models.user_link import UserLink
from datetime import datetime, timedelta
from app.models.post import Post
from app.models.batch import Batch
from app.models.social_account import SocialAccount
from app.models.notification import Notification
from app.extensions import db
from app.lib.logger import logger
import const


class UserService:

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
    def update_user(id, *args):
        user = User.query.get(id)
        user.update(*args)
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
    def admin_search_users(data_search):
        # Query cơ bản với các điều kiện
        query = User.query.filter(User.user_type == const.USER)

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

            User.query.filter(User.id.in_(user_ids)).delete(synchronize_session=False)

            db.session.commit()
        except Exception as ex:
            logger.error(f"Exception: Delete user Fail  :  {str(ex)}")
            db.session.rollback()
            return 0
        return 1
