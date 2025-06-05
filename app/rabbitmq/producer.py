import aio_pika
import json
import os

# Cấu hình kết nối RabbitMQ
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.environ.get("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD", "guest")

RABBITMQ_URL = (
    f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"
)


async def send_message(queue: str, message: dict):
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
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
            print(f" [x] Sent to [{queue}]: {message}")
    except Exception as e:
        print(f"Error sending message to {queue}: {e}")


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
