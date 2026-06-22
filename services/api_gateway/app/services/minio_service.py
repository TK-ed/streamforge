import os
from io import BytesIO

from minio import Minio

from app.config import settings

client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False,
)


def create_bucket():
    if not client.bucket_exists(settings.BUCKET_NAME):
        client.make_bucket(settings.BUCKET_NAME)


def upload_file(
    file_bytes: bytes,
    object_name: str,
    content_type: str,
):
    client.put_object(
        bucket_name=settings.BUCKET_NAME,
        object_name=object_name,
        data=BytesIO(file_bytes),
        length=len(file_bytes),
        content_type=content_type,
    )


def get_file_details(object_name: str):
    """Return a player-reachable URL for an object, or None if it doesn't exist.

    The public host is configurable so the same code works in Docker Compose
    (localhost:9000) and Kubernetes (the MinIO S3 ingress / port-forward).
    The bucket must allow anonymous download for the HLS playlist + segments
    to be fetched by a player such as VLC.
    """
    public_endpoint = os.getenv(
        "MINIO_PUBLIC_ENDPOINT", "http://localhost:9000"
    ).rstrip("/")

    try:
        # stat_object is a cheap HEAD; get_object opened a stream we never closed.
        client.stat_object(settings.BUCKET_NAME, object_name)
    except Exception as e:
        print(f"Object not found: {object_name} ({e})")
        return None

    return f"{public_endpoint}/{settings.BUCKET_NAME}/{object_name}"
