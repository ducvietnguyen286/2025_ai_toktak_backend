from app.lib.logger import logger
from app.models.user import User
from app.models.user_link import UserLink
from app.third_parties.facebook import FacebookTokenService
from app.third_parties.thread import ThreadTokenService
from app.third_parties.twitter import TwitterTokenService
from app.third_parties.youtube import YoutubeTokenService


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
    def update_user_link(link, user_link, args):
        if link.type == "X":
            user_link.status = 0
            user_link.save()

            code = args.get("Code")
            is_active = UserService.save_link_x(user_link, code)

        if link.type == "FACEBOOK":
            user_link.status = 0
            user_link.save()

            access_token = args.get("AccessToken")
            is_active = UserService.save_link_facebook(user_link, access_token)

        if link.type == "YOUTUBE":
            user_link.status = 0
            user_link.save()

            code = args.get("Code")
            is_active = UserService.save_link_youtube(user_link, code)

        if link.type == "THREAD":
            user_link.status = 0
            user_link.save()

            code = args.get("Code")
            is_active = UserService.save_link_thread(user_link, code)

        return is_active

    @staticmethod
    def update_info_user_link(user_link, info):
        user_link.social_id = info.get("social_id")
        user_link.name = info.get("name")
        user_link.avatar = info.get("avatar")
        user_link.url = info.get("url")
        user_link.save()
        user_link.status = 1
        return user_link

    @staticmethod
    def save_link_facebook(user_link, access_token):
        is_active = FacebookTokenService().exchange_token(
            access_token=access_token, user_link=user_link
        )
        fb_data = {}
        if is_active:
            data = FacebookTokenService().fetch_page_token_backend(
                user_link=user_link, is_all=True, page_id=None
            )
            logger.info(f"-----------FACEBOOK DATA: {data}-------------")
            if data:
                tasks = data.get("tasks")
                if "CREATE_CONTENT" in tasks:
                    fb_data = FacebookTokenService().get_info_page(data)
                else:
                    is_active = False

        if is_active:
            UserService.update_info_user_link(
                user_link,
                fb_data,
            )
        return is_active

    @staticmethod
    def save_link_x(user_link, code):
        is_active = TwitterTokenService().fetch_token(code, user_link)
        if is_active:
            data = TwitterTokenService().fetch_user_info(user_link)
            logger.info(f"-----------TWITTER DATA: {data}-------------")
            if data:
                UserService.update_info_user_link(
                    user_link,
                    data,
                )
        return is_active

    @staticmethod
    def save_link_youtube(user_link, code):
        is_active = YoutubeTokenService().exchange_code_for_token(
            code=code, user_link=user_link
        )
        if is_active:
            data = YoutubeTokenService().fetch_channel_info(user_link)
            if data:
                UserService.update_info_user_link(
                    user_link,
                    data,
                )
        return is_active

    @staticmethod
    def save_link_thread(user_link, code):
        is_active = ThreadTokenService().exchange_code(code=code, user_link=user_link)
        if is_active:
            is_active = ThreadTokenService().exchange_long_live_token(user_link)
            if is_active:
                data = ThreadTokenService().get_info(user_link)
                if data:
                    UserService.update_info_user_link(
                        user_link,
                        data,
                    )
        return is_active
