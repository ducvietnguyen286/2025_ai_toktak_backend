import json
import os
import asyncio
import aio_pika
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST") or "localhost"
RABBITMQ_PORT = os.environ.get("RABBITMQ_PORT") or 5672
RABBITMQ_USER = os.environ.get("RABBITMQ_USER") or "guest"
RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD") or "guest"
RABBITMQ_QUEUE = os.environ.get("RABBITMQ_QUEUE") or "hello"

RABBITMQ_URL = (
    f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}"
)


async def create_connection():
    # Kết nối robust giúp tự động tái kết nối khi cần
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    # Khai báo queue với durable=True để queue được lưu lại sau restart broker
    await channel.declare_queue(RABBITMQ_QUEUE, durable=True)
    return connection, channel


async def send_message(message):
    connection, channel = await create_connection()

    message_body = json.dumps(message)
    # Tạo message với delivery_mode persistent để message được lưu lại
    msg = aio_pika.Message(
        body=message_body.encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT
    )

    # Gửi message đến default exchange với routing_key là tên queue
    await channel.default_exchange.publish(msg, routing_key=RABBITMQ_QUEUE)
    print(f" [x] Sent '{message}'")
    await connection.close()
