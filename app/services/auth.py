import os
import requests
from app.errors.exceptions import BadRequest
from app.lib.logger import logger
from app.models.social_account import SocialAccount
from app.models.user import User
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
)
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


class AuthService:

    @staticmethod
    def register(email, password, username=""):
        user = User.query.filter_by(email=email).first()
        if user:
            raise BadRequest(message="Email already exists")
        user = User(email=email, username=username)
        user.set_password(password)
        user.save()
        return user

    @staticmethod
    def login(email, password):
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User.query.filter_by(username=email).first()
        if not user or not user.check_password(password):
            raise BadRequest(message="Email or password is incorrect")
        return user

    @staticmethod
    def social_login(
        provider,
        access_token,
        person_id="",
    ):
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

        social_account = SocialAccount.query.filter_by(
            provider=provider, provider_user_id=provider_user_id
        ).first()

        if social_account:
            user = User.query.get(social_account.user_id)
        else:
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(email=email, name=name, avatar=avatar)
                user.save()
            else:
                user.name = name
                user.avatar = avatar
                user.save()

            social_account = SocialAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                access_token=access_token,
            )
            social_account.save()
        return user

    @staticmethod
    def get_facebook_user_info(access_token, person_id):
        user_info_url = f"https://graph.facebook.com/v22.0/{person_id}"
        params = {"fields": "id,name,email,picture", "access_token": access_token}
        response = requests.get(user_info_url, params=params)
        print(response.json())
        if response.status_code == 200:
            user_info = response.json()
            return user_info
        return None

    @staticmethod
    def get_google_user_info(
        access_token,
    ):
        WEB_CLIENT_ID = os.environ.get("AUTH_GOOGLE_CLIENT_ID")
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
        }

    @staticmethod
    def refresh_token():
        current_user = get_jwt_identity()
        access_token = create_access_token(identity=current_user)
        return {"access_token": access_token}

    @staticmethod
    def get_current_identity():
        subject = get_jwt_identity()
        user_id = int(subject)
        user = User.query.get(user_id)
        return user
