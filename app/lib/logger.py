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

# ============================================================================
# HELPER FUNCTION - TỐI ƯU HÓA CODE LẶP LẠI
# ============================================================================

def _create_service_logger(service_name):
    """
    Tạo logger cho service cụ thể - tối ưu hóa để giảm code lặp lại
    Args:
        service_name: Tên service (facebook, instagram, etc.)
    Returns:
        tuple: (service_logger, handler) để có thể cleanup sau khi sử dụng
    """
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    
    # Tạo handler cho service cụ thể
    handler = handlers.RotatingFileHandler(
        f"logs/{service_name}-{new_filename}.log", 
        backupCount=14, 
        encoding="utf-8"
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    
    # Tạo logger cho service
    service_logger = logging.getLogger(f"{service_name.capitalize()}Logger")
    service_logger.setLevel(logging.INFO)
    service_logger.addHandler(handler)
    
    return service_logger, handler

# ============================================================================
# SERVICE LOG FUNCTIONS - SỬ DỤNG HELPER ĐỂ TỐI ƯU
# ============================================================================
def log_facebook_message(message):
    service_logger, handler = _create_service_logger("facebook")
    try:
        service_logger.info(message)
    finally:
        service_logger.removeHandler(handler)
        handler.close()


def log_instagram_message(message):
    service_logger, handler = _create_service_logger("instagram")
    try:
        service_logger.info(message)
    finally:
        service_logger.removeHandler(handler)
        handler.close()


def log_thread_message(message):
    service_logger, handler = _create_service_logger("thread")
    try:
        service_logger.info(message)
    finally:
        service_logger.removeHandler(handler)
        handler.close()


def log_twitter_message(message):
    service_logger, handler = _create_service_logger("twitter")
    try:
        service_logger.info(message)
    finally:
        service_logger.removeHandler(handler)
        handler.close()


def log_tiktok_message(message):
    service_logger, handler = _create_service_logger("tiktok")
    try:
        service_logger.info(message)
    finally:
        service_logger.removeHandler(handler)
        handler.close()


def log_youtube_message(message):
    service_logger, handler = _create_service_logger("youtube")
    try:
        service_logger.info(message)
    finally:
        service_logger.removeHandler(handler)
        handler.close()


def log_create_content_message(message):
    service_logger, handler = _create_service_logger("create_content")
    try:
        service_logger.info(message)
    finally:
        service_logger.removeHandler(handler)
        handler.close()


def log_socket_message(message):
    service_logger, handler = _create_service_logger("socket")
    try:
        service_logger.info(message)
    finally:
        service_logger.removeHandler(handler)
        handler.close()


def log_make_video_message(message):
    service_logger, handler = _create_service_logger("make_video")
    try:
        service_logger.info(message)
    except Exception as e:
        print(f"Đã xảy ra lỗi khi ghi log: {e}")
    finally:
        if handler:
            service_logger.removeHandler(handler)
            handler.close()


def log_webhook_message(message):
    service_logger, handler = _create_service_logger("webhook")
    try:
        service_logger.info(message)
    except Exception as e:
        print(f"Đã xảy ra lỗi khi ghi log: {e}")
    finally:
        if handler:
            service_logger.removeHandler(handler)
            handler.close()


def log_celery_worker_message(message):
    service_logger, handler = _create_service_logger("celery_worker")
    try:
        service_logger.info(message)
    finally:
        service_logger.removeHandler(handler)
        handler.close()


def log_mongo_database(message):
    service_logger, handler = _create_service_logger("mongo_queries")
    try:
        service_logger.info(message)
    finally:
        service_logger.removeHandler(handler)
        handler.close()


def log_reset_user_message(message):
    service_logger, handler = _create_service_logger("reset_user")
    try:
        service_logger.info(message)
    except Exception as e:
        print(f"Đã xảy ra lỗi khi ghi log: {e}")
    finally:
        if handler:
            service_logger.removeHandler(handler)
            handler.close()


def log_nice_verify_message(message):
    service_logger, handler = _create_service_logger("nice_verify")
    try:
        service_logger.info(message)
    except Exception as e:
        print(f"Đã xảy ra lỗi khi ghi log: {e}")
    finally:
        if handler:
            service_logger.removeHandler(handler)
            handler.close()

# ============================================================================
# CONSUMER LOGGING UTILITIES - GIẢM CODE LẶP LẠI
# ============================================================================
def setup_consumer_logging(app, consumer_name):
    """
    Setup logging cho consumer - tránh code lặp lại trong các consumer files
    Args:
        app: Flask app instance
        consumer_name: Tên consumer (FACEBOOK, INSTAGRAM, etc.)
    Returns:
        Logger instance
    """
    app.logger.setLevel(logging.DEBUG)
    app.logger.info(f"Start {consumer_name} Consumer...")
    return app.logger

def get_consumer_logger(consumer_name):
    """
    Lấy logger cho consumer với hierarchy
    Args:
        consumer_name: Tên consumer
    Returns:
        Logger instance với tên phân cấp
    """
    logger_name = f"app.consumers.{consumer_name.lower()}"
    return logging.getLogger(logger_name)