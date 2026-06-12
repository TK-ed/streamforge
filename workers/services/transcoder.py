import os
import subprocess

from services.logger import logger


def run(cmd):
    subprocess.run(cmd, check=True)


def transcode(video_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    out_360 = f"{out_dir}/360p.mp4"
    out_720 = f"{out_dir}/720p.mp4"
    out_1080 = f"{out_dir}/1080p.mp4"

    # 360p
    run(
        [
            "ffmpeg",
            "-i",
            video_path,
            "-vf",
            "scale=w=640:h=360:force_original_aspect_ratio=decrease",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-b:v",
            "800k",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            out_360,
        ]
    )

    # 720p
    run(
        [
            "ffmpeg",
            "-i",
            video_path,
            "-vf",
            "scale=w=1280:h=720:force_original_aspect_ratio=decrease",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-b:v",
            "2500k",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            out_720,
        ]
    )

    # 1080p
    run(
        [
            "ffmpeg",
            "-i",
            video_path,
            "-vf",
            "scale=w=1920:h=1080:force_original_aspect_ratio=decrease",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-b:v",
            "5000k",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            out_1080,
        ]
    )
    logger.info("Transcoding has been completed")

    return {"360p": out_360, "720p": out_720, "1080p": out_1080}
