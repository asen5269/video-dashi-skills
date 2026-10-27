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


def prepare_values(values: dict) -> dict:
    values = dict(values)
    values.setdefault("unresolved_decisions", "None." if values.get("confirmed") is True else "Pending review.")
    mode = values.get("reference_mode", "storyboard")
    order = values.get("frame_order", "left to right, top to bottom")
    values["reference_rule"] = (
        "Use the uploaded reference video as the primary motion and timing reference."
        if mode == "video" else
        "Use the uploaded storyboard image as the primary visual reference."
    )
    values["order_rule"] = ("Preserve the confirmed video shot order." if mode == "video" else
                            f"Animate the storyboard frames {order}.")
    assets = values.get("assets", [])
    values["primary_reference"] = next(
        (f"{asset['id']}: {asset['path']}" for asset in assets
         if asset["role"] == ("video" if mode == "video" else "storyboard")),
        values.get("storyboard_image", ""),
    )
    values["product_rule"] = (
        "No product replacement is requested." if values.get("replacement_target", "").lower() == "none" else
        "Use the listed product reference image(s) for the replacement shape, material, color, logo and scale."
    )
    if isinstance(values.get("duration_seconds"), (int, float)):
        values["duration"] = f"{values['duration_seconds']:g} seconds"
    values["asset_manifest"] = "\n".join(
        f"- {asset['id']} ({asset['role']}): {asset['path']}" for asset in assets
    )
    if values.get("shots"):
        values["shot_prompts"] = "\n".join(
            f"Shot {shot['id']} [{shot['start']:.3f}-{shot['end']:.3f}s]: {shot['prompt']}"
            for shot in values["shots"]
        )
    return values


def render_seedance_prompt(values: dict) -> str:
    return render_template("seedance_prompt.md", prepare_values(values))


def validate_values(values: dict) -> list[str]:
    errors = []
    for key in ["replacement_target", "duration", "aspect_ratio", "audio_mode", "style",
                "preserve_rules", "change_rules", "negative_rules", "dialogue_timeline", "frame_order"]:
        if not isinstance(values.get(key), str) or not values[key].strip():
            errors.append(f"missing value: {key}")
    if values.get("confirmed") is not True:
        errors.append("final generation requires confirmed=true after user confirmation")
    unresolved = values.get("unresolved_decisions")
    if unresolved is not None and str(unresolved).strip().lower() not in {"", "none", "none.", "无", "无。"}:
        errors.append("unresolved decisions must be cleared before final generation")
    if values.get("speech") not in {"yes", "no"}:
        errors.append("speech must be resolved to yes or no")
    if values.get("reference_mode") not in {"storyboard", "video"}:
        errors.append("reference_mode must be storyboard or video")
    if not re.fullmatch(r"[1-9]\d*:[1-9]\d*", str(values.get("aspect_ratio", ""))):
        errors.append("aspect_ratio must be a positive integer ratio such as 9:16")
    duration = values.get("duration_seconds")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not 0 < duration < float("inf"):
        return errors + ["duration_seconds must be a finite positive number"]
    assets = values.get("assets", [])
    primary_ids = []
    product_ids = []
    if not isinstance(assets, list) or not assets or not all(
        isinstance(asset, dict) and all(isinstance(asset.get(key), str) and asset[key].strip()
                                      for key in ["id", "role", "path"]) for asset in assets
    ):
        errors.append("assets must contain id, role and path")
    else:
        ids = [asset["id"] for asset in assets]
        if len(set(ids)) != len(ids):
            errors.append("asset IDs must be unique")
        primary_role = "video" if values.get("reference_mode") == "video" else "storyboard"
        primary_ids = [asset["id"] for asset in assets if asset["role"] == primary_role]
        product_ids = [asset["id"] for asset in assets if asset["role"] == "product"]
        if sum(asset["role"] == primary_role for asset in assets) != 1:
            errors.append(f"exactly one {primary_role} asset is required")
        if values.get("replacement_target", "none").lower() != "none" and not any(
            asset["role"] == "product" for asset in assets
        ):
            errors.append("replacement requires a product asset")
        for asset in assets:
            if not Path(asset["path"]).is_absolute() or not Path(asset["path"]).is_file():
                errors.append(f"asset must be an existing absolute file: {asset['id']}")
    shots = values.get("shots", [])
    end = 0.0
    ids = set()
    if not isinstance(shots, list) or not shots:
        return errors + ["shots must cover the output timeline"]
    for shot in shots:
        if not isinstance(shot, dict) or not all(key in shot for key in ["id", "start", "end", "prompt"]):
            errors.append("each shot requires id, start, end and prompt")
            continue
        start, stop = shot["start"], shot["end"]
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool)
                   and abs(value) < float("inf") for value in [start, stop]):
            errors.append("shot times must be finite numbers")
            continue
        shot_id = str(shot["id"])
        if shot_id in ids or not shot_id.strip() or not isinstance(shot["prompt"], str) or not shot["prompt"].strip():
            errors.append("shot IDs must be unique and shot prompts nonempty")
        ids.add(shot_id)
        if isinstance(shot["prompt"], str) and primary_ids and not any(
            re.search(rf"(?<!\w){re.escape(asset_id)}(?!\w)", shot["prompt"]) for asset_id in primary_ids
        ):
            errors.append(f"shot {shot_id} must name its primary reference asset ID")
        if abs(start - end) > 0.05 or stop <= start or stop > duration + 0.05:
            errors.append("shots must be ordered and cover duration without gaps or overlaps")
        end = stop
    if abs(end - duration) > 0.05:
        errors.append("shots do not cover output duration")
    shot_text = "\n".join(shot.get("prompt", "") for shot in shots
                          if isinstance(shot, dict) and isinstance(shot.get("prompt"), str))
    for asset_id in product_ids:
        if not re.search(rf"(?<!\w){re.escape(asset_id)}(?!\w)", shot_text):
            errors.append(f"product asset is not mapped to any output shot: {asset_id}")
    return errors


def render_replacement_plan(values: dict[str, str]) -> str:
    return render_template("replacement_plan.md", prepare_values(values))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--stage", choices=["plan", "final"], default="plan")
    args = parser.parse_args()

    values = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.stage == "plan":
        (out_dir / "replacement_plan.md").write_text(render_replacement_plan(values), encoding="utf-8")
        return
    errors = validate_values(values)
    if errors:
        raise SystemExit("\n".join(errors))
    prompt = render_seedance_prompt(values)
    errors = lint_prompt(prompt, values["speech"], values["reference_mode"],
                         values["frame_order"], values["duration_seconds"])
    if errors:
        raise SystemExit("\n".join(errors))
    prompt_path = out_dir / "seedance_prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    (out_dir / "seedance_prompt.lint.txt").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
