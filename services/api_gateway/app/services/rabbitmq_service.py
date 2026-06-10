import json

import pika
from app.config import settings


def publish_video_uploaded(video_id: int):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=settings.RABBITMQ_HOST)
    )

    channel = connection.channel()

    channel.basic_publish(
        exchange="",
        routing_key="video_uploaded",
        body=json.dumps({"video_id": video_id}),
        properties=pika.BasicProperties(delivery_mode=2),
    )

    connection.close()
