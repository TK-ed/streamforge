import os

from constants import VideoStatus as Status
from services.logger import logger
from services.minio import download_video

from shared.db import db
from shared.models.video import Video
from workers.helpers import verify_download


def process_video(video: Video, object_name: str, db: db):
    logger.info("Processing video %s", video)

    video.status = Status.PROCESSING
    db.commit()

    video_dir = f"/tmp/{video.id}"
    os.makedirs(video_dir, exist_ok=True)

    destination_path = os.path.join(video_dir, "input.mp4")
    path = download_video(str(object_name), destination_path)
    if not verify_download(path):
        return
    logger.info(f"File ready at {destination_path}")
    # processing logic
