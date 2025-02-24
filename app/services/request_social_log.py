from app.models.request_social_log import RequestSocialLog


class RequestSocialLogService:

    @staticmethod
    def create_request_social_log(*args, **kwargs):
        request_social_log = RequestSocialLog(*args, **kwargs)
        request_social_log.save()
        return request_social_log

    @staticmethod
    def find_request_social_log(id):
        return RequestSocialLog.query.get(id)

    @staticmethod
    def get_request_social_logs():
        request_social_logs = RequestSocialLog.query.where(
            RequestSocialLog.status == 1
        ).all()
        return [
            request_social_log._to_json() for request_social_log in request_social_logs
        ]

    @staticmethod
    def update_request_social_log(id, *args, **kwargs):
        request_social_log = RequestSocialLog.query.get(id)
        request_social_log.update(**kwargs)
        return request_social_log

    @staticmethod
    def delete_request_social_log(id):
        return RequestSocialLog.query.get(id).delete()

    @staticmethod
    def get_request_social_logs_by_batch_id(batch_id):
        request_social_logs = RequestSocialLog.query.where(
            RequestSocialLog.batch_id == batch_id
        ).all()
        return [
            request_social_log._to_json() for request_social_log in request_social_logs
        ]
