#!/usr/bin/env python3
"""Verify that a Three.js game report's evidence actually exists on disk.

Manifest mode checks a declared capture set from one run. Legacy report mode
checks cited files and discovered inspector reports; it cannot establish capture
coverage, freshness, visual quality, or that a build command succeeded.

    python3 check_evidence.py ./my-game
    python3 check_evidence.py ./my-game --report artifacts/final-evidence.md
    python3 check_evidence.py ./my-game --manifest artifacts/evidence.json

Exit 0 when every cited artifact resolves; exit 1 with the specific failures.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

# Extensions worth resolving, with the byte floor below which a file is a stub
# rather than evidence. A 0-byte PNG resolves but proves nothing; these floors
# are set just above "empty or truncated write" for each format.
MEDIA_FLOORS = {
    ".png": 1024,
    ".jpg": 1024,
    ".jpeg": 1024,
    ".webp": 512,
    ".gif": 512,
    ".glb": 1024,
    ".gltf": 512,
    ".fbx": 1024,
    ".obj": 512,
    ".mp3": 512,
    ".wav": 512,
    ".ogg": 512,
    ".m4a": 512,
    ".mp4": 1024,
    ".webm": 1024,
    ".json": 2,
}

# A path-like token: at least one directory separator, ending in a known
# extension. Requiring the separator keeps prose words with dots out.
PATH_TOKEN = re.compile(
    r"(?<![\w/.:~-])((?:/|~/|\.{1,2}/)?(?:[\w.-]+/)+[\w.-]+\.(?:"
    + "|".join(ext.lstrip(".") for ext in MEDIA_FLOORS)
    + r"))(?![\w/])",
    re.IGNORECASE,
)
MARKDOWN_LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*(?:<([^>\n]+)>|([^\n]+?))\s*\)")
INLINE_CODE = re.compile(r"`([^`\n]+)`")
COMMAND_NAMES = {"python", "python3", "node", "npm", "npx", "uv", "bash", "sh", "zsh", "powershell", "pwsh"}

BUILD_CLAIM = re.compile(
    r"production build|npm run build|vite build|preview server|dist/", re.IGNORECASE
)

# Paths that name the tooling rather than the game's own evidence.
SKIP_PREFIXES = ("node_modules/", "skills/", "scripts/", "src/", "tests/")


def find_paths(report_text: str) -> list[str]:
    """Read link/code destinations intact, then unquoted legacy path tokens."""
    candidates: list[tuple[int, str]] = []
    remaining = list(report_text)
    for pattern in (MARKDOWN_LINK, INLINE_CODE):
        for match in pattern.finditer("".join(remaining)):
            raw = next(group for group in match.groups() if group is not None).strip()
            if pattern is INLINE_CODE:
                try:
                    words = shlex.split(raw)
                except ValueError:
                    words = []
                is_command = bool(words) and (
                    words[0] in COMMAND_NAMES or any(word.startswith("--") for word in words[1:])
                )
                if is_command or raw.startswith(("https://", "http://")):
                    remaining[match.start():match.end()] = " " * (match.end() - match.start())
                    continue
            if pattern is MARKDOWN_LINK:
                raw = re.sub(r"\s+[\"'].*[\"']$", "", raw)
                parsed = urlsplit(raw)
                if parsed.scheme or parsed.netloc:
                    raw = ""
                else:
                    raw = unquote(parsed.path)
            if Path(raw).suffix.lower() in MEDIA_FLOORS:
                candidates.append((match.start(), raw))
                remaining[match.start():match.end()] = " " * (match.end() - match.start())
            elif pattern is MARKDOWN_LINK:
                remaining[match.start():match.end()] = " " * (match.end() - match.start())
    candidates.extend((match.start(), match.group(1)) for match in PATH_TOKEN.finditer("".join(remaining)))
    return list(dict.fromkeys(
        candidate for _, candidate in sorted(candidates)
        if not candidate.lower().startswith(SKIP_PREFIXES)
    ))


def resolve(candidate: str, roots: list[Path], *, allow_cwd: bool = True) -> Path | None:
    """Resolve a cited path against each root, then as given."""
    expanded = Path(candidate).expanduser()
    if expanded.is_absolute():
        return expanded if expanded.exists() else None
    for root in roots:
        resolved = root / expanded
        if resolved.exists():
            return resolved
    direct = Path(candidate)
    return direct if allow_cwd and direct.exists() else None


def check_artifacts(paths: list[str], roots: list[Path], *, allow_cwd: bool = True) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    confirmed: list[str] = []
    for candidate in paths:
        resolved = resolve(candidate, roots, allow_cwd=allow_cwd)
        if resolved is None:
            failures.append(f"cited path does not exist: {candidate}")
            continue
        if not resolved.is_file():
            failures.append(f"cited path is not a file: {candidate}")
            continue
        try:
            size = resolved.stat().st_size
        except OSError as exc:
            failures.append(f"cannot inspect {candidate}: {exc}")
            continue
        floor = MEDIA_FLOORS.get(resolved.suffix.lower(), 1)
        if size < floor:
            failures.append(
                f"cited path is a stub ({size} bytes, expected >= {floor}): {candidate}"
            )
            continue
        confirmed.append(f"{candidate} ({size:,} bytes)")
    return confirmed, failures


def find_inspector_reports(project: Path) -> list[Path]:
    """JSON files written by inspect-threejs-canvas.mjs, wherever they landed."""
    found: list[Path] = []
    for path in project.rglob("*.json"):
        if "node_modules" in path.parts or path.name == "package-lock.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            continue
        if isinstance(data, dict) and "screenshotPath" in data and "result" in data:
            found.append(path)
    return sorted(found)


def read_json_object(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data


def inspect_report(report: Path, project: Path, data: dict, *, strict_paths: bool = False) -> tuple[list[str], list[str]]:
    result = data.get("result")
    if not isinstance(result, dict) or result.get("ok") is not True:
        return [], [f"inspector {report} does not report a non-blank canvas"]
    shot = data.get("screenshotPath")
    if not isinstance(shot, str) or not shot.strip():
        return [], [f"inspector {report} has no screenshotPath"]
    roots = [project] if strict_paths else [project, report.parent]
    _, failures = check_artifacts([shot], roots, allow_cwd=not strict_paths)
    for field in ("consoleErrors", "pageErrors"):
        errors = data.get(field, [])
        if not isinstance(errors, list) or errors:
            failures.append(f"inspector {report} has {field}: {errors}")
    if failures:
        return [], failures
    metrics = result.get("metrics") or {}
    entropy = metrics.get("colorEntropyBits") if isinstance(metrics, dict) else None
    detail = f", colorEntropyBits={entropy:.2f}" if isinstance(entropy, (int, float)) else ""
    label = f"{data.get('mode', '?')}/{data.get('state') or 'default'}"
    return [f"{report} ({label}) non-blank{detail}"], []


def check_inspector(project: Path) -> tuple[list[str], list[str]]:
    reports = find_inspector_reports(project)
    if not reports:
        return [], [
            "no canvas inspector JSON found under "
            f"{project} - run `npm run inspect:canvas` or "
            "inspect-threejs-canvas.mjs before claiming visual evidence"
        ]

    confirmed: list[str] = []
    failures: list[str] = []
    for report in reports:
        try:
            ok, bad = inspect_report(report, project, read_json_object(report))
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            ok, bad = [], [f"cannot read inspector {report}: {exc}"]
        confirmed.extend(ok)
        failures.extend(bad)

    return confirmed, failures


def check_manifest(project: Path, manifest_path: Path) -> tuple[list[str], list[str]]:
    """Validate only the reports explicitly assigned to this run and state set."""
    try:
        manifest = read_json_object(manifest_path)
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        return [], [f"cannot read manifest {manifest_path}: {exc}"]
    run_id = manifest.get("runId")
    captures = manifest.get("captures")
    if type(manifest.get("version")) is not int or manifest["version"] != 1:
        return [], ["manifest version must be 1"]
    if not isinstance(run_id, str) or not run_id.strip():
        return [], ["manifest requires a nonempty runId"]
    if not isinstance(captures, list) or not captures:
        return [], ["manifest requires a nonempty captures list"]

    confirmed: list[str] = []
    failures: list[str] = []
    seen: set[tuple[str, str | None]] = set()
    reports: set[Path] = set()
    for index, capture in enumerate(captures):
        if not isinstance(capture, dict):
            failures.append(f"capture {index} must be an object")
            continue
        mode, state, report_name = capture.get("mode"), capture.get("state"), capture.get("report")
        if mode not in ("desktop", "mobile") or "state" not in capture or not (
            state is None or isinstance(state, str) and state.strip()
        ) or not isinstance(report_name, str) or not report_name.strip():
            failures.append(f"capture {index} requires mode desktop|mobile, state string|null, and report path")
            continue
        key = (mode, state)
        if key in seen:
            failures.append(f"duplicate capture {mode}/{state or 'default'}")
            continue
        seen.add(key)
        report = Path(report_name).expanduser()
        report = (report if report.is_absolute() else project / report).resolve()
        if report in reports:
            failures.append(f"inspector report reused for multiple captures: {report}")
            continue
        reports.add(report)
        try:
            data = read_json_object(report)
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            failures.append(f"cannot read declared capture {report}: {exc}")
            continue
        expected = {"runId": run_id, "mode": mode, "state": state,
                    "requestedState": state, "appliedState": state}
        mismatches = [field for field, value in expected.items() if field not in data or data[field] != value]
        if mismatches:
            failures.append(f"inspector {report} mismatches declared capture: {', '.join(mismatches)}")
            continue
        ok, bad = inspect_report(report, project, data, strict_paths=True)
        confirmed.extend(ok)
        failures.extend(bad)

    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list) or any(not isinstance(item, str) or not item.strip() for item in artifacts):
        failures.append("manifest artifacts must be a list of nonempty file paths")
    else:
        ok, bad = check_artifacts(artifacts, [project], allow_cwd=False)
        confirmed.extend(ok)
        failures.extend(bad)
    return confirmed, failures


def check_build(project: Path) -> tuple[list[str], list[str]]:
    dist = project / "dist"
    if not dist.is_dir():
        return [], [
            "report claims a production build but there is no dist/ directory in "
            f"{project}"
        ]
    entries = [p for p in dist.rglob("*") if p.is_file()]
    if not entries:
        return [], [f"report claims a production build but {dist} is empty"]
    return [f"dist/ present ({len(entries)} files)"], []


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify a Three.js game report's cited evidence exists on disk."
    )
    parser.add_argument("project", help="game project directory")
    parser.add_argument("--manifest", help="version 1 JSON capture manifest, relative to the project or absolute")
    parser.add_argument(
        "--report",
        help="markdown report whose cited paths should be resolved "
        "(relative to the project directory unless absolute)",
    )
    parser.add_argument(
        "--skip-inspector",
        action="store_true",
        help="do not require canvas inspector output (use for non-visual work)",
    )
    args = parser.parse_args()
    if args.manifest and args.skip_inspector:
        parser.error("--manifest requires inspector verification; do not combine with --skip-inspector")

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        print(f"Not a directory: {project}", file=sys.stderr)
        return 1

    confirmed: list[str] = []
    failures: list[str] = []

    if args.report:
        report_path = Path(args.report).expanduser()
        if not report_path.is_absolute():
            candidate = project / report_path
            report_path = candidate if candidate.exists() else report_path
        if not report_path.exists():
            print(f"Missing report file: {report_path}", file=sys.stderr)
            return 1

        try:
            text = report_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            print(f"Cannot read report {report_path}: {exc}", file=sys.stderr)
            return 1
        roots = [project, report_path.parent, Path.cwd()]

        cited = find_paths(text)
        if cited:
            ok, bad = check_artifacts(cited, roots)
            confirmed.extend(ok)
            failures.extend(bad)
        else:
            failures.append(
                f"{report_path.name} cites no artifact paths - a report with no "
                "screenshots, models, or audio files is not evidence"
            )

        if BUILD_CLAIM.search(text):
            ok, bad = check_build(project)
            confirmed.extend(ok)
            failures.extend(bad)

    if args.manifest:
        manifest_path = Path(args.manifest).expanduser()
        if not manifest_path.is_absolute():
            manifest_path = project / manifest_path
        ok, bad = check_manifest(project, manifest_path)
        confirmed.extend(ok)
        failures.extend(bad)
    elif not args.skip_inspector:
        print("Legacy mode checks existing files, not current-run coverage; use --manifest for capture verification.")
        ok, bad = check_inspector(project)
        confirmed.extend(ok)
        failures.extend(bad)

    for line in confirmed:
        print(f"  ok    {line}")
    for line in failures:
        print(f"  FAIL  {line}")

    print()
    if failures:
        print(f"Evidence check failed: {len(failures)} problem(s), {len(confirmed)} confirmed.")
        return 1
    print(f"Evidence check passed: {len(confirmed)} artifact(s) confirmed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
