from constants import VIDEO_QUEUE
from consumer import callback
from prometheus_client import start_http_server
from rabbitmq import create_channel, create_connection
from services.logger import logger
from signals import register_signal_handlers

from shared.models.user import User  # noqa: F401
from shared.models.video import Video  # noqa: F401

start_http_server(8001)
connection = create_connection()

channel = create_channel(connection)

register_signal_handlers(
    channel,
    connection,
)

channel.basic_consume(
    queue=VIDEO_QUEUE,
    on_message_callback=callback,
)

logger.info("Worker Started")

channel.start_consuming()
