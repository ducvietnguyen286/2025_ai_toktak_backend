import asyncio
import json
import os
import random
from aio_pika import connect_robust, IncomingMessage
from dotenv import load_dotenv
import logging
from flask import Flask
from functools import partial
from werkzeug.exceptions import default_exceptions

load_dotenv(override=False)

from app.lib.logger import log_facebook_message
from app.errors.handler import api_error_handler
from app.extensions import redis_client, db
from app.config import configs as config
from app.services.link import LinkService
from app.services.post import PostService
from app.third_parties.facebook import FacebookService

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST") or "localhost"
RABBITMQ_PORT = os.environ.get("RABBITMQ_PORT") or 5672
RABBITMQ_USER = os.environ.get("RABBITMQ_USER") or "guest"
RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD") or "guest"
RABBITMQ_QUEUE_FACEBOOK = os.environ.get("RABBITMQ_QUEUE_FACEBOOK") or "hello"


def __config_logging(app):
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("Start FACEBOOK Consumer...")


def __init_app(app):
    db.init_app(app)
    redis_client.init_app(app)


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


def action_send_post_to_link(message):
    try:
        link_id = message.get("link_id")
        post_id = message.get("post_id")
        user_id = message.get("user_id")
        page_id = message.get("page_id")
        sync_id = message.get("sync_id")
        social_post_id = message.get("social_post_id")
        is_all = message.get("is_all")

        link = LinkService.find_link(link_id)
        post = PostService.find_post(post_id)

        log_facebook_message(f"Received message: {message}")

        if not link or not post:
            log_facebook_message("Link or post not found")
            return False

        if link.social_type == "SOCIAL":
            if link.type == "FACEBOOK":
                FacebookService(sync_id=sync_id).send_post(
                    post, link, user_id, social_post_id, page_id, is_all=True
                )
        return True
    except Exception as e:
        log_facebook_message(f"Error send post to link: {str(e)}")
        db.session.rollback()
        return False
    finally:
        db.session.remove()  # CRITICAL: Cleanup session để tránh connection leak
        db.session.close()


def process_message_sync(body, app):
    """
    Hàm xử lý message một cách đồng bộ.
    Được chạy bên trong một thread với flask app context.
    """
    try:
        decoded_body = json.loads(body)
        action = decoded_body.get("action")
        if action == "SEND_POST_TO_LINK":
            log_facebook_message(f"Processing SEND_POST_TO_LINK action {decoded_body}")
            message = decoded_body.get("message")
            with app.app_context():
                result = action_send_post_to_link(message)
                return result

        return False
    except Exception as e:
        log_facebook_message(f"ERROR: Error processing message: {str(e)}")
        return False


async def process_message_async(body, app):
    """
    Hàm bọc để chạy process_message_sync trong executor, không block event loop.
    """
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, process_message_sync, body, app)
    if not result:
        log_facebook_message("ERROR: Message processing failed")
    return result


async def process_message_with_retry(message: IncomingMessage, app, semaphore):
    """
    Xử lý message với retry logic (đã được bao bọc trong hàm process_message_sync).
    Dùng semaphore để giới hạn số lượng tác vụ song song.
    """
    async with message.process():  # Đảm bảo ACK message khi xử lý xong
        body = message.body.decode()
        log_facebook_message(f"Received message: {body}")
        try:
            async with semaphore:
                result = await process_message_async(body, app)
            return result
        except Exception as e:
            log_facebook_message(f"Message processing failed after retries: {e}")
            return False


async def connect_rabbitmq_with_retry(rabbitmq_url, max_attempts=5):
    """
    Kết nối đến RabbitMQ với retry logic.
    Nếu kết nối thất bại, sẽ cố gắng kết nối lại theo exponential backoff.
    """
    attempt = 0
    while attempt < max_attempts:
        try:
            connection = await connect_robust(
                rabbitmq_url, heartbeat=60, timeout=10, reconnect_interval=5
            )
            log_facebook_message("Connected to RabbitMQ successfully.")
            return connection
        except Exception as e:
            attempt += 1
            log_facebook_message(f"Connection attempt {attempt} failed: {e}")
            sleep_time = 2**attempt + random.uniform(0, 1)
            await asyncio.sleep(sleep_time)
    raise Exception("Max retry attempts reached. Failed to connect to RabbitMQ.")


async def on_message(message: IncomingMessage, app, semaphore):
    await process_message_with_retry(message, app, semaphore)


async def main():
    RABBITMQ_URL = (
        f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"
    )

    app = create_app()
    connection = await connect_rabbitmq_with_retry(RABBITMQ_URL)
    channel = await connection.channel()
    queue = await channel.declare_queue(RABBITMQ_QUEUE_FACEBOOK, durable=True)

    semaphore = asyncio.Semaphore(20)

    log_facebook_message("Đang chờ message. Nhấn CTRL+C để dừng.")
    await queue.consume(partial(on_message, app=app, semaphore=semaphore), no_ack=False)
    return connection


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    connection = loop.run_until_complete(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        log_facebook_message("Consumer stopped by user")
    finally:
        loop.run_until_complete(connection.close())
        loop.close()
