from app.models.user import User
from app.models.user_link import UserLink


class Service:

    @staticmethod
    def find_user(id):
        return User.query.get(id)

    @staticmethod
    def get_users():
        return User.query.where(User.status == 1).all()

    @staticmethod
    def update_user(id, *args):
        user = User.query.get(id)
        user.update(*args)
        return user

    @staticmethod
    def delete_user(id):
        return User.query.get(id).delete()

    @staticmethod
    def create_user_link(*args):
        user_link = UserLink(*args)
        user_link.save()
        return user_link
