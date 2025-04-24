from datetime import datetime
from app.models.request_social_log import RequestSocialLog
from app.models.request_social_count import RequestSocialCount


class RequestSocialLogService:

    @staticmethod
    def create_request_social_log(*args, **kwargs):
        request_social_log = RequestSocialLog(*args, **kwargs)
        request_social_log.save()
        return request_social_log

    @staticmethod
    def find_request_social_log(id):
        return RequestSocialLog.objects.get(id)

    @staticmethod
    def get_request_social_logs():
        request_social_logs = RequestSocialLog.objects(status=1).all()
        return [
            request_social_log._to_json() for request_social_log in request_social_logs
        ]

    @staticmethod
    def update_request_social_log(id, *args, **kwargs):
        request_social_log = RequestSocialLog.objects.get(id)
        request_social_log.update(**kwargs)
        return request_social_log

    @staticmethod
    def delete_request_social_log(id):
        return RequestSocialLog.objects.get(id).delete()

    @staticmethod
    def get_request_social_logs_by_batch_id(batch_id):
        request_social_logs = RequestSocialLog.objects(batch_id=batch_id).all()
        return [
            request_social_log._to_json() for request_social_log in request_social_logs
        ]

    @staticmethod
    def increment_request_social_count(id, social=""):
        current_day = datetime.now().strftime("%Y-%m-%d")
        current_hour = datetime.now().strftime("%H")
        request_social_count = RequestSocialCount.objects(
            social=social,
            user_id=id,
            day=current_day,
            hour=current_hour,
        ).first()
        if request_social_count:
            request_social_count.count += 1
            request_social_count.save()
        else:
            request_social_count = RequestSocialCount(
                user_id=id,
                social=social,
                count=1,
                day=current_day,
                hour=current_hour,
            )
            request_social_count.save()
        return request_social_count

    @staticmethod
    def get_request_social_count_by_user_id(user_id, social):
        current_day = datetime.now().strftime("%Y-%m-%d")
        current_hour = datetime.now().strftime("%H")
        request_social_count = RequestSocialCount.query.where(
            RequestSocialCount.social == social,
            RequestSocialCount.user_id == user_id,
            RequestSocialCount.day == current_day,
            RequestSocialCount.hour == current_hour,
        ).first()
        return request_social_count.count if request_social_count else 0
