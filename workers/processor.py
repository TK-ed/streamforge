import os
import time

from constants import VideoStatus as Status
from services.logger import logger
from services.minio import download_video, upload_hls_thumbnail_video, upload_hls_video
from services.thumbnail import generate_thumbnail
from services.transcoder import generate_adaptive_hls

from shared.db import db
from shared.models.video import Video
from workers.helpers import verify_download


def process_video(video: Video, object_name: str, db: db):
    try:
        print("🔥🔥🔥 PROCESS_VIDEO ACTIVE NEW BUILD 🔥🔥🔥")
        start_time = time.perf_counter()

        video.status = Status.PROCESSING
        db.commit()

        video_dir = f"/tmp/{video.id}"
        os.makedirs(video_dir, exist_ok=True)
        destination_path = os.path.join(video_dir, "input.mp4")

        # download

        download_start = time.perf_counter()

        path = download_video(str(object_name), destination_path)
        if not verify_download(path):
            return

        download_time = time.perf_counter() - download_start
        logger.info(f"File ready at {destination_path}")

        input_path = f"/tmp/{video.id}/input.mp4"

        # thumbnail
        hls_dir = f"/tmp/{video.id}/hls"

        thumbnail_path = f"{hls_dir}/thumbnail.jpg"
        generate_thumbnail(input_path, thumbnail_path)

        # transcode
        renditions_dir = f"/tmp/{video.id}/renditions"
        os.makedirs(renditions_dir, exist_ok=True)

        hls_start = time.perf_counter()
        generate_adaptive_hls(
            input_path=input_path,
            output_dir=hls_dir,
        )
        hls_time = time.perf_counter() - hls_start
        logger.info(
            f"Adaptive HLS generation took {time.perf_counter() - hls_time:.2f}s"
        )

        logger.info(f"HLS ROOT: {os.listdir(hls_dir)}")

        # upload
        upload_start = time.perf_counter()
        upload_hls_thumbnail_video(hls_dir=hls_dir, video_id=str(object_name))
        upload_hls_video(hls_dir=hls_dir, video_id=str(object_name), logger=logger)
        upload_time = time.perf_counter() - upload_start

        total_time = time.perf_counter() - start_time

        logger.info(f"""
        PROCESSING BREAKDOWN
        -------------------
        Download   : {download_time:.2f}s
        HLS        : {hls_time:.2f}s
        Upload     : {upload_time:.2f}s
        Total      : {total_time:.2f}s
        """)

    except Exception as e:
        logger.exception("❌ PROCESS VIDEO FAILED: %s", str(e))
        raise
