from app.models.request_log import RequestLog


class RequestLogService:

    @staticmethod
    def create_request_log(*args, **kwargs):
        request_log = RequestLog(*args, **kwargs)
        request_log.save()
        return request_log

    @staticmethod
    def find_request_log(id):
        return RequestLog.query.get(id)

    @staticmethod
    def get_request_logs():
        return RequestLog.query.where(RequestLog.status == 1).all()

    @staticmethod
    def update_request_log(id, *args):
        request_log = RequestLog.query.get(id)
        request_log.update(*args)
        return request_log

    @staticmethod
    def delete_request_log(id):
        return RequestLog.query.get(id).delete()
