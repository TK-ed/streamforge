class VideoStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


MAX_RETRIES = 3

VIDEO_QUEUE = "video.processing"
DLQ_QUEUE = "video_uploaded_dlq"
VIDEO_DLX = "video_dlx"
VIDEO_FAILED_ROUTING_KEY = "video_failed"
