import logging
import datetime
import logging.handlers as handlers
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s - %(name)s: %(message)s", datefmt="%d-%m-%Y %H:%M:%S"
)

os.makedirs("logs", exist_ok=True)

now_date = datetime.datetime.now()
filename = now_date.strftime("%d-%m-%Y")

handler = handlers.TimedRotatingFileHandler(
    "logs/toktak-{0}.log".format(filename),
    when="midnight",
    interval=1,
    backupCount=14,
    encoding="utf-8",
)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)

errorLogHandler = handlers.RotatingFileHandler(
    "logs/error-{0}.log".format(filename), backupCount=14, encoding="utf-8"
)
errorLogHandler.setLevel(logging.ERROR)
errorLogHandler.setFormatter(formatter)

logger.addHandler(handler)
logger.addHandler(errorLogHandler)


def log_facebook_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = handlers.RotatingFileHandler(
        "logs/facebook-{0}.log".format(new_filename), backupCount=14, encoding="utf-8"
    )
    custom_handler.setLevel(logging.INFO)
    custom_handler.setFormatter(formatter)

    custom_logger = logging.getLogger("FacebookLogger")
    custom_logger.setLevel(logging.INFO)
    custom_logger.addHandler(custom_handler)

    custom_logger.info(message)
    custom_logger.removeHandler(custom_handler)
    custom_handler.close()


def log_instagram_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = handlers.RotatingFileHandler(
        "logs/instagram-{0}.log".format(new_filename), backupCount=14, encoding="utf-8"
    )
    custom_handler.setLevel(logging.INFO)
    custom_handler.setFormatter(formatter)

    custom_logger = logging.getLogger("InstagramLogger")
    custom_logger.setLevel(logging.INFO)
    custom_logger.addHandler(custom_handler)

    custom_logger.info(message)
    custom_logger.removeHandler(custom_handler)
    custom_handler.close()


def log_thread_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = handlers.RotatingFileHandler(
        "logs/thread-{0}.log".format(new_filename), backupCount=14, encoding="utf-8"
    )
    custom_handler.setLevel(logging.INFO)
    custom_handler.setFormatter(formatter)

    custom_logger = logging.getLogger("ThreadLogger")
    custom_logger.setLevel(logging.INFO)
    custom_logger.addHandler(custom_handler)

    custom_logger.info(message)
    custom_logger.removeHandler(custom_handler)
    custom_handler.close()


def log_twitter_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = handlers.RotatingFileHandler(
        "logs/twitter-{0}.log".format(new_filename), backupCount=14, encoding="utf-8"
    )
    custom_handler.setLevel(logging.INFO)
    custom_handler.setFormatter(formatter)

    custom_logger = logging.getLogger("TwitterLogger")
    custom_logger.setLevel(logging.INFO)
    custom_logger.addHandler(custom_handler)

    custom_logger.info(message)
    custom_logger.removeHandler(custom_handler)
    custom_handler.close()


def log_tiktok_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = handlers.RotatingFileHandler(
        "logs/tiktok-{0}.log".format(new_filename), backupCount=14, encoding="utf-8"
    )
    custom_handler.setLevel(logging.INFO)
    custom_handler.setFormatter(formatter)

    custom_logger = logging.getLogger("TiktokLogger")
    custom_logger.setLevel(logging.INFO)
    custom_logger.addHandler(custom_handler)

    custom_logger.info(message)
    custom_logger.removeHandler(custom_handler)
    custom_handler.close()


def log_youtube_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = handlers.RotatingFileHandler(
        "logs/youtube-{0}.log".format(new_filename), backupCount=14, encoding="utf-8"
    )
    custom_handler.setLevel(logging.INFO)
    custom_handler.setFormatter(formatter)

    custom_logger = logging.getLogger("YoutubeLogger")
    custom_logger.setLevel(logging.INFO)
    custom_logger.addHandler(custom_handler)

    custom_logger.info(message)
    custom_logger.removeHandler(custom_handler)
    custom_handler.close()


def log_create_content_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = handlers.RotatingFileHandler(
        "logs/create_content-{0}.log".format(new_filename),
        backupCount=14,
        encoding="utf-8",
    )
    custom_handler.setLevel(logging.INFO)
    custom_handler.setFormatter(formatter)

    custom_logger = logging.getLogger("CreateContentLogger")
    custom_logger.setLevel(logging.INFO)
    custom_logger.addHandler(custom_handler)

    custom_logger.info(message)
    custom_logger.removeHandler(custom_handler)
    custom_handler.close()


def log_socket_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = handlers.RotatingFileHandler(
        "logs/socket-{0}.log".format(new_filename), backupCount=14, encoding="utf-8"
    )
    custom_handler.setLevel(logging.INFO)
    custom_handler.setFormatter(formatter)

    custom_logger = logging.getLogger("SocketLogger")
    custom_logger.setLevel(logging.INFO)
    custom_logger.addHandler(custom_handler)

    custom_logger.info(message)
    custom_logger.removeHandler(custom_handler)
    custom_handler.close()


