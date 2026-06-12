import os

from constants import VideoStatus as Status
from helpers import create_master_playlist, generate_hls
from services.logger import logger
from services.minio import (download_video, upload_hls_thumbnail_video,
                            upload_hls_video)
from services.thumbnail import generate_thumbnail
from services.transcoder import transcode

from shared.db import db
from shared.models.video import Video
from workers.helpers import verify_download


def process_video(video: Video, object_name: str, db: db):
    try:
        print("🔥🔥🔥 PROCESS_VIDEO ACTIVE NEW BUILD 🔥🔥🔥")

        video.status = Status.PROCESSING
        db.commit()

        video_dir = f"/tmp/{video.id}"
        os.makedirs(video_dir, exist_ok=True)
        destination_path = os.path.join(video_dir, "input.mp4")

        # download
        path = download_video(str(object_name), destination_path)
        if not verify_download(path):
            return

        logger.info(f"File ready at {destination_path}")

        input_path = f"/tmp/{video.id}/input.mp4"

        # thumbnail
        hls_dir = f"/tmp/{video.id}/hls"

        thumbnail_path = f"{hls_dir}/thumbnail.jpg"
        generate_thumbnail(input_path, thumbnail_path)

        # transcode
        renditions_dir = f"/tmp/{video.id}/renditions"
        os.makedirs(renditions_dir, exist_ok=True)

        renditions = transcode(input_path, renditions_dir)
        logger.info("Transcoding completed")

        # generate hls
        logger.info(f"HLS DIR CONTENTS: {os.listdir(hls_dir)}")
        logger.info("🔥 ABOUT TO GENERATE HLS")

        p360 = os.path.join(hls_dir, "360p")
        p720 = os.path.join(hls_dir, "720p")
        p1080 = os.path.join(hls_dir, "1080p")

        os.makedirs(p360, exist_ok=True)
        os.makedirs(p720, exist_ok=True)
        os.makedirs(p1080, exist_ok=True)

        generate_hls(renditions["360p"], p360)
        logger.info(f"360p files: {os.listdir(p360)}")

        generate_hls(renditions["720p"], p720)
        logger.info(f"720p files: {os.listdir(p720)}")

        generate_hls(renditions["1080p"], p1080)
        logger.info(f"1080p files: {os.listdir(p1080)}")

        # master playlist
        master_path = create_master_playlist(hls_dir)
        logger.info(f"MASTER PLAYLIST EXISTS: {os.path.exists(master_path)}")
        logger.info(f"HLS ROOT: {os.listdir(hls_dir)}")

        # upload
        upload_hls_thumbnail_video(hls_dir=hls_dir, video_id=str(object_name))
        upload_hls_video(hls_dir=hls_dir, video_id=str(object_name), logger=logger)

        logger.info("Processing completed successfully")
    except Exception as e:
        logger.exception("❌ PROCESS VIDEO FAILED: %s", str(e))
        raise
