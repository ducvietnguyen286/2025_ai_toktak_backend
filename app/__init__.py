# coding: utf8
from logging import DEBUG

from werkzeug.exceptions import default_exceptions

from .errors.handler import api_error_handler

from flask import Flask
from flask_cors import CORS
from .extensions import redis_client


def create_app(config_app):
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(config_app)
    __init_app(app)
    __config_logging(app)
    __register_blueprint(app)
    __config_error_handlers(app)
    return app


def __config_logging(app):
    app.logger.setLevel(DEBUG)
    app.logger.info('Start flask...')


def __register_blueprint(app):
    from app.api import bp as api_bp
    app.register_blueprint(api_bp)


def __init_app(app):
    redis_client.init_app(app)


def __config_error_handlers(app):
    for exp in default_exceptions:
        app.register_error_handler(exp, api_error_handler)
    app.register_error_handler(Exception, api_error_handler)
