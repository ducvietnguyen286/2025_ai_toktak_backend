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

from app.consumer.crawl_advance import CrawlAdvance

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path, override=True)

from app.lib.logger import log_advance_run_crawler_message
from app.errors.handler import api_error_handler
from app.extensions import redis_client, db
from app.config import configs as config
from app.services.batch import BatchService

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST") or "localhost"
RABBITMQ_PORT = os.environ.get("RABBITMQ_PORT") or 5672
RABBITMQ_USER = os.environ.get("RABBITMQ_USER") or "guest"
RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD") or "guest"
RABBITMQ_QUEUE_RUN_CRAWLER = os.environ.get("RABBITMQ_QUEUE_RUN_CRAWLER") or "crawler"


def __config_logging(app):
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("Start RUN CRAWLER Consumer...")


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


def action_run_crawler(message, app):
    try:
        batch_id = message.get("batch_id")
        data = message.get("data")
        url = data.get("input_url")
        CrawlAdvance(batch_id, url).crawl_advance(app)
        return True
    except Exception as e:
        log_advance_run_crawler_message(f"ERROR: Error run crawler: {str(e)}")
        return False


def process_message_sync(body, app):
    """
    Hàm xử lý message một cách đồng bộ.
    Được chạy bên trong một thread với flask app context.
    """
    try:
        decoded_body = json.loads(body)
        action = decoded_body.get("action")
        if action == "RUN_CRAWLER":
            log_advance_run_crawler_message(
                f"Processing RUN_CRAWLER action {decoded_body}"
            )
            message = decoded_body.get("message")
            with app.app_context():
                result = action_run_crawler(message, app)
                return result

        return False
    except Exception as e:
        log_advance_run_crawler_message(f"ERROR: Error processing message: {str(e)}")
        return False


async def process_message_async(body, app):
    """
    Hàm bọc để chạy process_message_sync trong executor, không block event loop.
    """
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, process_message_sync, body, app)
    if not result:
        log_advance_run_crawler_message("ERROR: Message processing failed")
    return result


async def process_message_with_retry(message: IncomingMessage, app, semaphore):
    """
    Xử lý message với retry logic (đã được bao bọc trong hàm process_message_sync).
    Dùng semaphore để giới hạn số lượng tác vụ song song.
    """
    try:
        async with message.process():  # Đảm bảo ACK message khi xử lý xong
            body = message.body.decode()
            log_advance_run_crawler_message(f"Received message: {body}")
            try:
                async with semaphore:
                    result = await process_message_async(body, app)
                return result
            except Exception as e:
                log_advance_run_crawler_message(
                    f"Message processing failed after retries: {e}"
                )
                return False
    except Exception as e:
        print(f"Lỗi khi vào context: {str(e)}")
        print(f"Loại lỗi: {type(e)}")
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
            log_advance_run_crawler_message("Connected to RabbitMQ successfully.")
            return connection
        except Exception as e:
            attempt += 1
            log_advance_run_crawler_message(f"Connection attempt {attempt} failed: {e}")
            sleep_time = 2**attempt + random.uniform(0, 1)
            await asyncio.sleep(sleep_time)
    raise Exception("Max retry attempts reached. Failed to connect to RabbitMQ.")


async def on_message(message: IncomingMessage, app, semaphore):
    await process_message_with_retry(message, app, semaphore)


async def main():
    RABBITMQ_URL = (
        f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"
    )

    print(
        f"Connecting to RabbitMQ at {RABBITMQ_URL} with queue {RABBITMQ_QUEUE_RUN_CRAWLER}"
    )

    app = create_app()
    connection = await connect_rabbitmq_with_retry(RABBITMQ_URL)
    channel = await connection.channel()
    queue = await channel.declare_queue(RABBITMQ_QUEUE_RUN_CRAWLER, durable=True)

    semaphore = asyncio.Semaphore(50)

    log_advance_run_crawler_message("Đang chờ message. Nhấn CTRL+C để dừng.")
    await queue.consume(partial(on_message, app=app, semaphore=semaphore), no_ack=False)

    return connection


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    connection = loop.run_until_complete(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        log_advance_run_crawler_message("ERROR: Consumer stopped by user")
    finally:
        loop.run_until_complete(connection.close())
        loop.close()
