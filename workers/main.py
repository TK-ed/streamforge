from constants import VIDEO_QUEUE
from consumer import callback
from rabbitmq import (
    create_channel,
    create_connection,
)
from services.logger import logger
from signals import (
    register_signal_handlers,
)

import shared.models.user
import shared.models.video

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
