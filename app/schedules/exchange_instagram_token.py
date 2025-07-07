import datetime
import json
from app.lib.logger import log_instagram_message
from app.models.link import Link
from app.models.user_link import UserLink
from app.third_parties.instagram import InstagramTokenService


def exchange_instagram_token(app):
    with app.app_context():

        log_instagram_message("---------------REFRESH INSTAGRAM TOKEN-----------------")

        next_seven_days = datetime.datetime.now() + datetime.timedelta(days=7)
        instagram_link = Link.query.where(Link.type == "INSTAGRAM").first()

        expire_users = (
            UserLink.query.where(UserLink.status == 1)
            .where(UserLink.link_id == instagram_link.id)
            .where(UserLink.expired_at <= next_seven_days)
            .all()
        )

        log_instagram_message(f"Found {len(expire_users)} users to refresh token")

        for user_link in expire_users:

            meta = json.loads(user_link.meta)
            access_token = meta.get("access_token")

            InstagramTokenService().refresh_token(
                user_link=user_link, access_token=access_token
            )
