import json

import pika
from constants import EVENT_QUEUE


def publish_event(
    channel,
    event_type: str,
    video_id: str,
    user_id: str | None = None,
):
    payload = {
        "event": event_type,
        "video_id": video_id,
        "user_id": user_id,
    }

    channel.basic_publish(
        exchange="",
        routing_key=EVENT_QUEUE,
        body=json.dumps(payload),
        properties=pika.BasicProperties(
            delivery_mode=2,
        ),
    )
