import os
import subprocess

from services.logger import logger


def run(cmd):
    subprocess.run(cmd, check=True)


def generate_adaptive_hls(input_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-filter_complex",
        (
            "[0:v]split=3[v360in][v720in][v1080in];"
            "[v360in]scale=640:360[v360];"
            "[v720in]scale=1280:720[v720];"
            "[v1080in]scale=1920:1080[v1080]"
        ),
        # 360p
        "-map",
        "[v360]",
        "-map",
        "0:a?",
        # 720p
        "-map",
        "[v720]",
        "-map",
        "0:a?",
        # 1080p
        "-map",
        "[v1080]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "superfast",
        "-r",
        "30",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-b:v:0",
        "800k",
        "-b:v:1",
        "2500k",
        "-b:v:2",
        "5000k",
        "-b:a",
        "128k",
        "-f",
        "hls",
        "-hls_time",
        "4",
        "-hls_list_size",
        "0",
        "-master_pl_name",
        "master.m3u8",
        "-var_stream_map",
        "v:0,a:0,name:360p v:1,a:1,name:720p v:2,a:2,name:1080p",
        "-hls_segment_filename",
        f"{output_dir}/%v/segment_%03d.ts",
        f"{output_dir}/%v/index.m3u8",
    ]

    logger.info("Starting adaptive HLS generation")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error(result.stderr)
        raise Exception("Adaptive HLS generation failed")

    logger.info("Adaptive HLS generation completed")

    return os.path.join(output_dir, "master.m3u8")


def transcode_variant(video_path, output_path, width, height, v_bitrate, a_bitrate):
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vf",
            f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease",
            "-c:v",
            "libx264",
            "-preset",
            "superfast",
            "-b:v",
            v_bitrate,
            "-c:a",
            "aac",
            "-b:a",
            "-r",
            "30",
            a_bitrate,
            output_path,
        ]
    )

    return output_path
