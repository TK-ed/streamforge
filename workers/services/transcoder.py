import json
import os
import subprocess

from services.logger import logger

# Ladder of target renditions (by height). We only ever downscale to these.
RENDITIONS = [
    {"name": "360p", "height": 360, "vbr": "800k"},
    {"name": "720p", "height": 720, "vbr": "2500k"},
    {"name": "1080p", "height": 1080, "vbr": "5000k"},
]

# Video encoder is env-selectable so the same code runs on CPU by default and on
# NVIDIA GPUs where available (e.g. ENCODER=h264_nvenc). Presets are encoder-
# specific (x264 uses superfast/fast/...; NVENC uses p1-p7), so each encoder gets
# its own sensible default, overridable via ENCODER_PRESET.
ENCODER = os.getenv("ENCODER", "libx264")
_DEFAULT_PRESETS = {"libx264": "superfast", "h264_nvenc": "p4", "hevc_nvenc": "p4"}
ENCODER_PRESET = os.getenv("ENCODER_PRESET", _DEFAULT_PRESETS.get(ENCODER, "medium"))


def run(cmd):
    subprocess.run(cmd, check=True)


def _probe_input(input_path: str):
    """Return (has_audio, source_height) for the input, via ffprobe.

    On any probe error we fall back to (False, 0): no audio and "no known
    source height" (which keeps the full ladder).
    """
    has_audio = False
    source_height = 0
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-of", "json", input_path],
            capture_output=True,
            text=True,
            check=True,
        )
        for stream in json.loads(out.stdout or "{}").get("streams", []):
            if stream.get("codec_type") == "audio":
                has_audio = True
            elif stream.get("codec_type") == "video":
                source_height = max(source_height, int(stream.get("height") or 0))
    except Exception as e:
        logger.warning(f"ffprobe failed ({e}); assuming no audio, full ladder")
    return has_audio, source_height


def generate_adaptive_hls(input_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    has_audio, source_height = _probe_input(input_path)

    # Downscale only: keep renditions at or below the source height; never upscale.
    renditions = [
        r for r in RENDITIONS if source_height == 0 or r["height"] <= source_height
    ]
    if not renditions:
        # Source smaller than the smallest rung: emit one stream at source size.
        even_h = max(2, source_height - (source_height % 2))
        renditions = [{"name": f"{even_h}p", "height": even_h, "vbr": "800k"}]

    n = len(renditions)
    logger.info(
        f"Transcoding {n} rendition(s) {[r['name'] for r in renditions]} "
        f"(audio={has_audio}, source_height={source_height})"
    )

    # ffmpeg's HLS muxer writes into %v subdirs; pre-create them to be safe.
    for r in renditions:
        os.makedirs(os.path.join(output_dir, r["name"]), exist_ok=True)

    # Aspect-preserving scale: width auto (-2 => divisible by 2), so no stretching.
    split_labels = "".join(f"[v{i}in]" for i in range(n))
    scale_chain = ";".join(
        f"[v{i}in]scale=-2:{r['height']}[v{i}]" for i, r in enumerate(renditions)
    )
    filter_complex = f"[0:v]split={n}{split_labels};{scale_chain}"

    cmd = ["ffmpeg", "-y", "-i", input_path, "-filter_complex", filter_complex]

    # Map each scaled video, plus the source audio only when it exists.
    for i in range(n):
        cmd += ["-map", f"[v{i}]"]
        if has_audio:
            cmd += ["-map", "0:a:0"]

    cmd += ["-c:v", ENCODER, "-preset", ENCODER_PRESET, "-r", "30"]
    for i, r in enumerate(renditions):
        cmd += [f"-b:v:{i}", r["vbr"]]

    if has_audio:
        cmd += ["-c:a", "aac", "-ar", "48000", "-b:a", "128k"]
        var_map = " ".join(
            f"v:{i},a:{i},name:{r['name']}" for i, r in enumerate(renditions)
        )
    else:
        var_map = " ".join(f"v:{i},name:{r['name']}" for i, r in enumerate(renditions))

    cmd += [
        "-f",
        "hls",
        "-hls_time",
        "4",
        "-hls_list_size",
        "0",
        "-master_pl_name",
        "master.m3u8",
        "-var_stream_map",
        var_map,
        "-hls_segment_filename",
        f"{output_dir}/%v/segment_%03d.ts",
        f"{output_dir}/%v/index.m3u8",
    ]

    logger.info(
        f"Starting adaptive HLS generation (encoder={ENCODER}, preset={ENCODER_PRESET})"
    )

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
