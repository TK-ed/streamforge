from uuid import uuid4

from app.core.dependencies import get_current_user
from app.services.minio_service import upload_file
from app.services.rabbitmq_service import publish_video_uploaded
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from shared.db.db import get_db
from shared.models.user import User
from shared.models.video import Video

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


@router.get("/{video_id}")
def get_video(
    video_id: int,
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

    if not video:
        raise HTTPException(
            status_code=404,
            detail="Video not found",
        )

    return video


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file_bytes = await file.read()

    object_name = f"{uuid4()}-{file.filename}"

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

    publish_video_uploaded(video.id)
    print(f"Published video {video.id} to RabbitMQ", flush=True)

    return {
        "id": video.id,
        "filename": video.filename,
        "status": video.status,
    }
