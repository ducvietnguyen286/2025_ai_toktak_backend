from app.errors.const import error_codes


class ApiException(Exception):
    status_code = 500
    message = "Internal Server Error"

    def __init__(self, code=None, message=None):
        self.code = code if code is not None else self.__class__.status_code
        self.message = error_codes[self.code] if message is None else message

    @property
    def to_dict(self):
        return {'error': {'message': self.message, 'code': self.code}}


class BadRequest(ApiException):
    status_code = 400
    message = "Bad Request"


class NotFound(ApiException):
    status_code = 404
    message = "Not Found"


class MethodNotAllowed(ApiException):
    status_code = 405
    message = "Method Not Allowed"


class UnSupportedMediaType(ApiException):
    status_code = 415
    message = "Unsupported Media Type"


class Unauthorized(ApiException):
    status_code = 401
    message = "Unauthorized Error"
