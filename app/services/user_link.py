from app.lib.logger import logger
from app.services.user import UserService
from app.third_parties.facebook import FacebookTokenService
from app.third_parties.instagram import InstagramTokenService
from app.third_parties.thread import ThreadTokenService
from app.third_parties.twitter import TwitterTokenService
from app.third_parties.youtube import YoutubeTokenService


class UserLinkService:

    @staticmethod
    def update_user_link(link, user_id, args, redirect_uri=""):
        is_active = False

        user_link = UserService.find_user_link(link_id=link.id, user_id=user_id)
        user_link_id = user_link.id if user_link else 0

        logger.info(f"user_link_id: {user_link_id}")
        logger.info(f"args: {args}")

        if link.type == "X":
            UserService.update_user_link(
                id=user_link_id,
                status=0,
            )

            code = args.get("Code")
            if not code:
                code = args.get("code")

            is_active = UserLinkService.save_link_x(
                user_link_id=user_link_id, code=code, redirect_uri=redirect_uri
            )

        if link.type == "FACEBOOK":
            UserService.update_user_link(
                id=user_link_id,
                status=0,
            )

            access_token = args.get("AccessToken")
            if not access_token:
                access_token = args.get("accessToken")

            is_active = UserLinkService.save_link_facebook(
                user_link_id=user_link_id, access_token=access_token
            )

        if link.type == "YOUTUBE":
            UserService.update_user_link(
                id=user_link_id,
                status=0,
            )

            code = args.get("Code")
            if not code:
                code = args.get("code")

            is_active = UserLinkService.save_link_youtube(
                user_link_id=user_link_id, code=code, redirect_uri=redirect_uri
            )

        if link.type == "THREAD":
            UserService.update_user_link(
                id=user_link_id,
                status=0,
            )

            code = args.get("Code")
            if not code:
                code = args.get("code")

            is_active = UserLinkService.save_link_thread(
                user_link_id=user_link_id, code=code, redirect_uri=redirect_uri
            )

        if link.type == "INSTAGRAM":
            UserService.update_user_link(
                id=user_link_id,
                status=0,
            )

            code = args.get("Code")
            if not code:
                code = args.get("code")

            is_active = UserLinkService.save_link_instagram(
                user_link_id=user_link_id, code=code, redirect_uri=redirect_uri
            )

        if link.type == "BLOG_NAVER":
            link = args.get("Link")

            UserService.update_user_link(
                id=user_link_id,
                meta_url=link,
            )

            is_active = True

        return is_active

    @staticmethod
    def update_info_user_link(user_link_id, info):
        UserService.update_user_link(
            id=user_link_id,
            social_id=info.get("id"),
            username=info.get("username"),
            name=info.get("name"),
            avatar=info.get("avatar"),
            url=info.get("url"),
            status=1,
        )
        return True

    @staticmethod
    def save_link_facebook(user_link_id, access_token):
        is_active = FacebookTokenService().exchange_token(
            access_token=access_token, user_link_id=user_link_id
        )
        fb_data = {}
        if is_active:
            data = FacebookTokenService().fetch_page_token_backend(
                user_link_id=user_link_id, is_all=True, page_id=None
            )
            logger.info(f"-----------FACEBOOK DATA: {data}-------------")
            if data:
                tasks = data.get("tasks")
                if "CREATE_CONTENT" in tasks:
                    fb_data = FacebookTokenService().get_info_page(data)
                else:
                    is_active = False
            else:
                is_active = False

        if is_active:
            UserLinkService.update_info_user_link(
                user_link_id,
                fb_data,
            )
        return is_active

    @staticmethod
    def save_link_x(user_link_id, code, redirect_uri=""):
        is_active = TwitterTokenService().fetch_token(
            code, user_link_id, redirect_uri=redirect_uri
        )
        if is_active:
            data = TwitterTokenService().fetch_user_info(user_link_id)
            logger.info(f"-----------TWITTER DATA: {data}-------------")
            if data:
                UserLinkService.update_info_user_link(
                    user_link_id,
                    data,
                )
            else:
                is_active = False
        return is_active

    @staticmethod
    def save_link_youtube(user_link_id, code, redirect_uri=""):
        is_active = YoutubeTokenService().exchange_code_for_token(
            code=code, user_link_id=user_link_id, redirect_uri=redirect_uri
        )
        if is_active:
            data = YoutubeTokenService().fetch_channel_info(user_link_id)
            if data:
                UserLinkService.update_info_user_link(
                    user_link_id,
                    data,
                )
            else:
                is_active = False
        return is_active

    @staticmethod
    def save_link_thread(user_link_id, code, redirect_uri=""):
        is_active = ThreadTokenService().exchange_code(
            code=code, user_link_id=user_link_id, redirect_uri=redirect_uri
        )
        if is_active:
            is_active = ThreadTokenService().exchange_long_live_token(user_link_id)
            if is_active:
                data = ThreadTokenService().get_info(user_link_id)
                if data:
                    UserLinkService.update_info_user_link(
                        user_link_id,
                        data,
                    )
                else:
                    is_active = False
        return is_active

    @staticmethod
    def save_link_instagram(user_link_id, code, redirect_uri=""):
        is_active = InstagramTokenService().exchange_code(
            code=code, user_link_id=user_link_id, redirect_uri=redirect_uri
        )
        if is_active:
            is_active = InstagramTokenService().exchange_long_live_token(user_link_id)
            if is_active:
                data = InstagramTokenService().get_info(user_link_id)
                if data:
                    UserLinkService.update_info_user_link(
                        user_link_id,
                        data,
                    )
                else:
                    is_active = False
        return is_active
