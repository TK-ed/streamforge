from prometheus_client import Counter, Gauge, Histogram

VIDEO_PROCESSED = Counter("video_processed_total", "Total videos processed")

VIDEO_FAILED = Counter("video_failed_total", "Failed videos")

VIDEO_PROCESSING_TIME = Histogram(
    "video_processing_seconds", "Time taken to process video"
)

ACTIVE_JOBS = Gauge("active_video_jobs", "Currently processing videos")
