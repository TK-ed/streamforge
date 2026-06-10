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

        # objects = client.list_objects("streamforge", recursive=True)

        # for obj in objects:
        #     print(obj.object_name)

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
