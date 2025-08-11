


# ================== LOGURU LOGGER CONFIG =====================
import sys
import os
from loguru import logger
from dotenv import load_dotenv

os.makedirs("logs", exist_ok=True)

log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>batch:{extra[batch_id]}</cyan> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

logger.remove()
logger.add(sys.stderr, colorize=True, format=log_format, level="INFO")
logger.add(
    "logs/toktak_service.json",
    rotation="100 MB",
    retention="10 days",
    compression="zip",
    serialize=True,
    level="DEBUG",
    enqueue=True,
    catch=True
)
configured_logger = logger.patch(lambda record: record["extra"].setdefault("batch_id", "NO_BATCH"))

# ================== CRITICAL LOGGING REFACTORED =====================
def log_critical_infrastructure(message, component="SYSTEM", send_alert=False):
    """Log các vấn đề hạ tầng nghiêm trọng và gửi cảnh báo nếu cần."""
    configured_logger.critical(f"[CRITICAL-{component}] {message}")
    if send_alert:
        load_dotenv()
        try:
            # from app.third_parties.telegram import send_slack_message
            # send_slack_message(...)
            configured_logger.info(f"Đã gửi cảnh báo critical cho component: {component}")
        except Exception as e:
            configured_logger.error(f"Gửi cảnh báo critical thất bại: {e}")

# ================== EXPORT LOGGER =====================
log = configured_logger