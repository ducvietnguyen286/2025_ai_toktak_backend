import requests
from app.errors.exceptions import BadRequest
from app.models.social_account import SocialAccount
from app.models.user import User
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
)


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
    ):
        user_info = None
        if provider == "FACEBOOK":
            user_info = AuthService.get_facebook_user_info(access_token)
        elif provider == "GOOGLE":
            user_info = AuthService.get_google_user_info(access_token)
        else:
            raise BadRequest(message="Social not supported")

        if not user_info:
            raise BadRequest(message="Social login failed")

        provider_user_id = user_info.get("id")
        email = user_info.get("email")
        name = user_info.get("name")

        social_account = SocialAccount.query.filter_by(
            provider=provider, provider_user_id=provider_user_id
        ).first()

        if social_account:
            user = User.query.get(social_account.user_id)
        else:
            user = User(email=email, username=name)
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
    def get_facebook_user_info(access_token):
        user_info_url = "https://graph.facebook.com/me"
        params = {"fields": "id,name,email", "access_token": access_token}
        response = requests.get(user_info_url, params=params)
        if response.status_code == 200:
            user_info = response.json()
            return user_info
        return None

    @staticmethod
    def get_google_user_info(
        access_token,
    ):

        response = requests.get(
            f"https://www.googleapis.com/oauth2/v1/userinfo?access_token={access_token}"
        )
        if response.status_code == 200:
            user_info = response.json()
            return user_info
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
