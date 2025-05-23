# coding: utf8

import os
from flask import Flask
from flask_redis import FlaskRedis
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_mongoengine import MongoEngine
from celery import Celery


redis_client = FlaskRedis()
db = SQLAlchemy()

bcrypt = Bcrypt()
jwt = JWTManager()
socketio = SocketIO(async_mode="gevent", cors_allowed_origins="*")
db_mongo = MongoEngine()

celery = None


def make_celery(app: Flask) -> Celery:
    global celery

    celery = Celery(
        app.import_name,
        broker=app.config["CELERY_BROKER_URL"],
        backend=app.config["CELERY_RESULT_BACKEND"],
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
