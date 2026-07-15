import argparse
from pathlib import Path


def format_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    minutes, rem = divmod(ms, 60000)
    secs, ms = divmod(rem, 1000)
    return f"{minutes:02}:{secs:02}.{ms:03}"


def format_srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hours, rem = divmod(ms, 3600000)
    minutes, rem = divmod(rem, 60000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--srt-out")
    parser.add_argument("--model", default="small")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    args = parser.parse_args()

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SystemExit("faster-whisper is required: python -m pip install faster-whisper") from exc

    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    segments, info = model.transcribe(args.video, vad_filter=True, beam_size=5)
    segments = list(segments)

    transcript = [f"language={info.language} probability={info.language_probability:.2f}", ""]
    srt_lines = []
    for index, segment in enumerate(segments, start=1):
        text = (segment.text or "").strip()
        if not text:
            continue
        transcript.append(f"{format_timestamp(segment.start)}-{format_timestamp(segment.end)} {text}")
        srt_lines += [
            str(index),
            f"{format_srt_timestamp(segment.start)} --> {format_srt_timestamp(segment.end)}",
            text,
            "",
        ]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(transcript), encoding="utf-8")

    if args.srt_out:
        srt_path = Path(args.srt_out)
        srt_path.parent.mkdir(parents=True, exist_ok=True)
        srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

    print(out_path)


if __name__ == "__main__":
    main()
