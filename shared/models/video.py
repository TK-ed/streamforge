from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.sql import func

from shared.db.db import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    filename = Column(String, nullable=False)

    object_name = Column(
        String,
        nullable=False,
        unique=True,
    )

    content_type = Column(String)

    size = Column(BigInteger)

    status = Column(
        String,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    thumbnail_object_name = Column(String, nullable=True)
