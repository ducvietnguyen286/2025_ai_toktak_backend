import asyncio
import json
import os
from aio_pika import connect_robust, IncomingMessage
from dotenv import load_dotenv
import logging
from flask import Flask
from functools import partial
from werkzeug.exceptions import default_exceptions

load_dotenv(override=False)

from app.lib.logger import logger
from app.errors.handler import api_error_handler
from app.extensions import redis_client, db
from app.config import configs as config
from app.services.link import LinkService
from app.services.post import PostService
from app.third_parties.facebook import FacebookService
from app.third_parties.instagram import InstagramService
from app.third_parties.thread import ThreadService
from app.third_parties.tiktok import TiktokService
from app.third_parties.twitter import TwitterService
from app.third_parties.youtube import YoutubeService

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST") or "localhost"
RABBITMQ_PORT = os.environ.get("RABBITMQ_PORT") or 5672
RABBITMQ_USER = os.environ.get("RABBITMQ_USER") or "guest"
RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD") or "guest"
RABBITMQ_QUEUE = os.environ.get("RABBITMQ_QUEUE") or "hello"


def __config_logging(app):
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("Start Consumer...")


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
        social_post_id = message.get("social_post_id")

        link = LinkService.find_link(link_id)
        post = PostService.find_post(post_id)

        logger.info(f"Send post {post_id} to link {link_id}")
        logger.info(f"Send post to {link.type} of {link.social_type}")

        if not link or not post:
            logger.error("Link or post not found")
            return False

        if link.social_type == "SOCIAL":
            if link.type == "FACEBOOK":
                FacebookService().send_post(
                    post, link, user_id, social_post_id, page_id
                )
            elif link.type == "TELEGRAM":
                # Xử lý cho Telegram nếu cần
                pass
            elif link.type == "X":
                TwitterService().send_post(post, link, user_id, social_post_id)
            elif link.type == "INSTAGRAM":
                InstagramService().send_post(post, link, user_id, social_post_id)
            elif link.type == "YOUTUBE":
                YoutubeService().send_post(post, link, user_id, social_post_id)
            elif link.type == "TIKTOK":
                TiktokService().send_post(post, link, user_id, social_post_id)
            elif link.type == "THREAD":
                ThreadService().send_post(post, link, user_id, social_post_id)
        return True
    except Exception as e:
        logger.error(f"Error send post to link: {str(e)}")
        return False


def process_message_sync(body, app):
    """
    Hàm xử lý message một cách đồng bộ.
    Được chạy bên trong một thread với flask app context.
    """
    try:
        decoded_body = json.loads(body)
        action = decoded_body.get("action")
        if action == "SEND_POST_TO_LINK":
            logger.info(f"Processing SEND_POST_TO_LINK action {decoded_body}")
            message = decoded_body.get("message")
            with app.app_context():
                result = action_send_post_to_link(message)
                return result
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return False


async def on_message(message: IncomingMessage, app):
    """
    Hàm callback bất đồng bộ để xử lý từng message.
    Sử dụng asyncio.to_thread để chạy hàm xử lý đồng bộ trong một thread riêng.
    """
    async with message.process():
        body = message.body.decode()
        print(f"Received message: {body}")
        result = await asyncio.to_thread(process_message_sync, body, app)
        if not result:
            logger.error("Message processing failed")
            # Tùy chọn: có thể thêm xử lý khi message thất bại (requeue, log,...)


async def main():
    RABBITMQ_URL = (
        f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"
    )

    app = create_app()
    connection = await connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    queue = await channel.declare_queue(RABBITMQ_QUEUE, durable=True)

    logger.info("Đang chờ message. Nhấn CTRL+C để dừng.")
    await queue.consume(partial(on_message, app=app), no_ack=False)
    return connection


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    connection = loop.run_until_complete(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    finally:
        loop.run_until_complete(connection.close())
        loop.close()
