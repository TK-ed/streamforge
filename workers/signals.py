import signal
import sys

from services.logger import logger


def register_signal_handlers(
    channel,
    connection,
):
    def shutdown(sig, frame):
        logger.info("Shutdown signal received")
        try:
            channel.stop_consuming()
        except Exception:
            pass

        try:
            connection.close()
        except Exception:
            pass

        sys.exit(0)

    signal.signal(
        signal.SIGTERM,
        shutdown,
    )

    signal.signal(
        signal.SIGINT,
        shutdown,
    )