def log_make_video_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = None  # Khởi tạo biến custom_handler
    try:
        custom_handler = handlers.RotatingFileHandler(
            "logs/make_video-{0}.log".format(new_filename),
            backupCount=14,
            encoding="utf-8",
        )
        custom_handler.setLevel(logging.INFO)
        custom_handler.setFormatter(formatter)

        custom_logger = logging.getLogger("MakeVideo")
        custom_logger.setLevel(logging.INFO)
        custom_logger.addHandler(custom_handler)

        custom_logger.info(message)
        custom_logger.removeHandler(custom_handler)

    except Exception as e:
        # Xử lý ngoại lệ nếu có lỗi xảy ra
        print(f"Đã xảy ra lỗi khi ghi log: {e}")
    finally:
        # Đảm bảo đóng handler sau khi sử dụng
        if custom_handler:
            custom_handler.close()


def log_webhook_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = None  # Khởi tạo biến custom_handler
    try:
        custom_handler = handlers.RotatingFileHandler(
            "logs/webhook-{0}.log".format(new_filename),
            backupCount=14,
            encoding="utf-8",
        )
        custom_handler.setLevel(logging.INFO)
        custom_handler.setFormatter(formatter)

        custom_logger = logging.getLogger("WebHookLogger")
        custom_logger.setLevel(logging.INFO)
        custom_logger.addHandler(custom_handler)

        custom_logger.info(message)
        custom_logger.removeHandler(custom_handler)

    except Exception as e:
        # Xử lý ngoại lệ nếu có lỗi xảy ra
        print(f"Đã xảy ra lỗi khi ghi log: {e}")
    finally:
        # Đảm bảo đóng handler sau khi sử dụng
        if custom_handler:
            custom_handler.close()


def log_celery_worker_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = handlers.RotatingFileHandler(
        "logs/celery_worker-{0}.log".format(new_filename),
        backupCount=14,
        encoding="utf-8",
    )
    custom_handler.setLevel(logging.INFO)
    custom_handler.setFormatter(formatter)

    custom_logger = logging.getLogger("CeleryLogger")
    custom_logger.setLevel(logging.INFO)
    custom_logger.addHandler(custom_handler)

    custom_logger.info(message)
    custom_logger.removeHandler(custom_handler)
    custom_handler.close()


def log_mongo_database(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = handlers.RotatingFileHandler(
        "logs/mongo_queries-{0}.log".format(new_filename),
        backupCount=14,
        encoding="utf-8",
    )
    custom_handler.setLevel(logging.INFO)
    custom_handler.setFormatter(formatter)

    custom_logger = logging.getLogger("MongoQueryLogger")
    custom_logger.setLevel(logging.INFO)
    custom_logger.addHandler(custom_handler)

    custom_logger.info(message)
    custom_logger.removeHandler(custom_handler)
    custom_handler.close()


def log_reset_user_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = None  # Khởi tạo biến custom_handler
    try:
        custom_handler = handlers.RotatingFileHandler(
            "logs/reset_user-{0}.log".format(new_filename),
            backupCount=14,
            encoding="utf-8",
        )
        custom_handler.setLevel(logging.INFO)
        custom_handler.setFormatter(formatter)

        custom_logger = logging.getLogger("WebHookLogger")
        custom_logger.setLevel(logging.INFO)
        custom_logger.addHandler(custom_handler)

        custom_logger.info(message)
        custom_logger.removeHandler(custom_handler)

    except Exception as e:
        # Xử lý ngoại lệ nếu có lỗi xảy ra
        print(f"Đã xảy ra lỗi khi ghi log: {e}")
    finally:
        # Đảm bảo đóng handler sau khi sử dụng
        if custom_handler:
            custom_handler.close()



def log_nice_verify_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = None  # Khởi tạo biến custom_handler
    try:
        custom_handler = handlers.RotatingFileHandler(
            "logs/nice_verify-{0}.log".format(new_filename),
            backupCount=14,
            encoding="utf-8",
        )
        custom_handler.setLevel(logging.INFO)
        custom_handler.setFormatter(formatter)

        custom_logger = logging.getLogger("MakeVideo")
        custom_logger.setLevel(logging.INFO)
        custom_logger.addHandler(custom_handler)

        custom_logger.info(message)
        custom_logger.removeHandler(custom_handler)

    except Exception as e:
        # Xử lý ngoại lệ nếu có lỗi xảy ra
        print(f"Đã xảy ra lỗi khi ghi log: {e}")
    finally:
        # Đảm bảo đóng handler sau khi sử dụng
        if custom_handler:
            custom_handler.close()