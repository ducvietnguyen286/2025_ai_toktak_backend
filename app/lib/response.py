class Response:

    def __init__(self, code = 200, message = '', data = {}, status = 200):
        self.status = status
        self.message = message
        self.data = data
        self.code = code

    def to_dict(self):
        return {
            'code': self.code,
            'message': self.message,
            'data': self.data
        }, self.status