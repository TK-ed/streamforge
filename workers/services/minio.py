import os

from minio import Minio
from minio.error import S3Error

from workers.services.logger import logger

# Initialize the client (Correct for Docker-to-Docker networking)
client = Minio(
    "minio:9000",
    access_key="admin",
    secret_key="password123",
    secure=False,
)


def download_video(object_name: str, destination_path: str):
    try:
        logger.info(f"Downloading {object_name} → {destination_path}")

        client.fget_object(
            bucket_name="streamforge",
            object_name=object_name,
            file_path=destination_path,
        )
        logger.info("Download successful")

        return destination_path

    except Exception as e:
        logger.exception(f"MinIO download failed: {e}")
        raise


def upload_hls_video(hls_dir: str, video_id: str, logger):
    upload_prefix = f"hls/{video_id}"
    for root, _, files in os.walk(hls_dir):
        for file in files:
            file_path = os.path.join(root, file)

            object_name = f"{upload_prefix}/{file}"
            # logger.info(f"Uploading {file} → {object_name}")
            client.fput_object("streamforge", object_name, file_path)

    logger.info(f"HLS upload completed for video_id={video_id}")


def upload_hls_thumbnail_video(
    video_id: str,
    hls_dir: str,
):
    thumbnail_path = os.path.join(hls_dir, "thumbnail.jpg")

    object_name = f"hls/{video_id}/thumbnail.jpg"

    client.fput_object(
        "streamforge",
        object_name,
        thumbnail_path,
    )
