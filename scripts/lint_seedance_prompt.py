import argparse
import re
from pathlib import Path

REQUIRED_LINES = [
    "Use the uploaded storyboard image as the primary visual reference.",
    "Animate the storyboard frames left to right, top to bottom.",
]

FORBIDDEN_PATTERNS = [
    r"use\s+the\s+uploaded\s+reference\s+video",
    r"use\s+uploaded\s+reference\s+video",
    r"use\s+the\s+original\s+video\s+as\s+the\s+reference",
    r"upload\s+the\s+original\s+video",
    r"upload\s+the\s+reference\s+video",
]


def has_value(prompt: str, label: str) -> bool:
    match = re.search(rf"^\s*-\s*{re.escape(label)}:\s*(.+?)\s*$", prompt, re.MULTILINE)
    return bool(match and match.group(1).strip())


def has_timestamped_dialogue(prompt: str) -> bool:
    return bool(
        re.search(
            r"\d{2}:\d{2}(?:\.\d{1,3})?-\d{2}:\d{2}(?:\.\d{1,3})?\s+.+?\s+says:\s+\".+?\"",
            prompt,
        )
    )


def lint_prompt(prompt: str, speech: str = "unknown", reference_mode: str = "storyboard",
                frame_order: str = "left to right, top to bottom", duration_seconds: float | None = None) -> list[str]:
    errors: list[str] = []

    required = ([REQUIRED_LINES[0], f"Animate the storyboard frames {frame_order}."]
                if reference_mode == "storyboard" else
                ["Use the uploaded reference video as the primary motion and timing reference."])
    if reference_mode not in {"storyboard", "video"}:
        errors.append("reference_mode must be storyboard or video")
    for line in required:
        if line not in prompt:
            errors.append(f"missing required line: {line}")

    for pattern in FORBIDDEN_PATTERNS if reference_mode == "storyboard" else []:
        if re.search(pattern, prompt, flags=re.IGNORECASE):
            errors.append(f"forbidden reference-video instruction: {pattern}")

    if "{{" in prompt or "}}" in prompt:
        errors.append("unrendered template placeholder found")

    for label in ["Duration", "Aspect ratio", "Audio mode"]:
        if not has_value(prompt, label):
            errors.append(f"missing output setting: {label}")

    if speech == "yes" and not has_timestamped_dialogue(prompt):
        errors.append("speech is marked present, but timestamped dialogue is missing")
    if speech == "no" and has_timestamped_dialogue(prompt):
        errors.append("speech is marked absent, but dialogue is present")

    if re.search(r"\[unclear\]|\[疑似[:：]|\bTODO\b|\bTBD\b", prompt, re.IGNORECASE):
        errors.append("unresolved content found")
    previous_end = 0.0
    for match in re.finditer(r'(\d{2}:\d{2}(?:\.\d{1,3})?)-(\d{2}:\d{2}(?:\.\d{1,3})?)\s+.+?\s+says:\s+".+?"', prompt):
        start, end = [int(value.split(":")[0]) * 60 + float(value.split(":")[1])
                      for value in match.groups()]
        if any(float(value.split(":")[1]) >= 60 for value in match.groups()):
            errors.append("dialogue timestamp seconds must be less than 60")
        if end <= start or start < previous_end or (duration_seconds is not None and end > duration_seconds):
            errors.append("dialogue timestamps overlap, are reversed, or exceed output duration")
        previous_end = end

    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--speech", choices=["yes", "no", "unknown"], default="unknown")
    parser.add_argument("--reference-mode", choices=["storyboard", "video"], default="storyboard")
    parser.add_argument("--frame-order", default="left to right, top to bottom")
    parser.add_argument("--duration-seconds", type=float)
    args = parser.parse_args()

    prompt = Path(args.prompt).read_text(encoding="utf-8")
    errors = lint_prompt(prompt, args.speech, args.reference_mode, args.frame_order, args.duration_seconds)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    print("OK")


if __name__ == "__main__":
    main()
