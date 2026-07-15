from __future__ import annotations

import re
import sys
from pathlib import Path

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_PATTERN = re.compile(r"\[[^]]*]\(([^)]+)\)")


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("SKILL.md frontmatter is not closed")
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"\'')
    return values


def local_links(path: Path) -> list[Path]:
    missing: list[Path] = []
    for target in LINK_PATTERN.findall(path.read_text(encoding="utf-8")):
        target = target.split("#", 1)[0].strip()
        if not target or "://" in target or target.startswith("#"):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            missing.append(resolved)
    return missing


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    skill_path = root / "SKILL.md"
    agent_path = root / "agents" / "openai.yaml"
    if not skill_path.is_file():
        return ["SKILL.md is missing"]

    text = skill_path.read_text(encoding="utf-8")
    try:
        metadata = frontmatter(text)
    except ValueError as exc:
        return [str(exc)]

    name = metadata.get("name", "")
    description = metadata.get("description", "")
    if not NAME_PATTERN.fullmatch(name):
        errors.append("frontmatter name must use lowercase letters, digits, and hyphens")
    if root.name != name:
        errors.append(f"folder name '{root.name}' must match skill name '{name}'")
    if not description:
        errors.append("frontmatter description is required")
    if len(text.splitlines()) > 500:
        errors.append("SKILL.md must stay at or below 500 lines")
    if not agent_path.is_file():
        errors.append("agents/openai.yaml is missing")
    elif f"$${name}" in agent_path.read_text(encoding="utf-8"):
        errors.append("agents/openai.yaml contains an invalid doubled skill marker")
    elif f"${name}" not in agent_path.read_text(encoding="utf-8"):
        errors.append("agents/openai.yaml default_prompt must mention the skill with $name")

    for document in (skill_path, root / "README.md", root / "README.zh-CN.md"):
        if document.is_file():
            errors.extend(f"broken local link in {document.name}: {item}" for item in local_links(document))
    return errors


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Valid skill: {root.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
