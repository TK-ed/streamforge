import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from shared.db.db import Base


class VideoRendition(Base):
    __tablename__ = "video_renditions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False)

    resolution = Column(String, nullable=False)  # 360p/ 720p / 1080p

    status = Column(
        String,
        nullable=False,
        default="processing",  # processing | ready | failed
    )

    file_path = Column(Text, nullable=True)
    hls_path = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
