import time

import pika

from constants import (
    EVENT_QUEUE,
    VIDEO_QUEUE,
)
from services.logger import logger


def create_connection():
    while True:
        try:
            logger.info("RabbitMQ tryna connect")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host="rabbitmq",
                    heartbeat=600,
                    blocked_connection_timeout=300,
                )
            )

            return connection

        except Exception as e:
            logger.error(
                "RabbitMQ unavailable: %s",
                e,
            )

            time.sleep(5)


def create_channel(connection):
    channel = connection.channel()

    # Main queue
    channel.queue_declare(
        queue=VIDEO_QUEUE,
        durable=True,
    )

    # Event queue
    channel.queue_declare(
        queue=EVENT_QUEUE,
        durable=True,
    )

    channel.basic_qos(prefetch_count=1)

    return channel
