import json

import pika
from app.config import settings

from shared.models.video import Video


def publish_video_uploaded(video: Video):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=settings.RABBITMQ_HOST)
    )

    channel = connection.channel()
    channel.queue_declare(
        queue=settings.VIDEO_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": settings.VIDEO_DLX,
            "x-dead-letter-routing-key": settings.VIDEO_FAILED_ROUTING_KEY,
        },
    )

    message = {"video_id": str(video.id), "retry_count": 0}
    channel.basic_publish(
        exchange="",
        routing_key="video.processing",
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2),
    )

    connection.close()
