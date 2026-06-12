import os

from minio import Minio

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

            relative_path = os.path.relpath(file_path, hls_dir)

            object_name = f"{upload_prefix}/{relative_path}"

            logger.info(f"Uploading {file_path} → {object_name}")

            try:
                client.fput_object("streamforge", object_name, file_path)
                logger.info(f"UPLOADED: {object_name}")
            except Exception as e:
                logger.error(f"UPLOAD FAILED {object_name}: {e}")
                raise

    logger.info(f"HLS upload completed for video_id={video_id}")


def upload_hls_thumbnail_video(
    video_id: str,
    hls_dir: str,
):
    thumbnail_path = os.path.join(hls_dir, "thumbnail.jpg")

    object_name = f"hls/{video_id}/thumbnail.jpg"

    try:
        client.fput_object(
            "streamforge",
            object_name,
            thumbnail_path,
        )
    except Exception as e:
        logger.error(f"UPLOAD FAILED {object_name}: {e}")
        raise
