import pika
import json
import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình kết nối RabbitMQ
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.environ.get("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD", "guest")

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
connection_params = pika.ConnectionParameters(
    host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials
)


def send_facebook_message(message):
    RABBITMQ_QUEUE_FACEBOOK = os.environ.get("RABBITMQ_QUEUE_FACEBOOK", "hello")
    send_message(RABBITMQ_QUEUE_FACEBOOK, message)


def send_tiktok_message(message):
    RABBITMQ_QUEUE_TIKTOK = os.environ.get("RABBITMQ_QUEUE_TIKTOK", "hello")
    send_message(RABBITMQ_QUEUE_TIKTOK, message)


def send_twitter_message(message):
    RABBITMQ_QUEUE_TWITTER = os.environ.get("RABBITMQ_QUEUE_TWITTER", "hello")
    send_message(RABBITMQ_QUEUE_TWITTER, message)


def send_youtube_message(message):
    RABBITMQ_QUEUE_YOUTUBE = os.environ.get("RABBITMQ_QUEUE_YOUTUBE", "hello")
    send_message(RABBITMQ_QUEUE_YOUTUBE, message)


def send_message(queue, message):
    try:
        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()
        channel.queue_declare(queue=queue, durable=True)

        message_body = json.dumps(message)

        channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=2,
            ),
        )
        print(f" [x] Sent '{message}'")
        connection.close()
    except Exception as e:
        print(f"Error sending message: {e}")
