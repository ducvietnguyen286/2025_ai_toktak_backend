import os
import atexit
import time
from logging import DEBUG

from dotenv import load_dotenv
from flask import Flask

load_dotenv(override=False)

from werkzeug.exceptions import default_exceptions
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.errors.handler import api_error_handler
from app.extensions import redis_client, db
from app.config import configs as config  # noqa


def schedule_task():
    pass


def start_scheduler():
    config_name = os.environ.get("FLASK_CONFIG") or "develop"
    config_app = config[config_name]

    app = Flask(__name__)
    app.config.from_object(config_app)
    __init_app(app)
    __config_logging(app)
    __config_error_handlers(app)

    scheduler = BackgroundScheduler()
    one_hour_trigger = CronTrigger(hour="*/1")

    scheduler.add_job(func=schedule_task, trigger=one_hour_trigger, id="one_hour_job")

    atexit.register(lambda: scheduler.shutdown())

    scheduler.start()


def __config_logging(app):
    app.logger.setLevel(DEBUG)
    app.logger.info("Start schedule...")


def __init_app(app):
    db.init_app(app)
    redis_client.init_app(app)


def __config_error_handlers(app):
    for exp in default_exceptions:
        app.register_error_handler(exp, api_error_handler)
    app.register_error_handler(Exception, api_error_handler)


if __name__ == "__main__":
    start_scheduler()
    while True:
        time.sleep(1)
