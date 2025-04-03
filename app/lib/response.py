from app.lib.logger import logger


class Response:

    def __init__(self, code=200, message="", data={}, status=200):
        try:
            self.status = status
            self.message = message
            self.data = data
            self.code = code
        except Exception as e:
            logger.error(f"Error in Response __init__: {e}", exc_info=True)
            self.status = 500
            self.message = "Internal Server Error"
            self.data = {}
            self.code = 500

    def to_dict(self):
        try:
            return {
                "code": self.code,
                "message": self.message,
                "data": self.data,
            }, self.status
        except Exception as e:
            logger.error(f"Error in Response to_dict: {e}", exc_info=True)
            return {"code": 500, "message": "Internal Server Error", "data": {}}, 500
