import logging
import datetime
import logging.handlers as handlers
import os
from dotenv import load_dotenv

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


def log_advance_run_crawler_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = handlers.RotatingFileHandler(
        "logs/advance_run_crawler-{0}.log".format(new_filename),
        backupCount=14,
        encoding="utf-8",
    )
    custom_handler.setLevel(logging.INFO)
    custom_handler.setFormatter(formatter)

    custom_logger = logging.getLogger("AdvanceRunCrawlerLogger")
    custom_logger.setLevel(logging.INFO)
    custom_logger.addHandler(custom_handler)

    custom_logger.info(message)
    custom_logger.removeHandler(custom_handler)
    custom_handler.close()


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

# ============================================================================
# CRITICAL LOGGING - CHO CÁC TÌNH HUỐNG NGHIÊM TRỌNG VỚI ALERT
# ============================================================================

def log_critical_infrastructure(message, component="SYSTEM", send_alert=False):
    """
    Log cho critical infrastructure issues - cần attention ngay lập tức
    
    Args:
        message: Chi tiết lỗi critical
        component: Thành phần hệ thống (DATABASE, REDIS, QUEUE, DISK, SECURITY)
        send_alert: Có gửi alert qua Slack/Telegram không
    """
    
    # Đảm bảo .env được load (fix cho vấn đề environment)
    load_dotenv()
    
    logger = logging.getLogger(__name__)
    critical_msg = f"🔥 [CRITICAL-{component}] {message}"
    logger.critical(critical_msg)
    
    if send_alert:
        try:
            from app.third_parties.telegram import send_slack_message, send_telegram_message
            
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            alert_text = f"🚨 CRITICAL SYSTEM ALERT\n\n{critical_msg}\n\nTime: {current_time}\nServer: TokTak Production"
            
            # Gửi Slack alert
            slack_success = send_slack_message(alert_text)
            if slack_success:
                logger.info("✅ Critical alert sent to Slack successfully")
            else:
                logger.warning("⚠️ Failed to send Slack alert")
            
            # Gửi Telegram alert
            telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if telegram_token:
                send_telegram_message(alert_text)
                logger.info("✅ Critical alert sent to Telegram successfully")
                
        except Exception as e:
            logger.error(f"❌ Failed to send critical alert: {e}")

def log_critical_database(message, current_connections=None, max_connections=None):
    """Log cho database critical issues"""
    load_dotenv()
    
    if current_connections and max_connections:
        usage_percent = (current_connections / max_connections) * 100
        full_message = f"{message}\nConnections: {current_connections}/{max_connections} ({usage_percent:.1f}%)"
    else:
        full_message = message
    
    log_critical_infrastructure(full_message, "DATABASE", send_alert=True)

def log_critical_security(event, ip=None, user_id=None, details=None):
    """Log cho security incidents critical"""
    load_dotenv()
    
    context = []
    if ip:
        context.append(f"IP:{ip}")
    if user_id:
        context.append(f"User:{user_id}")
    if details:
        context.append(f"Details:{details}")
    
    context_str = " | " + " | ".join(context) if context else ""
    message = f"SECURITY INCIDENT: {event}{context_str}"
    log_critical_infrastructure(message, "SECURITY", send_alert=True)

def log_critical_emergency_kill(killed_count, total_connections):
    """Log cho emergency mass connection kill"""
    load_dotenv()
    
    message = f"EMERGENCY: Mass killed {killed_count} database connections\nTotal connections before: {total_connections}\nAction taken to prevent system crash"
    log_critical_infrastructure(message, "EMERGENCY", send_alert=True)

def log_critical_service_down(service_name, error_details=None):
    """Log cho service down critical"""
    load_dotenv()
    
    message = f"{service_name} service is DOWN"
    if error_details:
        message += f"\nError: {error_details}"
    log_critical_infrastructure(message, "SERVICE", send_alert=True)



def log_make_repayment_message(message):
    now_date = datetime.datetime.now()
    new_filename = now_date.strftime("%d-%m-%Y")
    custom_handler = None  # Khởi tạo biến custom_handler
    try:
        custom_handler = handlers.RotatingFileHandler(
            "logs/repayment-{0}.log".format(new_filename),
            backupCount=14,
            encoding="utf-8",
        )
        custom_handler.setLevel(logging.INFO)
        custom_handler.setFormatter(formatter)

        custom_logger = logging.getLogger("RepaymentLogger")
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
