# coding: utf8
from logging import DEBUG
import os

from werkzeug.exceptions import default_exceptions

from app.lib.logger import log_mongo_database

from .errors.handler import api_error_handler

from flask import Flask, jsonify
from flask_cors import CORS
from .extensions import redis_client, db, bcrypt, jwt, db_mongo, make_celery
from pymongo import monitoring

from flask_jwt_extended.exceptions import NoAuthorizationError


def create_app(config_app):
    app = Flask(__name__)
    # CORS(app)

    cors_scheme = os.environ.get("CORS_SCHEME") or "*"

    CORS(app, resources={r"/*": {"origins": cors_scheme}})
    app.config.from_object(config_app)
    __init_app(app)
    __config_logging(app)
    __register_blueprint(app)
    __config_error_handlers(app)

    # @app.teardown_appcontext
    # def shutdown_session(exception=None):
    #     db.session.remove()

    @app.route("/admin/persistence/on")
    def persistence_on():
        redis_client.config_set("appendonly", "yes")
        redis_client.config_set("appendfsync", "everysec")
        redis_client.config_set("save", "900 1 300 10 60 10000")
        return jsonify(status="persistence enabled")

    @app.route("/admin/persistence/off")
    def persistence_off():
        # Tắt hoàn toàn persistence (cẩn trọng!)
        redis_client.config_set("appendonly", "no")
        redis_client.config_set("save", "")
        return jsonify(status="persistence disabled")

    return app


def __config_logging(app):
    app.logger.setLevel(DEBUG)
    app.logger.info("Start flask...")


def __register_blueprint(app):
    from app.api import bp as api_bp

    app.register_blueprint(api_bp)


def __init_app(app):
    monitoring.register(CommandLogger())

    db.init_app(app)
    redis_client.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    db_mongo.init_app(app)
    # init_sam_model(app)

    celery = make_celery(app)
    app.extensions["celery"] = celery

    app.logger.info("Initial app...")


def __config_error_handlers(app):
    for exp in default_exceptions:
        app.register_error_handler(exp, api_error_handler)
    app.register_error_handler(Exception, api_error_handler)

    @app.errorhandler(NoAuthorizationError)
    def handle_auth_error(e):
        return (
            jsonify(
                {"status": 401, "sub_status": 44, "msg": "Missing Authorization Header"}
            ),
            401,
        )

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


class CommandLogger(monitoring.CommandListener):
    def started(self, event):
        # log_mongo_database(f"Command: {event.command}")
        pass

    def succeeded(self, event):
        pass

    def failed(self, event):
        # log_mongo_database(
        #     f"Failed command: {event.command_name} with request id {event.request_id} on server {event.connection_id} with error: {event.failure}"
        # )
        pass
