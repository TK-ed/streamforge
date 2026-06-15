import json

import pika
from app.config import settings

from shared.models.video import Video
from workers.constants import VideoEvents as EVENT


def publish_video_uploaded(video: Video):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=settings.RABBITMQ_HOST)
    )

    channel = connection.channel()
    channel.queue_declare(
        queue=settings.VIDEO_QUEUE,
        durable=True,
    )

    message = {
        "video_id": str(video.id),
        "retry_count": 0,
        "user_id": str(video.user_id),
        "event": EVENT.VIDEO_PROCESSING_STARTED,
    }
    channel.basic_publish(
        exchange="",
        routing_key="video.processing",
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2),
    )

    connection.close()
