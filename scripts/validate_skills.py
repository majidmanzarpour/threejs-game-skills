#!/usr/bin/env python3
"""Self-contained validator for Three.js game skill folders.

Checks SKILL.md frontmatter parity with skill-creator's quick_validate.py,
verifies agents/openai.yaml metadata, validates local reference/script paths,
and ensures sibling threejs-* skill references resolve inside the pack.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - stdlib fallback when PyYAML is absent
    yaml = None

MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
REQUIRED_OPENAI_INTERFACE_KEYS = ("display_name", "short_description", "default_prompt")

# Identifiers starting with threejs- that are project/template names, not skill folders.
NON_SKILL_THREEJS_TOKENS = {
    "threejs-vite-game",
    "threejs-game-skills",
    "threejs-game",
    "threejs-canvas",
    "threejs-package",
    "threejs-cli",
    "threejs-audio",
}


def _parse_simple_yaml_mapping(text: str) -> dict[str, Any]:
    """Minimal fallback parser for flat key: value YAML blocks when PyYAML is absent."""
    result: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Unsupported YAML line without colon: {raw_line!r}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        result[key] = value
    return result


def parse_yaml_block(text: str) -> Any:
    if yaml is not None:
        return yaml.safe_load(text)
    return _parse_simple_yaml_mapping(text)


def strip_fenced_blocks(markdown: str) -> str:
    """Return markdown lines outside fenced code blocks."""
    kept: list[str] = []
    fence_marker: str | None = None
    fence_length = 0
    for line in markdown.splitlines():
        fence = re.match(r"^[ \t]*(?:(?:[-+*]|\d+[.)])[ \t]+)?(`{3,}|~{3,})(.*)$", line)
        if fence:
            marker = fence.group(1)
            if fence_marker is None:
                fence_marker = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_marker and len(marker) >= fence_length and not fence.group(2).strip():
                fence_marker = None
                fence_length = 0
            continue
        if fence_marker is None:
            kept.append(line)
    return "\n".join(kept)


def validate_openai_yaml(skill_path: Path) -> list[str]:
    errors: list[str] = []
    openai_yaml = skill_path / "agents" / "openai.yaml"
    if not openai_yaml.is_file():
        return ["Missing agents/openai.yaml"]

    raw = openai_yaml.read_text(encoding="utf-8")
    if yaml is not None:
        try:
            data = yaml.safe_load(raw)
        except Exception as exc:  # pragma: no cover
            return [f"Invalid YAML in agents/openai.yaml: {exc}"]
        interface = data.get("interface") if isinstance(data, dict) else None
        if not isinstance(interface, dict):
            return ["agents/openai.yaml must define an 'interface' mapping"]
    else:
        interface = {}
        for line in raw.splitlines():
            m = re.match(r"^\s+([a-z_]+)\s*:\s*(.+)$", line)
            if m:
                val = m.group(2).strip()
                if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                    val = val[1:-1]
                interface[m.group(1)] = val

    for key in REQUIRED_OPENAI_INTERFACE_KEYS:
        val = interface.get(key)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"agents/openai.yaml missing non-empty interface.{key}")
        elif "[TODO:" in val:
            errors.append(f"agents/openai.yaml interface.{key} contains TODO placeholder")

    return errors


def validate_links(skill_path: Path, body: str, known_skills: set[str] | None) -> list[str]:
    errors: list[str] = []
    prose = strip_fenced_blocks(body)

    # 1. Local skill references mentioned outside code blocks (excluding sibling-prefixed paths)
    for match in re.finditer(r"(?<![A-Za-z0-9_/-])(references/[A-Za-z0-9._/-]+\.md)\b", prose):
        rel = match.group(1)
        if not (skill_path / rel).is_file():
            errors.append(f"Referenced local file does not exist: {rel}")

    # 2. Explicit <this-skill-dir>/<path> references anywhere in body (including code blocks)
    for match in re.finditer(r"<this-skill-dir>/([A-Za-z0-9._/-]+)", body):
        rel = match.group(1).rstrip("/.,);:")
        if not (skill_path / rel).exists():
            errors.append(f"Referenced <this-skill-dir>/{rel} does not exist")

    # 3. Cross-skill paths and sibling skill names when validating within a skill pack
    if known_skills is not None:
        skills_root = skill_path.parent
        for match in re.finditer(
            r"\b(threejs-[a-z0-9-]+)/(references|scripts|assets)/([A-Za-z0-9._/-]+)", body
        ):
            sibling, kind, rest = match.group(1), match.group(2), match.group(3).rstrip("/.,);:")
            if sibling not in known_skills:
                errors.append(f"Referenced unknown sibling skill: {sibling}")
                continue
            target = skills_root / sibling / kind / rest
            if not target.exists():
                errors.append(f"Referenced sibling resource does not exist: {sibling}/{kind}/{rest}")

        # Verify backticked sibling skill names in prose resolve to real skills
        for match in re.finditer(r"`(threejs-[a-z0-9-]+)`", prose):
            token = match.group(1)
            if token in NON_SKILL_THREEJS_TOKENS or token == "threejs-*":
                continue
            if token not in known_skills:
                errors.append(f"Unknown sibling skill name in SKILL.md: {token}")

    return errors


def validate_skill(skill_path: Path, known_skills: set[str] | None = None) -> tuple[bool, list[str]]:
    skill_path = Path(skill_path)
    errors: list[str] = []

    skill_md = skill_path / "SKILL.md"
    if not skill_md.is_file():
        return False, ["SKILL.md not found"]

    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False, ["No YAML frontmatter found"]

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, ["Invalid frontmatter format"]

    try:
        frontmatter = parse_yaml_block(match.group(1))
        if not isinstance(frontmatter, dict):
            return False, ["Frontmatter must be a YAML dictionary"]
    except Exception as exc:
        return False, [f"Invalid YAML in frontmatter: {exc}"]

    unexpected_keys = set(frontmatter.keys()) - ALLOWED_FRONTMATTER_KEYS
    if unexpected_keys:
        errors.append(
            f"Unexpected frontmatter key(s): {', '.join(sorted(unexpected_keys))}"
        )

    name = frontmatter.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("Missing or invalid 'name' in frontmatter")
    else:
        name = name.strip()
        if not re.match(r"^[a-z0-9-]+$", name):
            errors.append(f"Name '{name}' must be hyphen-case (a-z, 0-9, -)")
        if name.startswith("-") or name.endswith("-") or "--" in name:
            errors.append(f"Name '{name}' cannot start/end with '-' or contain '--'")
        if len(name) > MAX_SKILL_NAME_LENGTH:
            errors.append(f"Name exceeds {MAX_SKILL_NAME_LENGTH} characters ({len(name)})")
        if name != skill_path.name:
            errors.append(f"Frontmatter name '{name}' does not match directory '{skill_path.name}'")

    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append("Missing or invalid 'description' in frontmatter")
    else:
        description = description.strip()
        if description.startswith("[TODO:"):
            errors.append("Description contains an unfinished TODO placeholder")
        if "<" in description or ">" in description:
            errors.append("Description cannot contain angle brackets (< or >)")
        if len(description) > MAX_DESCRIPTION_LENGTH:
            errors.append(
                f"Description exceeds {MAX_DESCRIPTION_LENGTH} characters ({len(description)})"
            )

    body = content[match.end() :]
    prose = strip_fenced_blocks(body)
    for line in prose.splitlines():
        if re.fullmatch(r"[ ]{0,3}\[TODO:[^\n]*\][ \t]*", line):
            errors.append("Skill instructions contain an unfinished TODO placeholder")
            break

    errors.extend(validate_openai_yaml(skill_path))
    errors.extend(validate_links(skill_path, body, known_skills))

    return len(errors) == 0, errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python3 scripts/validate_skills.py <skills-dir-or-skill-dir>", file=sys.stderr)
        return 1

    target = Path(argv[1]).resolve()
    if not target.exists():
        print(f"Path not found: {target}", file=sys.stderr)
        return 1

    if (target / "SKILL.md").is_file():
        sibling_dirs = {
            p.parent.name for p in target.parent.glob("*/SKILL.md")
        } if target.parent.is_dir() else {target.name}
        skill_dirs = [target]
        known_skills = sibling_dirs
    else:
        skill_dirs = sorted(p.parent for p in target.glob("*/SKILL.md"))
        if not skill_dirs:
            print(f"No skills found under: {target}", file=sys.stderr)
            return 1
        known_skills = {p.name for p in skill_dirs}

    failed = 0
    for skill_dir in skill_dirs:
        ok, errors = validate_skill(skill_dir, known_skills)
        if ok:
            print(f"OK   {skill_dir.name}")
        else:
            failed += 1
            print(f"FAIL {skill_dir.name}")
            for err in errors:
                print(f"  - {err}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
