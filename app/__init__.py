# coding: utf8
from logging import DEBUG

from werkzeug.exceptions import default_exceptions

from .errors.handler import api_error_handler

from flask import Flask, jsonify
from flask_cors import CORS
from .extensions import redis_client, db, bcrypt, jwt


def create_app(config_app):
    app = Flask(__name__)
    # CORS(app)
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.config.from_object(config_app)
    __init_app(app)
    __config_logging(app)
    __register_blueprint(app)
    __config_error_handlers(app)
    return app


def __config_logging(app):
    app.logger.setLevel(DEBUG)
    app.logger.info("Start flask...")


def __register_blueprint(app):
    from app.api import bp as api_bp

    app.register_blueprint(api_bp)


def __init_app(app):
    db.init_app(app)
    redis_client.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    app.logger.info("Initial app...")


def __config_error_handlers(app):
    for exp in default_exceptions:
        app.register_error_handler(exp, api_error_handler)
    app.register_error_handler(Exception, api_error_handler)

    @jwt.expired_token_loader
    def expired_token_callback(callback):
        return (
            jsonify({"status": 401, "sub_status": 42, "msg": "The token has expired"}),
            401,
        )

    @jwt.invalid_token_loader
    def invalid_token_callback(callback):
        return jsonify({"status": 401, "sub_status": 43, "msg": "Invalid token"}), 401

    @jwt.unauthorized_loader
    def unauthorized_callback(callback):
        return (
            jsonify(
                {"status": 401, "sub_status": 44, "msg": "Missing Authorization Header"}
            ),
            401,
        )
