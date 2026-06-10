import json
import time
import traceback

from constants import MAX_RETRIES, VIDEO_QUEUE, VideoStatus
from db import SessionLocal
from processor import process_video
from services.logger import logger

from shared.models.video import Video
from shared.schemas.video_status import VideoStatus as Status


def callback(
    ch,
    method,
    properties,
    body,
):
    db = SessionLocal()

    try:
        data = json.loads(body)

        video_id = data["video_id"]

        logger.info(f"Consumer is consuming{body}")

        retries = data.get(
            "retry_count",
            0,
        )

        video = db.query(Video).filter(Video.id == video_id).first()

        if not video:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.warning(
                "Video %s not found",
                video_id,
            )
            return

        process_video(
            db=db,
            video=video,
        )
        video.status = Status.COMPLETED
        db.commit()

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception:
        traceback.print_exc()
        db.rollback()

        if retries >= MAX_RETRIES:
            if video:
                video.status = VideoStatus.FAILED
                db.commit()

            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        data["retry_count"] = MAX_RETRIES + 1

        time.sleep(2**MAX_RETRIES)

        ch.basic_publish(
            exchange="",
            routing_key=VIDEO_QUEUE,
            body=json.dumps(data),
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)

    finally:
        db.close()
