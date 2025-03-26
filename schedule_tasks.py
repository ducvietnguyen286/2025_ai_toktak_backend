import os
import atexit
import time
import logging
import shutil
from datetime import datetime
from logging import DEBUG
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from flask import Flask
from werkzeug.exceptions import default_exceptions
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.schedules.exchange_facebook_token import exchange_facebook_token
from app.schedules.exchange_instagram_token import exchange_instagram_token
from app.schedules.exchange_thread_token import exchange_thread_token
from app.errors.handler import api_error_handler
from app.extensions import redis_client, db, db_mongo
from app.config import configs as config
from app.models.batch import Batch
from app.models.post import Post
from app.models.notification import Notification
from pytz import timezone

from pathlib import Path

# Load biến môi trường
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)


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
    db_mongo.init_app(app)

    configure_logging(app)
    configure_error_handlers(app)

    return app


def configure_logging(app):
    """Cấu hình logging của Flask với file log theo ngày"""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    log_filename = os.path.join(
        LOG_DIR, f"schedule_tasks-{datetime.now().strftime('%Y-%m-%d')}.log"
    )

    file_handler = RotatingFileHandler(
        log_filename, maxBytes=10 * 1024 * 1024, backupCount=5
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


def cleanup_pending_batches(app):
    """Xóa Batch có process_status = 'PENDING', các Post liên quan và thư mục"""
    with app.app_context():
        try:
            has_more_batches = True

            while has_more_batches:
                with db.session.begin():
                    batches = (
                        Batch.query.filter_by(process_status="PENDING").limit(100).all()
                    )
                    has_more_batches = bool(batches)

                    deleted_batch_ids = []

                    for batch in batches:
                        try:
                            batch_date = batch.created_at.strftime("%Y_%m_%d")

                            Post.query.filter_by(batch_id=batch.id).delete()
                            db.session.delete(batch)
                            deleted_batch_ids.append(batch.id)

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

                db.session.commit()

            if deleted_batch_ids:
                app.logger.info(
                    f"Deleted Batches: {', '.join(map(str, deleted_batch_ids))}"
                )

        except Exception as e:
            app.logger.error(f"Error in cleanup_pending_batches: {str(e)}")


def create_notification_task():
    try:
        app.logger.info("Created a new notification successfully.")
    except Exception as e:
        app.logger.error(f"Error creating notification: {str(e)}")


def start_scheduler(app):
    """Khởi động Scheduler với các công việc theo lịch trình"""
    scheduler = BackgroundScheduler()
    kst = timezone("Asia/Seoul")
    
    every_5_minutes_trigger = CronTrigger(minute='*/5', timezone=kst)
    three_am_kst_trigger = CronTrigger(hour=3, minute=0, timezone=kst)
    every_hour_trigger = CronTrigger(hour="*/1", minute=0)  # Chạy mỗi 1 tiếng

    scheduler.add_job(
        func=lambda: cleanup_pending_batches(app),
        trigger=every_5_minutes_trigger,
        id="cleanup_pending_batches",
    )

    scheduler.add_job(
        func=create_notification_task,
        trigger=every_hour_trigger,
        id="create_notification_task",
    )

    scheduler.add_job(
        func=exchange_facebook_token,
        trigger=three_am_kst_trigger,
        id="exchange_facebook_token",
    )
    scheduler.add_job(
        func=exchange_instagram_token,
        trigger=three_am_kst_trigger,
        id="exchange_instagram_token",
    )
    scheduler.add_job(
        func=exchange_thread_token,
        trigger=three_am_kst_trigger,
        id="exchange_thread_token",
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
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        app.logger.info("Shutting down scheduler...")
        scheduler.shutdown()
