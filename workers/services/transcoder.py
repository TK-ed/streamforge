import os
import subprocess

from services.logger import logger


def generate_hls(input_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, "index.m3u8")

    command = [
        "ffmpeg",
        "-i",
        input_path,
        "-c",
        "copy",
        "-start_number",
        "0",
        "-hls_time",
        "4",
        "-hls_list_size",
        "0",
        "-f",
        "hls",
        output_path,
    ]

    subprocess.run(command, check=True)
    logger.info("HLS is generated!")
    return output_path
