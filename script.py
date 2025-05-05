import os
import time
from dotenv import load_dotenv
import logging
from flask import Flask
from werkzeug.exceptions import default_exceptions

from app.services.link import LinkService
from app.services.notification import NotificationServices
from app.services.user import UserService
import const

load_dotenv(override=False)

from app.errors.handler import api_error_handler
from app.extensions import redis_client, db, db_mongo
from app.config import configs as config
from threading import Thread


def __config_logging(app):
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("Start TEST...")


def __init_app(app):
    db.init_app(app)
    redis_client.init_app(app)
    db_mongo.init_app(app)


def __config_error_handlers(app):
    for exp in default_exceptions:
        app.register_error_handler(exp, api_error_handler)
    app.register_error_handler(Exception, api_error_handler)


def create_app():
    config_name = os.environ.get("FLASK_CONFIG") or "develop"
    config_app = config[config_name]
    app = Flask(__name__)
    app.config.from_object(config_app)
    __init_app(app)
    __config_logging(app)
    __config_error_handlers(app)
    return app


def main():
    app = create_app()
    with app.app_context():
        app.logger.info("Start Script...")
        users = UserService.all_users()
        links = LinkService.get_all_links()
        x_link = None
        for link in links:
            if link.get("type") == "X":
                x_link = link
                break
        for user in users:
            user_link = UserService.find_user_link(user.get("id"), x_link.get("id"))
            if user_link:
                UserService.delete_user_link(user_link_id=user_link.id)
                NotificationServices.create_notification(
                    user_id=user.get("id"),
                    title=f"🔒 X 계정의 토큰이 만료됐어요!",
                    description="🔗 계속 사용하시려면 X 계정을 다시 연결해 주세요. 😊",
                    description_korea="🔗 계속 사용하시려면 X 계정을 다시 연결해 주세요. 😊",
                )


if __name__ == "__main__":
    main()
