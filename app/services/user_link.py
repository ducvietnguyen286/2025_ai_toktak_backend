from app.lib.logger import logger
from app.third_parties.facebook import FacebookTokenService
from app.third_parties.instagram import InstagramTokenService
from app.third_parties.thread import ThreadTokenService
from app.third_parties.twitter import TwitterTokenService
from app.third_parties.youtube import YoutubeTokenService


class UserLinkService:

    @staticmethod
    def update_user_link(link, user_link, args):
        is_active = False

        if link.type == "X":
            user_link.status = 0
            user_link.save()

            code = args.get("Code")
            is_active = UserLinkService.save_link_x(user_link, code)

        if link.type == "FACEBOOK":
            user_link.status = 0
            user_link.save()

            access_token = args.get("AccessToken")
            is_active = UserLinkService.save_link_facebook(user_link, access_token)

        if link.type == "YOUTUBE":
            user_link.status = 0
            user_link.save()

            code = args.get("Code")
            is_active = UserLinkService.save_link_youtube(user_link, code)

        if link.type == "THREAD":
            user_link.status = 0
            user_link.save()

            code = args.get("Code")
            is_active = UserLinkService.save_link_thread(user_link, code)

        if link.type == "INSTAGRAM":
            user_link.status = 0
            user_link.save()

            code = args.get("Code")
            is_active = UserLinkService.save_link_instagram(user_link, code)

        if link.type == "BLOG_NAVER":
            link = args.get("Link")
            user_link.meta_url = link
            user_link.save()

            is_active = True

        return is_active

    @staticmethod
    def update_info_user_link(user_link, info):
        user_link.social_id = info.get("id")
        user_link.username = info.get("username")
        user_link.name = info.get("name")
        user_link.avatar = info.get("avatar")
        user_link.url = info.get("url")
        user_link.status = 1
        user_link.save()
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
            UserLinkService.update_info_user_link(
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
                UserLinkService.update_info_user_link(
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
                UserLinkService.update_info_user_link(
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
                    UserLinkService.update_info_user_link(
                        user_link,
                        data,
                    )
        return is_active

    @staticmethod
    def save_link_instagram(user_link, code):
        is_active = InstagramTokenService().exchange_code(
            code=code, user_link=user_link
        )
        if is_active:
            is_active = InstagramTokenService().exchange_long_live_token(user_link)
            if is_active:
                data = InstagramTokenService().get_info(user_link)
                if data:
                    UserLinkService.update_info_user_link(
                        user_link,
                        data,
                    )
        return is_active
