import argparse
import json
import re
from pathlib import Path

try:
    from scripts.lint_seedance_prompt import lint_prompt
except ImportError:
    from lint_seedance_prompt import lint_prompt


ROOT = Path(__file__).resolve().parents[1]


def render_template(template_name: str, values: dict[str, str]) -> str:
    template = (ROOT / "templates" / template_name).read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        return str(values.get(key, ""))

    return re.sub(r"{{\s*([^}]+)\s*}}", replace, template)


def render_seedance_prompt(values: dict[str, str]) -> str:
    return render_template("seedance_prompt.md", values)


def render_replacement_plan(values: dict[str, str]) -> str:
    return render_template("replacement_plan.md", values)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--skip-lint", action="store_true")
    args = parser.parse_args()

    values = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = render_seedance_prompt(values)
    prompt_path = out_dir / "seedance_prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    (out_dir / "replacement_plan.md").write_text(render_replacement_plan(values), encoding="utf-8")

    if not args.skip_lint:
        speech = str(values.get("speech") or values.get("has_speech") or values.get("speech_presence") or "unknown")
        speech = {"true": "yes", "false": "no"}.get(speech.lower(), speech.lower())
        if speech not in {"yes", "no", "unknown"}:
            speech = "unknown"
        errors = lint_prompt(prompt, speech=speech)
        if errors:
            (out_dir / "seedance_prompt.lint.txt").write_text(
                "\n".join(f"ERROR: {error}" for error in errors) + "\n",
                encoding="utf-8",
            )
            raise SystemExit("seedance_prompt.md failed lint; see seedance_prompt.lint.txt")


if __name__ == "__main__":
    main()
