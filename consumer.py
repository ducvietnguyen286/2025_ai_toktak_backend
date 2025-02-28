import json
import os
import time
import pika
from logging import DEBUG

from dotenv import load_dotenv
from flask import Flask
from werkzeug.exceptions import default_exceptions

from app.lib.logger import logger

load_dotenv(override=False)

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


def connect_to_rabbitmq():
    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=int(RABBITMQ_PORT),
            credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD),
        )
    )


def action_send_post_to_link(message):
    try:
        link_id = message.get("link_id")
        post_id = message.get("post_id")
        page_id = message.get("page_id")
        social_post_id = message.get("social_post_id")

        link = LinkService.find_link(link_id)
        post = PostService.find_post(post_id)

        print(f"Send post {post_id} to link {link_id}")

        print(f"Send post to {link.type} of {link.social_type}")

        if not link or not post:
            print("Link or post not found")
            return

        if link.social_type == "SOCIAL":

            if link.type == "FACEBOOK":
                FacebookService().send_post(post, link, social_post_id, page_id)

            if link.type == "TELEGRAM":
                pass

            if link.type == "X":
                TwitterService().send_post(post, link, social_post_id)

            if link.type == "INSTAGRAM":
                InstagramService().send_post(post, link, social_post_id)

            if link.type == "YOUTUBE":
                YoutubeService().send_post(post, link, social_post_id)

            if link.type == "TIKTOK":
                TiktokService().send_post(post, link, social_post_id)

            if link.type == "THREAD":
                ThreadService().send_post(post, link, social_post_id)

        return True
    except Exception as e:
        logger.error(f"Error send post to link: {str(e)}")
        return False


def start_consumer():
    config_name = os.environ.get("FLASK_CONFIG") or "develop"
    config_app = config[config_name]

    app = Flask(__name__)
    app.config.from_object(config_app)
    __init_app(app)
    __config_logging(app)
    __config_error_handlers(app)

    connection = connect_to_rabbitmq()
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE)

    def callback(ch, method, properties, body):
        logger.info(f" [x] Received {body}")
        with app.app_context():
            try:
                decoded_body = json.loads(body)
                action = decoded_body.get("action")
                message = decoded_body.get("message")
                if action == "SEND_POST_TO_LINK":
                    action_send_post_to_link(message)
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")

    channel.basic_consume(
        queue=RABBITMQ_QUEUE, on_message_callback=callback, auto_ack=True
    )

    logger.info(" [*] Waiting for messages. To exit press CTRL+C")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.error("Consumer stopped by user")
    except Exception as e:
        logger.error(f"Consumer stopped due to error: {str(e)}")
    finally:
        connection.close()


def __config_logging(app):
    app.logger.setLevel(DEBUG)
    app.logger.info("Start Consumer...")


def __init_app(app):
    db.init_app(app)
    redis_client.init_app(app)


def __config_error_handlers(app):
    for exp in default_exceptions:
        app.register_error_handler(exp, api_error_handler)
    app.register_error_handler(Exception, api_error_handler)


if __name__ == "__main__":
    while True:
        try:
            start_consumer()
        except Exception as e:
            print(f"Error in consumer: {str(e)}")
            time.sleep(5)  # Wait for 5 seconds before reconnecting
