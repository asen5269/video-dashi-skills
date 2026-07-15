import argparse
import json
import subprocess
from fractions import Fraction
from pathlib import Path


def parse_fps(value: str) -> float:
    if not value or value == "0/0":
        return 0.0
    return float(Fraction(value))


def run_ffprobe(video_path: str) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            video_path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def inspect_video(probe: dict) -> dict:
    streams = probe.get("streams", [])
    video = next(stream for stream in streams if stream.get("codec_type") == "video")
    audio = [stream for stream in streams if stream.get("codec_type") == "audio"]
    width = int(video["width"])
    height = int(video["height"])
    duration = float(video.get("duration") or probe.get("format", {}).get("duration") or 0)
    bitrate = int(video.get("bit_rate") or probe.get("format", {}).get("bit_rate") or 0)
    fps = parse_fps(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/0")
    pixels = width * height

    if min(width, height) < 720:
        scale = 2
    elif min(width, height) < 1080:
        scale = 2
    else:
        scale = 1

    if bitrate and duration and bitrate / max(pixels * max(fps, 1), 1) < 0.04:
        profile = "compressed"
    else:
        profile = "realistic"

    return {
        "width": width,
        "height": height,
        "duration_seconds": round(duration, 3),
        "fps": round(fps, 3),
        "bitrate": bitrate,
        "has_audio": bool(audio),
        "recommended_scale": scale,
        "recommended_profile": profile,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()

    result = inspect_video(run_ffprobe(args.video))
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
