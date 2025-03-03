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
RABBITMQ_QUEUE = os.environ.get("RABBITMQ_QUEUE", "hello")

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
connection_params = pika.ConnectionParameters(
    host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials
)


def send_message(message):
    try:
        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=False)

        message_body = json.dumps(message)

        channel.basic_publish(
            exchange="",
            routing_key=RABBITMQ_QUEUE,
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=2,
            ),
        )
        print(f" [x] Sent '{message}'")
        connection.close()
    except Exception as e:
        print(f"Error sending message: {e}")
