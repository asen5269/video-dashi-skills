import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

TIMED_LINE = re.compile(
    r"^(?P<start>\d{2}:\d{2}(?:\.\d{1,3})?|\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?)"
    r"-"
    r"(?P<end>\d{2}:\d{2}(?:\.\d{1,3})?|\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?)"
    r"\s+(?P<text>.+?)\s*$"
)


@dataclass
class TranscriptLine:
    start: str
    end: str
    text: str


def normalize_text(text: str, replacements: dict[str, str] | None = None) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    for old, new in (replacements or {}).items():
        text = text.replace(old, new)
    text = re.sub(r"\s+([，。！？；：,.!?;:])", r"\1", text)
    return text


def parse_transcript(content: str, replacements: dict[str, str] | None = None) -> list[TranscriptLine]:
    lines: list[TranscriptLine] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        match = TIMED_LINE.match(line)
        if not match:
            continue
        lines.append(
            TranscriptLine(
                start=match.group("start"),
                end=match.group("end"),
                text=normalize_text(match.group("text"), replacements),
            )
        )
    return lines


def timestamp_seconds(value: str) -> float:
    parts = value.split(":")
    if len(parts) == 2:
        minutes = int(parts[0])
        seconds = float(parts[1])
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    raise ValueError(f"invalid timestamp: {value}")


def srt_timestamp(value: str) -> str:
    total_ms = int(round(timestamp_seconds(value) * 1000))
    hours, rem = divmod(total_ms, 3600000)
    minutes, rem = divmod(rem, 60000)
    seconds, ms = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{ms:03}"


def render_clean(lines: list[TranscriptLine]) -> str:
    output = ["# Clean Transcript", ""]
    output.extend(f"{line.start}-{line.end} {line.text}" for line in lines)
    output.append("")
    return "\n".join(output)


def render_timeline(lines: list[TranscriptLine], speaker: str) -> str:
    output = ["# Dialogue Timeline", ""]
    for line in lines:
        output += [
            f'{line.start}-{line.end} {speaker} says: "{line.text}"',
            "Tone: natural spoken delivery.",
            "Visual sync: match the original speaker timing and visible action.",
            "",
        ]
    return "\n".join(output)


def render_srt(lines: list[TranscriptLine]) -> str:
    output: list[str] = []
    for index, line in enumerate(lines, start=1):
        output += [
            str(index),
            f"{srt_timestamp(line.start)} --> {srt_timestamp(line.end)}",
            line.text,
            "",
        ]
    return "\n".join(output)


def load_replacements(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("replacement file must be a JSON object")
    return {str(key): str(value) for key, value in data.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--clean-out")
    parser.add_argument("--timeline-out")
    parser.add_argument("--srt-out")
    parser.add_argument("--replacements")
    parser.add_argument("--speaker", default="Speaker")
    args = parser.parse_args()

    replacements = load_replacements(args.replacements)
    lines = parse_transcript(Path(args.input).read_text(encoding="utf-8"), replacements)
    if not lines:
        raise SystemExit("no timestamped transcript lines found")

    outputs = {
        args.clean_out: render_clean(lines),
        args.timeline_out: render_timeline(lines, args.speaker),
        args.srt_out: render_srt(lines),
    }
    for path, content in outputs.items():
        if not path:
            continue
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        print(out_path)


if __name__ == "__main__":
    main()
