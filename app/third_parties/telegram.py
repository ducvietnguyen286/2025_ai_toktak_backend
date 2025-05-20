import os
import requests
from app.lib.logger import logger


def send_telegram_message(message: str, app=None, parse_mode: str = "Markdown"):
    """
    Gửi tin nhắn đến Telegram Bot

    Args:
        message (str): Nội dung tin nhắn.
        app (Flask app, optional): Để log nếu có.
        parse_mode (str, optional): "Markdown" hoặc "HTML" nếu muốn định dạng tin nhắn.
    """
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not telegram_token or not chat_id:
        if app:
            logger.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env")
        return

    telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"

    try:
        response = requests.post(
            telegram_url,
            data={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode
            },
            timeout=10,
        )
        if response.status_code == 200:
            if app:
                logger.info(f"✅ Sent Telegram message: {message}")
        else:
            if app:
                logger.warning(f"⚠️ Failed to send Telegram message. Response: {response.text}")
    except Exception as e:
        if app:
            logger.error(f"❌ Error sending Telegram message: {str(e)}")
