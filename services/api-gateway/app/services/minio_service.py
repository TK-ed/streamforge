from io import BytesIO

from app.config import settings
from minio import Minio

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
