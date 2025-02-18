# coding: utf8
import os


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or "<your secret key>"
    API_URL = os.environ.get("API_URL") or "<your api url>"
    CHATGPT_API_KEY = os.environ.get("CHATGPT_API_KEY") or "<your chatgpt api key>"
    MAXIMUM_USER_API = 3


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
