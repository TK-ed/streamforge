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
        object_name = f"uploads/{video_id}/input.mp4"

        logger.info(f"Consumer is consuming video_id:{video_id}")

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

        process_video(video=video, object_name=object_name, db=db)
        video.status = Status.COMPLETED
        db.commit()

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        traceback.print_exc()
        db.rollback()

        retries = data.get("retry_count", 0)

        if retries >= MAX_RETRIES:
            if video:
                video.status = Status.FAILED
                db.commit()

            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        data["retry_count"] = retries + 1

        ch.basic_publish(
            exchange="",
            routing_key=VIDEO_QUEUE,
            body=json.dumps(data),
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)

    finally:
        return
