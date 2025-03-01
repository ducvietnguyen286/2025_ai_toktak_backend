# coding: utf8
import os
from datetime import timedelta


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or "<your secret key>"
    API_URL = os.environ.get("API_URL") or "<your api url>"
    CHATGPT_API_KEY = os.environ.get("CHATGPT_API_KEY") or "<your chatgpt api key>"
    MAXIMUM_USER_API = 3

    REDIS_URL = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"

    SQLALCHEMY_DATABASE_URI = "{engine}://{user}:{password}@{host}:{port}/{db}".format(
        engine=os.environ.get("SQLALCHEMY_ENGINE") or "mysql+pymysql",
        user=os.environ.get("SQLALCHEMY_USER") or "<your sql username>",
        password=os.environ.get("SQLALCHEMY_PASSWORD") or "<your sql password>",
        host=os.environ.get("SQLALCHEMY_HOST") or "<your sql host",
        port=os.environ.get("SQLALCHEMY_PORT") or "<your sql port>",
        db=os.environ.get("SQLALCHEMY_DATABASE") or "<your sql database>",
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or "secret"
    JWT_ACCESS_TOKEN_EXPIRES = False  # timedelta(days=90)
    JWT_REFRESH_TOKEN_EXPIRES = False  # timedelta(days=7)

    MAX_COUNT_IMAGE = os.environ.get("MAX_COUNT_IMAGE") or 8
    
    RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST") or "localhost"
    RABBITMQ_PORT = os.environ.get("RABBITMQ_PORT") or 5672
    RABBITMQ_USER = os.environ.get("RABBITMQ_USER") or "guest"
    RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD") or "guest"
    RABBITMQ_QUEUE = os.environ.get("RABBITMQ_QUEUE") or "hello"


class TestingConfig(Config):
    TESTING = True


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


configs = {
    "develop": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
