import os
import atexit
import time
import logging
from logging import DEBUG

from dotenv import load_dotenv
from flask import Flask
from werkzeug.exceptions import default_exceptions
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.schedules.exchange_facebook_token import exchange_facebook_token
from app.schedules.exchange_instagram_token import exchange_instagram_token
from app.schedules.exchange_thread_token import exchange_thread_token
from app.errors.handler import api_error_handler
from app.extensions import redis_client, db
from app.config import configs as config  # noqa

load_dotenv(override=False)


def schedule_task():
    # Placeholder function for scheduled tasks
    pass


def create_app():
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
    handler = logging.StreamHandler()
    handler.setLevel(DEBUG)
    app.logger.addHandler(handler)
    app.logger.setLevel(DEBUG)
    app.logger.info("Starting scheduler...")


def configure_error_handlers(app):
    for exp in default_exceptions:
        app.register_error_handler(exp, api_error_handler)
    app.register_error_handler(Exception, api_error_handler)


def start_scheduler(app):
    scheduler = BackgroundScheduler()
    one_hour_trigger = CronTrigger(hour="*/1")
    one_day_trigger = CronTrigger(hour="0", minute="0")

    scheduler.add_job(func=schedule_task, trigger=one_hour_trigger, id="one_hour_job")
    scheduler.add_job(
        func=exchange_facebook_token,
        trigger=one_day_trigger,
        id="exchange_facebook_token",
    )
    scheduler.add_job(
        func=exchange_instagram_token,
        trigger=one_day_trigger,
        id="exchange_instagram_token",
    )
    scheduler.add_job(
        func=exchange_thread_token, trigger=one_day_trigger, id="exchange_thread_token"
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
