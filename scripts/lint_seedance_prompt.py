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


def lint_prompt(prompt: str, speech: str = "unknown") -> list[str]:
    errors: list[str] = []

    for line in REQUIRED_LINES:
        if line not in prompt:
            errors.append(f"missing required line: {line}")

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, prompt, flags=re.IGNORECASE):
            errors.append(f"forbidden reference-video instruction: {pattern}")

    if "{{" in prompt or "}}" in prompt:
        errors.append("unrendered template placeholder found")

    for label in ["Duration", "Aspect ratio", "Audio mode"]:
        if not has_value(prompt, label):
            errors.append(f"missing output setting: {label}")

    if speech == "yes" and not has_timestamped_dialogue(prompt):
        errors.append("speech is marked present, but timestamped dialogue is missing")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--speech", choices=["yes", "no", "unknown"], default="unknown")
    args = parser.parse_args()

    prompt = Path(args.prompt).read_text(encoding="utf-8")
    errors = lint_prompt(prompt, args.speech)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    print("OK")


if __name__ == "__main__":
    main()
