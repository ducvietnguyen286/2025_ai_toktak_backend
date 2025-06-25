import os
import atexit
import time
import logging
import shutil
from datetime import datetime, timedelta
from logging import DEBUG
from logging.handlers import TimedRotatingFileHandler

from pathlib import Path
from dotenv import load_dotenv

# Load biến môi trường
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

from app.config import configs as config


from flask import Flask
from werkzeug.exceptions import default_exceptions
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.schedules.exchange_facebook_token import exchange_facebook_token
from app.schedules.exchange_instagram_token import exchange_instagram_token
from app.schedules.exchange_thread_token import exchange_thread_token
from app.errors.handler import api_error_handler
from app.extensions import redis_client, db
from app.models.batch import Batch
from app.models.post import Post
from app.models.notification import Notification
from app.services.user import UserService
from app.services.auth import AuthService
from pytz import timezone
import requests

import const

from app.services.notification import NotificationServices
from app.models.notification import Notification
from app.models.request_log import RequestLog
from app.models.request_social_log import RequestSocialLog
from app.models.video_create import VideoCreate

from app.ais.chatgpt import (
    translate_notifications_batch,
)
from sqlalchemy import or_, text

from app.third_parties.telegram import send_telegram_message, send_slack_message


UPLOAD_BASE_PATH = "uploads"
VOICE_BASE_PATH = "static/voice/gtts_voice"
LOG_DIR = "logs"


def create_app():
    """Khởi tạo Flask app"""
    config_name = os.environ.get("FLASK_CONFIG", "develop")
    config_app = config.get(config_name, config["develop"])

    app = Flask(__name__)
    app.config.from_object(config_app)

    db.init_app(app)
    redis_client.init_app(app)

    configure_logging(app)
    configure_error_handlers(app)

    return app


