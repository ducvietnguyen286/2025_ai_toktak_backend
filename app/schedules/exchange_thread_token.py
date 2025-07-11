import datetime
import json
from app.lib.logger import log_thread_message
from app.models.link import Link
from app.models.user_link import UserLink
from app.third_parties.thread import ThreadTokenService


def exchange_thread_token(app):
    with app.app_context():

        log_thread_message("---------------REFRESH THREAD TOKEN-----------------")

        next_seven_days = datetime.datetime.now() + datetime.timedelta(days=7)
        thread_link = Link.query.where(Link.type == "THREAD").first()

        expire_users = (
            UserLink.query.where(UserLink.status == 1)
            .where(UserLink.link_id == thread_link.id)
            .where(UserLink.expired_at <= next_seven_days)
            .all()
        )

        log_thread_message(f"Found {len(expire_users)} users to refresh token")

        for user_link in expire_users:

            meta = json.loads(user_link.meta)
            access_token = meta.get("access_token")

            ThreadTokenService().refresh_token(
                user_link=user_link, access_token=access_token
            )
