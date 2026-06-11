import os

from constants import VideoStatus as Status
from services.logger import logger
from services.minio import download_video, upload_hls_thumbnail_video, upload_hls_video
from services.thumbnail import generate_thumbnail
from services.transcoder import generate_hls

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

    input_path = f"/tmp/{video.id}/input.mp4"

    hls_dir = f"/tmp/{video.id}/hls"
    thumbnail_path = f"{hls_dir}/thumbnail.jpg"

    generate_thumbnail(input_path, thumbnail_path)
    generate_hls(input_path, hls_dir)

    upload_hls_video(hls_dir=hls_dir, video_id=str(object_name), logger=logger)
    upload_hls_thumbnail_video(hls_dir=hls_dir, video_id=str(object_name))
    logger.info("Processing completed successfully")
