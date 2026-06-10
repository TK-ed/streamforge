from constants import VideoStatus as Status
from services.logger import logger
from services.minio import StorageService

storage = StorageService()


# def process_video(
#     db,
#     video,
# ):
#     raise Exception("DLQ TEST")


def process_video(db, video):
    logger.info(
        "Processing video %s",
        video,
    )
    video.status = Status.PROCESSING
    db.commit()

    storage.download_video(video.object_name)

    # processing logic
