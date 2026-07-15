import argparse
import json
import subprocess
from fractions import Fraction
from pathlib import Path


def classify_aspect_ratio(width: int, height: int) -> str:
    ratio = width / height
    known = {
        "9:16": 9 / 16,
        "16:9": 16 / 9,
        "1:1": 1,
        "4:5": 4 / 5,
        "5:4": 5 / 4,
    }
    return min(known, key=lambda key: abs(known[key] - ratio))


def parse_fps(value: str) -> float:
    if not value or value == "0/0":
        return 0.0
    return float(Fraction(value))


def normalize_probe(probe: dict) -> dict:
    streams = probe.get("streams", [])
    video = next(stream for stream in streams if stream.get("codec_type") == "video")
    audio = [stream for stream in streams if stream.get("codec_type") == "audio"]
    width = int(video["width"])
    height = int(video["height"])
    duration = float(video.get("duration") or probe.get("format", {}).get("duration") or 0)
    fps = parse_fps(video.get("r_frame_rate", "0/0"))
    return {
        "width": width,
        "height": height,
        "aspect_ratio": classify_aspect_ratio(width, height),
        "duration_seconds": round(duration, 3),
        "fps": round(fps, 3),
        "has_audio": bool(audio),
    }


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    analysis = normalize_probe(run_ffprobe(args.video))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
