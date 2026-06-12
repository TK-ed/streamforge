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


def get_file_details(object_name: str):
    try:
        obj = client.get_object(settings.BUCKET_NAME, object_name)
        if obj:
            print(f"Got the file: {object_name}")
            hls_streaming_url = f"http://localhost:9000/streamforge/{object_name}"
            return hls_streaming_url
    except Exception as e:
        print(e)
