import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.logger import logger


def verify_download(path: str) -> bool:
    if not os.path.exists(path):
        return False

    size = os.path.getsize(path)
    if size == 0:
        return False

    return True


def generate_all_hls(renditions: dict, hls_root: str):
    futures = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        for quality, video_path in renditions.items():
            output_dir = os.path.join(hls_root, quality)

            futures.append(
                executor.submit(
                    generate_hls,
                    video_path,
                    output_dir,
                )
            )

        for future in as_completed(futures):
            future.result()

    logger.info("All HLS renditions generated")


def generate_hls(input_path: str, output_dir: str):
    print("🔥 HLS FUNCTION ENTERED")
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, "index.m3u8")

    if not os.path.exists(input_path):
        raise Exception(f"Input missing: {input_path}")

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        input_path,
        "-c:v",
        "libx264",
        "-preset",
        "superfast",
        "-r",
        "30",
        "-g",
        "48",
        "-sc_threshold",
        "0",
        "-c:a",
        "aac",
        "-f",
        "hls",
        "-hls_time",
        "4",
        "-hls_list_size",
        "0",
        "-hls_segment_filename",
        f"{output_dir}/segment_%03d.ts",
        output_path,
    ]
    logger.info(f"HLS CMD: {cmd}")

    print("\n🚀 RUNNING FFmpeg HLS:\n", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True)

    print(result.stdout)
    print(result.stderr)

    result.check_returncode()

    if result.returncode != 0:
        raise Exception("HLS FAILED")

    print("\n✅ HLS GENERATED:", output_path)
    return output_path


def create_master_playlist(hls_dir: str):
    """
    hls_dir structure:
    /hls/
        360p/index.m3u8
        720p/index.m3u8
        1080p/index.m3u8
    """

    master_path = os.path.join(hls_dir, "master.m3u8")

    playlist = """#EXTM3U

#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360
360p/index.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=3000000,RESOLUTION=1280x720
720p/index.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=6000000,RESOLUTION=1920x1080
1080p/index.m3u8
"""

    with open(master_path, "w") as f:
        f.write(playlist)

    logger.info(f"Master playlist created at {master_path}")

    return master_path
