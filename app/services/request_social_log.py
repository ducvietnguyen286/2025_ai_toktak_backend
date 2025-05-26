from datetime import datetime
from app.models.request_social_log import RequestSocialLog
from app.models.request_social_count import RequestSocialCount
from app.models.social_post_created import SocialPostCreated
from app.extensions import db
from app.lib.query import (
    select_with_filter,
    select_by_id,
    select_with_filter_one,
    update_by_id,
)


class RequestSocialLogService:

    @staticmethod
    def create_request_social_log(**kwargs):
        log = RequestSocialLog(**kwargs)
        log.save()
        return log

    @staticmethod
    def find_request_social_log(id):
        return select_by_id(RequestSocialLog, id)

    @staticmethod
    def get_request_social_logs():
        logs = select_with_filter(
            RequestSocialLog, filters=[RequestSocialLog.status == 1]
        )
        return [log._to_json() for log in logs]

    @staticmethod
    def update_request_social_log(id, **kwargs):
        return update_by_id(RequestSocialLog, id, kwargs)

    @staticmethod
    def delete_request_social_log(id):
        log = select_by_id(RequestSocialLog, id)
        if log:
            db.session.delete(log)
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_request_social_logs_by_batch_id(batch_id):
        logs = select_with_filter(
            RequestSocialLog, filters=[RequestSocialLog.batch_id == batch_id]
        )
        return [log._to_json() for log in logs]

    @staticmethod
    def increment_request_social_count(user_id, social=""):
        now = datetime.now()
        day = now.strftime("%Y-%m-%d")
        hour = now.strftime("%H")

        count = select_with_filter_one(
            RequestSocialCount,
            filters=[
                RequestSocialCount.user_id == user_id,
                RequestSocialCount.social == social,
                RequestSocialCount.day == day,
                RequestSocialCount.hour == hour,
            ],
        )

        if count:
            count.count += 1
        else:
            count = RequestSocialCount(
                user_id=user_id, social=social, count=1, day=day, hour=hour
            )
            db.session.add(count)

        db.session.commit()
        return count

    @staticmethod
    def get_request_social_count_by_user_id(user_id, social):
        now = datetime.now()
        day = now.strftime("%Y-%m-%d")
        hour = now.strftime("%H")

        count = select_with_filter_one(
            RequestSocialCount,
            filters=[
                RequestSocialCount.user_id == user_id,
                RequestSocialCount.social == social,
                RequestSocialCount.day == day,
                RequestSocialCount.hour == hour,
            ],
        )
        return count.count if count else 0

    @staticmethod
    def increment_social_post_created(user_id, social):
        now = datetime.now()
        day = now.strftime("%Y-%m-%d")

        post = select_with_filter_one(
            SocialPostCreated,
            filters=[
                SocialPostCreated.user_id == user_id,
                SocialPostCreated.social == social,
                SocialPostCreated.day == day,
            ],
        )

        if post:
            post.count += 1
        else:
            post = SocialPostCreated(user_id=user_id, social=social, count=1, day=day)
            db.session.add(post)

        db.session.commit()
        return post

    @staticmethod
    def get_social_post_created_by_user_id(user_id, social):
        now = datetime.now()
        day = now.strftime("%Y-%m-%d")

        post = select_with_filter_one(
            SocialPostCreated,
            filters=[
                SocialPostCreated.user_id == user_id,
                SocialPostCreated.social == social,
                SocialPostCreated.day == day,
            ],
        )

        return post.count if post else 0
