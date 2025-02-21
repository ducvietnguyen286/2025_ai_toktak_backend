from app.models.request_x_log import RequestXLog


class RequestXLogService:

    @staticmethod
    def create_request_x_log(*args, **kwargs):
        request_x_log = RequestXLog(*args, **kwargs)
        request_x_log.save()
        return request_x_log

    @staticmethod
    def find_request_x_log(id):
        return RequestXLog.query.get(id)

    @staticmethod
    def get_request_x_logs():
        request_x_logs = RequestXLog.query.where(RequestXLog.status == 1).all()
        return [request_x_log._to_json() for request_x_log in request_x_logs]

    @staticmethod
    def update_request_x_log(id, *args, **kwargs):
        request_x_log = RequestXLog.query.get(id)
        request_x_log.update(**kwargs)
        return request_x_log

    @staticmethod
    def delete_request_x_log(id):
        return RequestXLog.query.get(id).delete()

    @staticmethod
    def get_request_x_logs_by_batch_id(batch_id):
        request_x_logs = RequestXLog.query.where(RequestXLog.batch_id == batch_id).all()
        return [request_x_log._to_json() for request_x_log in request_x_logs]
