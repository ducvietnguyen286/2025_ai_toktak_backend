import json
import os
import pika

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST") or "localhost"
RABBITMQ_PORT = os.environ.get("RABBITMQ_PORT") or 5672
RABBITMQ_USER = os.environ.get("RABBITMQ_USER") or "guest"
RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD") or "guest"
RABBITMQ_QUEUE = os.environ.get("RABBITMQ_QUEUE") or "hello"


connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=int(RABBITMQ_PORT),
        credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD),
    )
)
channel = connection.channel()

channel.queue_declare(queue=RABBITMQ_QUEUE)


def send_message(message):

    channel.basic_publish(
        exchange="", routing_key=RABBITMQ_QUEUE, body=json.dumps(message)
    )
    print(f" [x] Sent '{message}'")

    connection.close()
