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


def send_slack_message(text: str, channel: str = None) -> bool:
    """
    Gửi tin nhắn đến Slack channel bằng Slack Bot Token.

    Args:
        text (str): Nội dung tin nhắn.
        channel (str): ID kênh Slack (ví dụ: C0123456789). Nếu không có, lấy từ env.

    Returns:
        bool: True nếu gửi thành công, False nếu lỗi.
    """
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    default_channel = os.environ.get("SLACK_CHANNEL_ID")

    if not slack_token:
        print("❌ Thiếu SLACK_BOT_TOKEN trong biến môi trường.")
        return False

    channel_id = channel or default_channel
    if not channel_id:
        print("❌ Thiếu channel_id (truyền tham số hoặc đặt SLACK_CHANNEL_ID trong .env)")
        return False

    print(channel_id)

    slack_url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {slack_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "channel": channel_id,
        "text": text,
    }

    try:
        response = requests.post(slack_url, headers=headers, json=payload, timeout=10)
        data = response.json()

        if response.status_code == 200 and data.get("ok"):
            return True
        else:
            print(f"⚠️ Gửi Slack thất bại: {data.get('error')}")
            return False

    except Exception as e:
        print(f"❌ Lỗi khi gửi Slack message: {str(e)}")
        return False