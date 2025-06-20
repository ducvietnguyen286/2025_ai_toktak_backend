# coding: utf8
import os


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or "<your secret key>"
    API_URL = os.environ.get("API_URL") or "<your api url>"
    CHATGPT_API_KEY = os.environ.get("CHATGPT_API_KEY") or "<your chatgpt api key>"
    MAXIMUM_USER_API = 3

    REDIS_URL = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"

    SQLALCHEMY_DATABASE_URI = "{engine}://{user}:{password}@{host}:{port}/{db}".format(
        engine=os.environ.get("SQLALCHEMY_ENGINE") or "mysql+pymysql",
        user=os.environ.get("SQLALCHEMY_USER") or "root",
        password=os.environ.get("SQLALCHEMY_PASSWORD") or "",
        host=os.environ.get("SQLALCHEMY_HOST") or "127.0.0.1",
        port=int(os.environ.get("SQLALCHEMY_PORT", 3306)),
        db=os.environ.get("SQLALCHEMY_DATABASE") or "toktak",
    )

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 20,  # Giảm từ 200 xuống 20
        "max_overflow": 50,  # Giảm từ 500 xuống 50
        "pool_timeout": 10,  # Giảm từ 30 xuống 10 giây
        "pool_recycle": 900,  # Giảm từ 1800 xuống 900 giây (15 phút)
        "pool_pre_ping": True,  # Kiểm tra connection trước khi sử dụng
    }

    CELERY_BROKER_URL = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"

    MONGODB_DB = os.environ.get("MONGODB_DB") or "toktak"
    MONGODB_HOST = os.environ.get("MONGODB_HOST") or "localhost"
    MONGODB_PORT = int(os.environ.get("MONGODB_PORT") or "27017")
    MONGODB_USERNAME = os.environ.get("MONGODB_USERNAME") or ""
    MONGODB_PASSWORD = os.environ.get("MONGODB_PASSWORD") or ""

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

    PROPAGATE_EXCEPTIONS = os.environ.get("FLASK_CONFIG") == "production"

    CELERY_BROKER_URL = (
        os.environ.get("CELERY_BROKER_URL") or "redis://localhost:6379/0"
    )
    CELERY_RESULT_BACKEND = (
        os.environ.get("CELERY_RESULT_BACKEND") or "redis://localhost:6379/0"
    )


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
