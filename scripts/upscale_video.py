import argparse
import json
from pathlib import Path

from enhance_video import (
    enhance_with_realesrgan,
    find_executable,
    run,
    video_info,
)


def resize_to_height(src: Path, dst: Path, target_height: int, crf: int, preset: str) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            f"scale=-2:{target_height}:flags=lanczos",
            "-c:v",
            "libx264",
            "-crf",
            str(crf),
            "-preset",
            preset,
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            str(dst),
        ]
    )


def write_metadata(path: Path, metadata: dict) -> None:
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--backend", choices=["auto", "realesrgan"], default="auto")
    parser.add_argument("--profile", choices=["realistic", "product", "compressed", "game", "anime", "clean"], default="compressed")
    parser.add_argument("--scale", type=int, choices=[1, 2, 3, 4], default=2)
    parser.add_argument("--target-height", type=int)
    parser.add_argument("--model", default="realesr-animevideov3")
    parser.add_argument("--tile", type=int, default=0)
    parser.add_argument("--crf", type=int, default=16)
    parser.add_argument("--preset", default="slow")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "upscaled_video.mp4"
    work_path = out_dir / "_upscaled_work.mp4" if args.target_height else out_path
    if not find_executable("realesrgan-ncnn-vulkan", "realesrgan-ncnn-vulkan.exe"):
        raise SystemExit("realesrgan-ncnn-vulkan not found")
    backend = "realesrgan"
    before = video_info(args.video)

    enhance_with_realesrgan(args.video, out_dir, work_path, args.model, args.scale, args.crf, args.preset, args.tile)

    if args.target_height:
        resize_to_height(work_path, out_path, args.target_height, args.crf, args.preset)
        work_path.unlink(missing_ok=True)

    after = video_info(str(out_path))
    write_metadata(
        out_dir / "upscale_metadata.json",
        {
            "input_video": str(Path(args.video).resolve()),
            "output_video": str(out_path.resolve()),
            "backend": backend,
            "profile": args.profile,
            "scale": args.scale,
            "target_height": args.target_height,
            "model": args.model if backend == "realesrgan" else None,
            "tile": args.tile,
            "before": before,
            "after": after,
            "usage_note": "Final delivery video. Audio preserved when source has audio.",
        },
    )
    print(out_path)


if __name__ == "__main__":
    main()