def configure_logging(app):
    """Cấu hình logging để tự động ghi log theo ngày (hàng ngày tạo file mới)"""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    log_filename = os.path.join(
        LOG_DIR, "schedule_tasks.log"
    )  # Không cần ghi ngày ở đây

    file_handler = TimedRotatingFileHandler(
        log_filename,
        when="midnight",  # Reset mỗi đêm
        interval=1,  # Mỗi 1 ngày
        backupCount=7,  # Giữ tối đa 7 bản log cũ
        encoding="utf-8",
    )
    file_handler.setLevel(DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(DEBUG)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(DEBUG)
    app.logger.info("Start Schedule Tasks...")


def configure_error_handlers(app):
    for exp in default_exceptions:
        app.register_error_handler(exp, api_error_handler)
    app.register_error_handler(Exception, api_error_handler)


def delete_folder_if_exists(folder_path, app):
    """Xóa thư mục nếu tồn tại"""
    try:
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            app.logger.info(f"Deleted folder: {folder_path}")
    except Exception as e:
        app.logger.error(f"Error deleting folder {folder_path}: {str(e)}")


def split_message(text, max_length=4000):
    """Chia tin nhắn thành nhiều đoạn dưới max_length ký tự"""
    return [text[i : i + max_length] for i in range(0, len(text), max_length)]


def format_notification_message(notification_detail, fe_current_domain, user=None):
    email = user.email if user else ""
    now_korea = datetime.now(timezone("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"======================================================================\n"
        f"[{now_korea}] [Toktak Notification {fe_current_domain}]\n"
        f"- User Email: {email}\n"
        f"- Notification ID: {notification_detail.get('id')}\n"
        f"- Batch ID: {notification_detail.get('batch_id')}\n"
        f"- Title: {notification_detail.get('title')}\n"
        f"- Description: {notification_detail.get('description')}\n"
        f"{notification_detail.get('description_korea')}\n"
        f"======================================================================\n"
    )


def send_slack_notifications(app):
    """Gửi Notification đến Slack cho những bản ghi chưa gửi (send_telegram = 0)"""
    app.logger.info("🔔 Start send_slack_notifications...")

    with app.app_context():
        try:
            notifications = (
                db.session.query(Notification)
                .filter(
                    Notification.send_telegram == 0,
                    Notification.status == const.NOTIFICATION_FALSE,
                )
                .order_by(Notification.created_at)
                .limit(10)
                .all()
            )

            if not notifications:
                app.logger.info("✅ No pending notifications to send.")
                return

            fe_current_domain = os.environ.get("FE_DOMAIN") or "http://localhost:5000"

            user_ids = [n.user_id for n in notifications]
            users = UserService.find_users(user_ids)
            user_dict = {user.id: user for user in users}

            for notification in notifications:
                try:
                    # Đánh dấu đã gửi SLACK NGAY và commit, tránh race/trùng
                    notification.send_telegram = 1
                    notification.save()
                    db.session.commit()

                    notification_detail = notification.to_dict()
                    user = user_dict.get(notification.user_id)

                    message = format_notification_message(
                        notification_detail, fe_current_domain, user=user
                    )

                    message_parts = split_message(message)
                    for idx, part in enumerate(message_parts):
                        send_slack_message(part)

                except Exception as single_error:
                    app.logger.error(
                        f"❌ Error sending notification ID {notification.id}: {str(single_error)}"
                    )
                    db.session.rollback()
        except Exception as e:
            app.logger.exception(f"❌ Error in send_slack_notifications: {str(e)}")
        finally:
            db.session.remove()


def translate_notification(app):
    """Gửi Notification đến Telegram cho những bản ghi chưa gửi (send_telegram = 0)"""
    app.logger.info("Start translate_notification...")

    with app.app_context():
        try:
            notifications = (
                db.session.query(Notification)
                .filter(
                    Notification.status == const.NOTIFICATION_FALSE,
                    Notification.description != "",
                    or_(
                        Notification.description_korea == None,
                        Notification.description_korea == "",
                    ),
                )
                .order_by(Notification.id.desc())
                .limit(10)
                .all()
            )

            if not notifications:
                return

            notification_data = [
                {"id": notification.id, "text": notification.description}
                for notification in notifications
            ]

            translated_results = translate_notifications_batch(notification_data)
            if translated_results:
                NotificationServices.update_translated_notifications(translated_results)

        except Exception as e:
            app.logger.error(f"Error in translate_notification: {str(e)}")


def cleanup_pending_batches(app):
    """Xóa Batch có process_status = 'PENDING', các Post liên quan và thư mục"""
    app.logger.info("Begin cleanup_pending_batches.")
    with app.app_context():
        try:
            has_more_batches = True

            while has_more_batches:
                batches = (
                    db.session.query(Batch)
                    .filter(Batch.process_status == "PENDING")
                    .order_by(Batch.created_at.asc())
                    .limit(100)
                    .all()
                )
                has_more_batches = bool(batches)

                deleted_batch_ids = []

                for batch in batches:
                    try:
                        app.logger.info(
                            f"Deleting batch {batch.id} with process_status 'PENDING'"
                        )

                        batch_date = batch.created_at.strftime("%Y_%m_%d")

                        # Delete related posts
                        posts = (
                            db.session.query(Post)
                            .filter(Post.batch_id == batch.id)
                            .all()
                        )
                        for post in posts:
                            post.delete()
                            app.logger.info(
                                f"Deleted post {post.id} related to batch {batch.id}"
                            )

                        batch.delete()

                        upload_folder = os.path.join(
                            UPLOAD_BASE_PATH, batch_date, str(batch.id)
                        )
                        voice_folder = os.path.join(
                            VOICE_BASE_PATH, batch_date, str(batch.id)
                        )
                        delete_folder_if_exists(upload_folder, app)
                        delete_folder_if_exists(voice_folder, app)

                    except Exception as batch_error:
                        app.logger.error(
                            f"Error processing batch {batch.id}: {str(batch_error)}"
                        )
                        db.session.rollback()

            if deleted_batch_ids:
                app.logger.info(
                    f"Deleted Batches: {', '.join(map(str, deleted_batch_ids))}"
                )

            db.session.commit()

        except Exception as e:
            app.logger.error(f"Error in cleanup_pending_batches: {str(e)}")
            db.session.rollback()
        finally:
            # CRITICAL: Cleanup session to prevent connection leaks
            db.session.remove()


def cleanup_request_log(app):
    """Xóa những dữ liệu cũ từ bảng request_logs, chỉ giữ lại 5 ngày gần nhất."""
    app.logger.info("Begin cleanup_request_log.")

    with app.app_context():
        try:
            # Tính ngày giới hạn (5 ngày trước)
            five_days_ago = datetime.now() - timedelta(days=5)
            three_days_ago = datetime.now() - timedelta(days=3)
            # Đếm số bản ghi sẽ xóa
            req_deleted = (
                db.session.query(RequestLog)
                .filter(RequestLog.created_at < five_days_ago)
                .delete(synchronize_session=False)
            )

            # --- RequestSocialLog ---
            social_deleted = (
                db.session.query(RequestSocialLog)
                .filter(RequestSocialLog.created_at < three_days_ago)
                .delete(synchronize_session=False)
            )
            # --- VideoCreate ---
            video_deleted = (
                db.session.query(VideoCreate)
                .filter(VideoCreate.created_at < three_days_ago)
                .delete(synchronize_session=False)
            )

            db.session.commit()
            app.logger.info(
                f"🧹 Đã xóa: {req_deleted} request_logs, {social_deleted} request_social_logs, "
                f"{video_deleted} video_create cũ hơn {five_days_ago.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"❌ Error in cleanup_request_log: {str(e)}")
        finally:
            # CRITICAL: Cleanup session to prevent connection leaks
            db.session.remove()


def check_urls_health(app):
    """Check the health of predefined URLs and send one combined Telegram alert if any fail."""
    app.logger.info("Start checking URL health...")

    # 103.98.152.125
    # 3.38.117.230
    # 43.203.118.116
    # 3.35.172.6

    urls = [
        "https://scraper.vodaplay.vn/ping",
        "https://scraper.play-tube.net/ping",
        "https://scraper.canvasee.com/ping",
        "https://scraper.bodaplay.ai/ping",
    ]

    headers = {"User-Agent": "ToktakHealthChecker/1.0"}
    timeout_sec = 10
    fe_current_domain = os.environ.get("FE_DOMAIN") or "http://localhost:5000"

    failed_reports = []

    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=timeout_sec)
            if response.status_code != 200:
                failed_reports.append(
                    f"⚠️ [URL Check Failed]({url})\nStatus Code: `{response.status_code}`"
                )
        except Exception as e:
            failed_reports.append(f"❌ [URL Unreachable]({url})\nError: `{str(e)}`")

    if failed_reports:
        message = (
            f"*Domain:* `{fe_current_domain}`\n"
            f"*Failed URL Reports:* 🚨\n\n" + "\n\n".join(failed_reports)
        )
        app.logger.warning("Some URLs failed health check.")
        send_slack_message(message)
        # send_telegram_message(message, app, parse_mode="Markdown")
    else:
        app.logger.info("✅ All URLs are healthy.")


def auto_extend_subscription_task(app):
    app.logger.info("Start auto_extend_subscription_task...")
    with app.app_context():
        try:
            count = AuthService.auto_extend_free_subscriptions()
            app.logger.info(f"✓ Auto-extended {count} FREE users")
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Error in auto_extend_subscription_task: {str(e)}")
            db.session.rollback()
        finally:
            # CRITICAL: Cleanup session to prevent connection leaks
            db.session.remove()


def auto_kill_long_connections(app):
    """
    Tự động kill các connections > 60 giây
    Chạy mỗi phút để duy trì connection pool sạch sẽ
    """
    app.logger.info("🔪 Start auto_kill_long_connections...")

    with app.app_context():
        killed_count = 0
        try:
            # Get all sleep connections
            result = db.session.execute(text("SHOW FULL PROCESSLIST")).fetchall()

            sleep_connections = []
            for row in result:
                if len(row) >= 5 and row[4] == "Sleep":
                    connection_info = {
                        "id": row[0],
                        "user": row[1],
                        "host": row[2],
                        "db": row[3],
                        "command": row[4],
                        "time": row[5],
                        "state": row[6] if len(row) > 6 else "",
                        "info": row[7] if len(row) > 7 else "",
                    }
                    sleep_connections.append(connection_info)

            app.logger.info(f"📊 Found {len(sleep_connections)} sleep connections")

            # Kill connections > 100 seconds
            threshold_seconds = 100
            for conn in sleep_connections:
                if conn["time"] > threshold_seconds and conn["user"] == "toktak":
                    try:
                        db.session.execute(text(f"KILL {conn['id']}"))
                        app.logger.info(
                            f"🔪 Killed connection ID {conn['id']} (Sleep {conn['time']}s) from {conn['host']}"
                        )
                        killed_count += 1
                    except Exception as e:
                        app.logger.error(
                            f"❌ Failed to kill connection {conn['id']}: {e}"
                        )

            # Get stats after cleanup
            current_result = db.session.execute(
                text("SHOW STATUS LIKE 'Threads_connected'")
            ).fetchone()
            current_connections = int(current_result[1]) if current_result else 0

            sleep_after = len(
                [
                    conn
                    for conn in sleep_connections
                    if conn["time"] <= threshold_seconds
                ]
            )

            if killed_count > 0:
                app.logger.info(
                    f"✅ Killed {killed_count} long connections. Current: {current_connections}, Sleep remaining: {sleep_after}"
                )

                # Alert if still too many connections
                if sleep_after > 50:
                    alert_msg = (
                        f"⚠️ HIGH SLEEP CONNECTIONS ALERT!\n"
                        f"Killed: {killed_count} connections\n"
                        f"Sleep remaining: {sleep_after}\n"
                        f"Current total: {current_connections}\n"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    app.logger.warning(alert_msg)
                    send_slack_message(alert_msg)
            else:
                app.logger.info(
                    f"✅ No long connections to kill. Current: {current_connections}, Sleep: {len(sleep_connections)}"
                )

        except Exception as e:
            app.logger.error(f"❌ Error in auto_kill_long_connections: {str(e)}")
        finally:
            # CRITICAL: Force cleanup session to prevent connection leaks
            try:
                if db.session.is_active:
                    db.session.rollback()
                db.session.close()
                db.session.remove()
            except:
                pass


def create_notification_task():
    try:
        app.logger.info("Check : Created a new notification successfully.")
    except Exception as e:
        app.logger.error(f"Error creating notification: {str(e)}")


def start_scheduler(app):
    """Khởi động Scheduler với các công việc theo lịch trình"""
    scheduler = BackgroundScheduler()
    kst = timezone("Asia/Seoul")

    every_1_minutes_trigger = CronTrigger(minute="*/1", timezone=kst)
    every_2_minutes_trigger = CronTrigger(minute="*/2", timezone=kst)
    every_5_minutes_trigger = CronTrigger(minute="*/5", timezone=kst)
    one_am_kst_trigger = CronTrigger(hour=1, minute=0, timezone=kst)
    one_30_am_kst_trigger = CronTrigger(hour=1, minute=30, timezone=kst)
    two_am_kst_trigger = CronTrigger(hour=2, minute=0, timezone=kst)
    three_am_kst_trigger = CronTrigger(hour=3, minute=0, timezone=kst)
    four_am_kst_trigger = CronTrigger(hour=4, minute=0, timezone=kst)
    every_hour_trigger = CronTrigger(hour="*/1", minute=0)  # Chạy mỗi 1 tiếng

    twelve_oh_one_trigger = CronTrigger(hour=0, minute=1, timezone=kst)

    every_3_hours_trigger = CronTrigger(hour="*/3", minute=0, timezone=kst)

    scheduler.add_job(
        func=lambda: check_urls_health(app),
        trigger=every_3_hours_trigger,
        id="check_urls_health",
    )

    scheduler.add_job(
        func=lambda: translate_notification(app),
        trigger=every_2_minutes_trigger,
        id="translate_notification",
    )

    scheduler.add_job(
        func=lambda: send_slack_notifications(app),
        trigger=every_2_minutes_trigger,
        id="send_slack_notifications",
    )

    scheduler.add_job(
        func=lambda: cleanup_pending_batches(app),
        trigger=one_am_kst_trigger,
        id="cleanup_pending_batches",
    )
    scheduler.add_job(
        func=lambda: cleanup_request_log(app),
        trigger=one_30_am_kst_trigger,
        id="cleanup_request_log",
    )

    scheduler.add_job(
        func=lambda: create_notification_task(),
        trigger=every_hour_trigger,
        id="create_notification_task",
    )

    scheduler.add_job(
        func=exchange_facebook_token,
        trigger=two_am_kst_trigger,
        id="exchange_facebook_token",
    )
    scheduler.add_job(
        func=exchange_instagram_token,
        trigger=three_am_kst_trigger,
        id="exchange_instagram_token",
    )
    scheduler.add_job(
        func=exchange_thread_token,
        trigger=four_am_kst_trigger,
        id="exchange_thread_token",
    )

    scheduler.add_job(
        func=lambda: auto_extend_subscription_task(app),
        trigger=twelve_oh_one_trigger,
        id="auto_extend_subscription_task",
    )

    # Auto kill long database connections every minute
    scheduler.add_job(
        func=lambda: auto_kill_long_connections(app),
        trigger=every_1_minutes_trigger,
        id="auto_kill_long_connections",
    )

    atexit.register(lambda: scheduler.shutdown(wait=False))
    scheduler.start()

    app.logger.info("Scheduler started successfully.")
    return scheduler


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        scheduler = start_scheduler(app)

    try:
        app.logger.info("while True loop...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        app.logger.info("Shutting down scheduler...")
        scheduler.shutdown()
