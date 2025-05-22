import json
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
import uuid


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
        app.logger.info("Start TEST...")

        user = UserService.find_user(id=1)
        link = LinkService.find_link(id=1)

        thread1 = Thread(target=run_test, args=(app, link, user))
        thread2 = Thread(target=run_test, args=(app, link, user))
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        app.logger.info("End TEST...")


def run_test(app, link, user):
    with app.app_context():
        user_id = user.id

        user_link = UserService.find_user_link(link_id=link.id, user_id=user_id)
        user_link_meta = json.loads(user_link.meta)

        redis_key_done = f"toktak:users:{user_id}:refreshtoken-done:X"
        redis_key_check = f"toktak:users:{user_id}:refresh-token:X"
        unique_value = f"{time.time()}_{user_id}_{uuid.uuid4()}"
        redis_key_check_count = f"toktak:users:{user_id}:logging:X"
        redis_client.rpush(redis_key_check_count, unique_value)
        redis_client.expire(redis_key_check_count, 300)

        is_refresing = redis_client.get(redis_key_check)
        current_time = time.time()
        for i in range(3):
            time.sleep(1)
            count_client = redis_client.llen(
                redis_key_check_count
            )  # Đêm lấy số lượng client đang refresh
            if count_client > 1:  # Nếu có nhiều client đang refresh
                unique_values = redis_client.lrange(
                    redis_key_check_count, 0, -1
                )  # Lấy ra client refresh sau
                if (
                    unique_values and unique_values[-1].decode("utf-8") != unique_value
                ):  # Xác định client refresh sau
                    time.sleep(2)
                    is_refresing = redis_client.get(redis_key_check)
                    if is_refresing:
                        break
                else:
                    is_refresing = redis_client.get(redis_key_check)
            else:
                is_refresing = redis_client.get(redis_key_check)

        check_refresh = is_refresing.decode("utf-8") if is_refresing else None

        if check_refresh:
            current_time = time.time()
            print("is_refresing", current_time, is_refresing)
            while True:
                refresh_done = redis_client.get(redis_key_done)
                refresh_done_str = (
                    refresh_done.decode("utf-8") if refresh_done else None
                )
                if refresh_done_str:
                    redis_client.delete(redis_key_check)
                    redis_client.delete(redis_key_done)
                    current_time = time.time()
                    print("refresh_done", current_time, refresh_done_str)
                    if refresh_done_str == "failled":
                        return False
                    return True
                time.sleep(1)

        redis_client.set(redis_key_check, 1, ex=300)
        current_time = time.time()
        print("processed", current_time, is_refresing)

        time.sleep(3)

        redis_client.set(redis_key_done, "success")
        current_time = time.time()
        print("updated_refresh_done", current_time)


if __name__ == "__main__":
    main()
