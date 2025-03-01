import os
import threading
import json

from app.lib.logger import logger
from .extensions import redis_client, socketio


def process_redis_message(message, app):
    """
    Xử lý dữ liệu nhận được từ Redis.
    Bạn có thể thêm logic tính toán vào đây, rồi emit kết quả qua SocketIO.
    """

    SOCKETIO_PROGRESS_EVENT = os.environ.get("SOCKETIO_PROGRESS_EVENT") or "progress"

    try:
        data = json.loads(message)
        logger.info("Received message from Redis: %s", data)
        socketio.emit(SOCKETIO_PROGRESS_EVENT, data)
    except Exception as e:
        app.logger.error("Error processing Redis message: %s", e)


def start_redis_subscriber(app):
    """
    Khởi chạy một thread lắng nghe channel Redis (PROGRESS_CHANNEL) và xử lý message.
    """

    def redis_listener():

        PROGRESS_CHANNEL = os.environ.get("REDIS_PROGRESS_CHANNEL") or "progessbar"

        pubsub = redis_client.pubsub()
        pubsub.subscribe(PROGRESS_CHANNEL)
        logger.info("Started Redis subscriber on channel '%s'", PROGRESS_CHANNEL)
        for item in pubsub.listen():
            print("item", item)
            if item.get("type") != "message":
                continue
            message_str = item.get("data").decode("utf-8")
            process_redis_message(message_str, app)

    thread = threading.Thread(target=redis_listener)
    thread.daemon = True
    thread.start()
