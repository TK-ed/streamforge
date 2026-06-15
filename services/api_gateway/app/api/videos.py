from uuid import uuid4

from app.core.dependencies import get_current_user
from app.services.minio_service import get_file_details, upload_file
from app.services.rabbitmq_service import publish_video_uploaded
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from shared.db.db import get_db
from shared.models.user import User
from shared.models.video import Video
from workers.services.logger import logger

router = APIRouter(
    prefix="/videos",
    tags=["Videos"],
)


@router.get("/videos")
async def get_videos(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    files = db.query(Video).filter(Video.user_id == current_user.id).all()
    return [
        {
            "id": video.id,
            "filename": video.filename,
            "status": video.status,
        }
        for video in files
    ]


@router.get("/{video_id}/stream")
def get_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    video = (
        db.query(Video)
        .filter(
            Video.id == video_id,
            Video.user_id == current_user.id,
        )
        .first()
    )
    test = str(video.id)
    logger.info(f"video: {video}")
    test = f"hls/uploads/{test}/input.mp4/master.m3u8"
    logger.info(f"passing value: {test}")
    if not video:
        raise HTTPException(
            status_code=404,
            detail="Video not found",
        )

    url = get_file_details(test)

    return {"streaming_url": url}


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file_bytes = await file.read()

    video_id = str(uuid4())
    object_name = f"uploads/{video_id}/input.mp4"

    print(object_name)
    existing = (
        db.query(Video)
        .filter(
            Video.user_id == current_user.id,
            Video.filename == file.filename,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="File already uploaded",
        )
    upload_file(
        file_bytes=file_bytes,
        object_name=object_name,
        content_type=file.content_type,
    )

    print("CURRENT USER ID:", current_user.id)
    print("FILE NAME:", file.filename)
    print("CONTENT TYPE:", file.content_type)
    print("SIZE:", len(file_bytes))

    video = Video(
        id=video_id,
        user_id=current_user.id,
        filename=file.filename,
        object_name=object_name,
        content_type=file.content_type,
        size=len(file_bytes),
        status="pending",
    )

    db.add(video)
    db.commit()
    db.refresh(video)

    publish_video_uploaded(video)
    print(f"Published video {video.id} to RabbitMQ", flush=True)
    return {
        "id": video.id,
        "object_name": video.object_name,
        "status": video.status,
    }
