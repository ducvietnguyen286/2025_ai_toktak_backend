import logging
import datetime
import logging.handlers as handlers

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s - %(name)s: %(message)s", datefmt="%d-%m-%Y %H:%M:%S"
)

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
    "logs/error-{0}.log".format(filename), backupCount=14
)
errorLogHandler.setLevel(logging.ERROR)
errorLogHandler.setFormatter(formatter)

logger.addHandler(handler)
logger.addHandler(errorLogHandler)


def log_social_message(message):
    custom_handler = handlers.RotatingFileHandler(
        "logs/social-{0}.log".format(filename), backupCount=14
    )
    custom_handler.setLevel(logging.INFO)
    custom_handler.setFormatter(formatter)

    custom_logger = logging.getLogger("SocialLogger")
    custom_logger.setLevel(logging.INFO)
    custom_logger.addHandler(custom_handler)

    custom_logger.info(message)
    custom_logger.removeHandler(custom_handler)
    custom_handler.close()


def log_make_video_message(message):
    # Tạo thư mục logs nếu chưa có

    # Tạo tên file log dựa trên ngày tháng
    filename = now_date.strftime("%Y-%m-%d")

    # Tạo file handler xoay vòng với 14 file backup
    custom_handler = handlers.RotatingFileHandler(
        f"logs/shotstack_make_video-{filename}.log", maxBytes=5*1024*1024, backupCount=14
    )
    custom_handler.setLevel(logging.INFO)
    custom_handler.setFormatter(formatter)

    # Tạo logger
    custom_logger = logging.getLogger("ShotStackLogger")
    custom_logger.setLevel(logging.INFO)

    # Tránh thêm handler trùng lặp
    if not custom_logger.hasHandlers():
        custom_logger.addHandler(custom_handler)

    # Ghi log
    custom_logger.info(message)

    # Đóng handler
    custom_handler.close()
    