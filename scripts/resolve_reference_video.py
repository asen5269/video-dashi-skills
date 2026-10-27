import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

try:
    from .douyin_parser import parse_douyin
except ImportError:
    from douyin_parser import parse_douyin

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def extension_from(url: str, content_type: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".mp4", ".mov", ".m4v", ".webm"}:
        return suffix
    if "webm" in content_type:
        return ".webm"
    if "quicktime" in content_type:
        return ".mov"
    return ".mp4"


def download_video(url: str, out_dir: Path, referer: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": referer or "https://www.douyin.com/",
    }
    with requests.get(url, headers=headers, stream=True, timeout=60) as response:
        response.raise_for_status()
        ext = extension_from(url, response.headers.get("content-type", ""))
        out_path = out_dir / f"reference_video{ext}"
        with out_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return out_path


def resolve(input_value: str, out_dir: Path) -> dict:
    local_path = Path(input_value.strip().strip('"'))
    if local_path.exists():
        if not local_path.is_file():
            raise SystemExit("Input must be a file, not a directory.")
        if local_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            from PIL import Image

            with Image.open(local_path) as image:
                width, height = image.size
                image.verify()
            return {
                "input_type": "storyboard_image",
                "image_path": str(local_path.resolve()),
                "width": width,
                "height": height,
                "duration": None,
                "audio": "unknown",
                "frame_order": "unknown",
                "parser_result": None,
            }
        return {
            "input_type": "local_video",
            "video_path": str(local_path.resolve()),
            "parser_result": None,
        }

    parser_result = parse_douyin(input_value)
    videos = parser_result.get("videos") or []
    if not videos:
        raise SystemExit("No video URL found. Parser may have returned an image/note post or login-gated page.")

    video_path = download_video(videos[0], out_dir, parser_result.get("url") or "")
    return {
        "input_type": "social_link",
        "video_path": str(video_path.resolve()),
        "parser_result": parser_result,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    result = resolve(args.input, out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "reference_input.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
