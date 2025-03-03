import asyncio
import os
from dotenv import load_dotenv
import logging
from flask import Flask

load_dotenv(override=False)

from app.extensions import redis_client, socketio
from app.config import configs as config
from app.socket_sub import start_redis_subscriber


def __config_logging(app):
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("Start Socket...")


def __init_app(app):
    socketio.init_app(app)
    redis_client.init_app(app)


def create_app():
    config_name = os.environ.get("FLASK_CONFIG") or "develop"
    config_app = config[config_name]
    app = Flask(__name__)
    app.config.from_object(config_app)
    __init_app(app)
    __config_logging(app)

    start_redis_subscriber(app)

    return app


main_loop = asyncio.get_event_loop()


if __name__ == "__main__":
    application = create_app()
    SOCKET_PORT = os.environ.get("SOCKET_PORT") or 5001
    socketio.run(
        application,
        debug=True,
        port=int(SOCKET_PORT) if not isinstance(SOCKET_PORT, int) else 5001,
    )
