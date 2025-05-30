import os
from celery import Celery
from dotenv import load_dotenv
from flask import Flask
from app.extensions import redis_client, db

load_dotenv(override=False)

from app.config import configs

config_name = os.environ.get("FLASK_CONFIG") or "develop"
config_app = configs[config_name]


celery_app = Celery(
    "worker",
    broker=config_app.CELERY_BROKER_URL,
    backend=config_app.CELERY_RESULT_BACKEND,
)

celery_app.conf.task_routes = {
    "app.tasks.social_post_tasks.*": {"queue": "social_post"},
}


celery_app.autodiscover_tasks(["app.tasks"])


def make_celery_app():
    flask_app = Flask(__name__)
    flask_app.config.from_object(config_app)

    redis_client.init_app(flask_app)
    db.init_app(flask_app)

    return flask_app
