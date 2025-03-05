from app.models.user import User
from app.models.user_link import UserLink


class UserService:

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
            UserLink.query.where(UserLink.user_id == user_id)
            .where(UserLink.link_id == link_id)
            .where(UserLink.status == 1)
            .first()
        )
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
