import datetime
import json
from app.lib.logger import log_facebook_message
from app.models.link import Link
from app.models.user_link import UserLink
from app.third_parties.facebook import FacebookTokenService


def exchange_facebook_token(app):
    with app.app_context():

        log_facebook_message("---------------REFRESH FACEBOOK TOKEN-----------------")

        next_seven_days = datetime.datetime.now() + datetime.timedelta(days=7)
        facebook_link = Link.query.where(Link.type == "FACEBOOK").first()

        expire_users = (
            UserLink.query.where(UserLink.status == 1)
            .where(UserLink.link_id == facebook_link.id)
            .where(UserLink.expired_at <= next_seven_days)
            .all()
        )

        log_facebook_message(f"Found {len(expire_users)} users to refresh token")

        for user_link in expire_users:

            meta = json.loads(user_link.meta)
            access_token = meta.get("access_token")

            FacebookTokenService().exchange_token(
                user_link_id=user_link.id, access_token=access_token
            )
