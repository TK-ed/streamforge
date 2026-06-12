import time

import pika
from constants import (DLQ_QUEUE, VIDEO_DLX, VIDEO_FAILED_ROUTING_KEY,
                       VIDEO_QUEUE)
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

    # Exchange first
    channel.exchange_declare(
        exchange=VIDEO_DLX,
        exchange_type="direct",
        durable=True,
    )

    # DLQ
    channel.queue_declare(
        queue=DLQ_QUEUE,
        durable=True,
    )

    channel.queue_bind(
        exchange=VIDEO_DLX,
        queue=DLQ_QUEUE,
        routing_key=VIDEO_FAILED_ROUTING_KEY,
    )

    # Main queue
    channel.queue_declare(
        queue=VIDEO_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": VIDEO_DLX,
            "x-dead-letter-routing-key": VIDEO_FAILED_ROUTING_KEY,
        },
    )

    channel.basic_qos(prefetch_count=1)

    return channel
