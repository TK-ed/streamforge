import os
import subprocess

from services.logger import logger


def generate_thumbnail(input_path, thumbnail_path):
    os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
    # print(os.path.isfile(thumbnail_path))
    # print(os.path.isdir(thumbnail_path))
    try:
        command = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-ss",
            "00:00:02",
            "-vframes",
            "1",
            "-f",
            "image2",
            thumbnail_path,
        ]
        subprocess.run(command, check=True)
        logger.info("Thumbnail is generated!")
    except Exception as e:
        logger.error(f"Thumbnail failed: {e}")
        raise
