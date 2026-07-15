import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def default_parser_root() -> Path:
    home = Path(os.environ.get("USERPROFILE", str(Path.home())))
    candidates = [
        home / ".codex" / "skills" / "social-media-parser",
        home / ".codex" / "skills" / "social-media-parser" / "social-media-parser",
    ]
    for candidate in candidates:
        if (candidate / "scripts" / "social_media_parser.py").exists():
            return candidate
    raise SystemExit("social-media-parser skill not found under USERPROFILE\\.codex\\skills")


def run_parser(parser_root: Path, text: str) -> dict:
    script = parser_root / "scripts" / "social_media_parser.py"
    result = subprocess.run(
        [sys.executable, str(script), "parse", text, "--format", "json"],
        cwd=parser_root,
        check=True,
        capture_output=True,
    )
    try:
        stdout = result.stdout.decode("utf-8")
    except UnicodeDecodeError:
        stdout = result.stdout.decode("gbk")
    return json.loads(stdout)


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


def resolve(input_value: str, out_dir: Path, parser_root: Path) -> dict:
    local_path = Path(input_value.strip().strip('"'))
    if local_path.exists():
        return {
            "input_type": "local_video",
            "video_path": str(local_path.resolve()),
            "parser_result": None,
        }

    parser_result = run_parser(parser_root, input_value)
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
    parser.add_argument("--parser-root")
    args = parser.parse_args()

    parser_root = Path(args.parser_root) if args.parser_root else default_parser_root()
    out_dir = Path(args.out_dir)
    result = resolve(args.input, out_dir, parser_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "reference_input.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
