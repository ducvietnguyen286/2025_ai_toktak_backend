import aio_pika
import json
import os
import asyncio
import random
from app.lib.logger import logger

# Cấu hình kết nối RabbitMQ
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.environ.get("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD", "guest")

RABBITMQ_URL = (
    f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"
)


async def connect_with_retry(max_attempts=5):
    """
    Kết nối đến RabbitMQ với retry logic.
    Nếu kết nối thất bại, sẽ cố gắng kết nối lại theo exponential backoff.
    """
    attempt = 0
    while attempt < max_attempts:
        try:
            connection = await aio_pika.connect_robust(
                RABBITMQ_URL, heartbeat=60, timeout=10, reconnect_interval=5
            )
            logger.info("Connected to RabbitMQ successfully")
            return connection
        except Exception as e:
            attempt += 1
            logger.error(f"Connection attempt {attempt} failed: {e}")
            if attempt == max_attempts:
                raise Exception(
                    f"Failed to connect to RabbitMQ after {max_attempts} attempts: {e}"
                )
            sleep_time = 2**attempt + random.uniform(0, 1)
            await asyncio.sleep(sleep_time)


async def send_message(queue: str, message: dict):
    """
    Gửi message đến queue với retry logic.
    """
    try:
        logger.info(f"Attempting to send message to queue [{queue}]")
        connection = await connect_with_retry()

        async with connection:
            channel = await connection.channel()
            await channel.declare_queue(queue, durable=True)

            message_body = json.dumps(message).encode()
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=message_body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=queue,
            )
            logger.info(f"Successfully sent message to [{queue}]: {message}")
            return True
    except Exception as e:
        logger.error(f"Error sending message to {queue}: {e}")
        return False


async def send_run_crawler_message(message):
    queue = os.environ.get("RABBITMQ_QUEUE_RUN_CRAWLER", "hello")
    await send_message(queue, message)


async def send_create_content_message(message):
    queue = os.environ.get("RABBITMQ_QUEUE_CREATE_CONTENT", "hello")
    await send_message(queue, message)


async def send_facebook_message(message):
    queue = os.environ.get("RABBITMQ_QUEUE_FACEBOOK", "hello")
    await send_message(queue, message)


async def send_tiktok_message(message):
    queue = os.environ.get("RABBITMQ_QUEUE_TIKTOK", "hello")
    await send_message(queue, message)


async def send_twitter_message(message):
    queue = os.environ.get("RABBITMQ_QUEUE_TWITTER", "hello")
    await send_message(queue, message)


async def send_youtube_message(message):
    queue = os.environ.get("RABBITMQ_QUEUE_YOUTUBE", "hello")
    await send_message(queue, message)


async def send_thread_message(message):
    queue = os.environ.get("RABBITMQ_QUEUE_THREAD", "hello")
    await send_message(queue, message)


async def send_instagram_message(message):
    queue = os.environ.get("RABBITMQ_QUEUE_INSTAGRAM", "hello")
    await send_message(queue, message)
