from app.errors.exceptions import BadRequest
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
