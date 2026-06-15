from enum import Enum


class VideoStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoEvents(str, Enum):
    VIDEO_PROCESSING_STARTED = "VIDEO_PROCESSING_STARTED"
    VIDEO_PROCESSING_COMPLETED = "VIDEO_PROCESSING_COMPLETED"
    VIDEO_PROCESSING_FAILED = "VIDEO_PROCESSING_FAILED"


MAX_RETRIES = 3

VIDEO_QUEUE = "video.processing"
EVENT_QUEUE = "video.events"
