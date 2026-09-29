#!/usr/bin/env python3
"""Small Meshy OpenAPI client for skill-driven 3D asset generation."""

from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import csv
from email.utils import parsedate_to_datetime
import hashlib
from http.client import IncompleteRead
import json
import math
import mimetypes
import os
from pathlib import Path
import struct
import sys
import tempfile
import time
from typing import Any, Callable, Iterator
from urllib import error, parse, request

BASE_URL = "https://api.meshy.ai"

ENDPOINTS = {
    "text": "/openapi/v2/text-to-3d",
    "image": "/openapi/v1/image-to-3d",
    "multi-image": "/openapi/v1/multi-image-to-3d",
    "retexture": "/openapi/v1/retexture",
    "remesh": "/openapi/v1/remesh",
    "rig": "/openapi/v1/rigging",
    "animate": "/openapi/v1/animations",
    "motion": "/openapi/v1/text-to-motion",
}
KIND_ORDER = ("text", "image", "multi-image", "rig", "animate", "retexture", "remesh", "motion")

FINAL_STATUSES = {"SUCCEEDED", "FAILED", "CANCELED"}
STAGE_STATES = FINAL_STATUSES | {"prepared", "submitting", "submitted", "unknown_submission", "rejected"}
FORMATS = ("glb", "fbx", "obj", "stl", "usdz", "3mf", "blend")
DATA_URI_WARN_BYTES = 9 * 1024 * 1024
GET_ATTEMPTS = 4
RETRY_DELAY_CAP = 60

ACTION_ALIASES = {
    "walk": "walking",
    "run": "running",
    "jump": "jumping",
    "climb": "climbing",
    "dance": "dancing",
    "punch": "punching",
    "block": "blocking",
    "die": "dying",
    "death": "dying",
    "hit": "gettinghit",
    "cast": "castingspell",
    "attack": "attackingwithweapon",
    "swim": "swimming",
    "fall": "fallingfreely",
    "turn": "turningaround",
    "crouch": "crouchwalking",
    "pickup": "pickingupitem",
    "sleep": "sleeping",
}

RIG_FACE_LIMIT = 300_000
RIG_FACE_BUDGET = 60_000

ANIMATIONS_CSV = Path(__file__).resolve().parent.parent / "references" / "animations.csv"

HUMANOID_CORE = ("Hips", "Spine", "Head")
HUMANOID_PAIRED = ("Arm", "ForeArm", "Hand", "UpLeg", "Leg", "Foot")


class MeshyError(RuntimeError):
    def __init__(self, message: str, category: str = "invalid_input", retry_after: float | None = None):
        super().__init__(message)
        self.category = category
        self.retry_after = retry_after


def eprint(*parts: object) -> None:
    print(*parts, file=sys.stderr)


def api_key_from(args: argparse.Namespace) -> str:
    key = getattr(args, "api_key", None) or os.environ.get("MESHY_API_KEY")
    if not key:
        raise MeshyError(
            "Missing API key. Set MESHY_API_KEY or pass --api-key. If the export lives in an "
            "interactive-only profile (~/.bashrc below its non-interactive guard), run through: "
            "bash -ic 'python3 ...'",
            "missing_credentials",
        )
    return key


def error_category(http_status: int | None = None, body: str = "") -> str:
    lowered = body.lower()
    if http_status == 402 or "insufficient credit" in lowered or "not enough credit" in lowered:
        return "exhausted_credits"
    if http_status in {401, 403}:
        return "credentials"
    if http_status in {408, 425, 429} or (http_status is not None and http_status >= 500):
        return "transient"
    return "invalid_input"


def retry_after_seconds(headers: Any) -> float | None:
    value = headers.get("Retry-After") if headers else None
    if value is None:
        return None
    try:
        delay = float(value)
    except ValueError:
        try:
            delay = parsedate_to_datetime(value).timestamp() - time.time()
        except (TypeError, ValueError, OverflowError):
            return None
    return min(RETRY_DELAY_CAP, max(0, delay))


def safe_get(operation: Callable[[], Any]) -> Any:
    """Retry only idempotent reads, never a task submission."""
    for attempt in range(GET_ATTEMPTS):
        try:
            return operation()
        except MeshyError as exc:
            if exc.category != "transient" or attempt + 1 == GET_ATTEMPTS:
                raise
            delay = min(RETRY_DELAY_CAP, max(2 ** attempt, exc.retry_after or 0))
            eprint(f"Transient GET failure; retry {attempt + 1}/{GET_ATTEMPTS - 1} in {delay:g}s")
            time.sleep(delay)


def request_once(req: request.Request, timeout: int) -> tuple[bytes, Any]:
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), resp.headers
    except error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except (OSError, IncompleteRead):
            body = ""
        finally:
            exc.close()
        category = error_category(exc.code, body)
        if req.get_method() == "GET" and not req.full_url.startswith(BASE_URL) and exc.code in {401, 403}:
            category = "expired_download"
        # A timed-out or 5xx POST may have created the task before the error arrived.
        if req.get_method() != "GET" and category == "transient" and exc.code != 429:
            category = "unknown_submission"
        raise MeshyError(
            f"HTTP {exc.code} {exc.reason}; {category}: {body[:400]}", category,
            retry_after_seconds(exc.headers),
        ) from exc
    except (error.URLError, OSError, IncompleteRead) as exc:
        category = "transient" if req.get_method() == "GET" else "unknown_submission"
        raise MeshyError(f"{req.get_method()} interrupted; {category}.", category) from exc


def api_request(api_key: str, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(f"{BASE_URL}{path}", data=body, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    if payload is not None:
        req.add_header("Content-Type", "application/json")

    def fetch() -> Any:
        raw, _headers = request_once(req, 120)
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            category = "transient" if method == "GET" else "unknown_submission"
            raise MeshyError("Invalid JSON response from Meshy.", category) from exc

    return safe_get(fetch) if method == "GET" else fetch()


def endpoint_for(kind: str) -> str:
    if kind not in ENDPOINTS:
        raise MeshyError(f"Unknown task kind {kind!r}. Valid: {', '.join(ENDPOINTS)}")
    return ENDPOINTS[kind]


def create_task(api_key: str, kind: str, payload: dict[str, Any]) -> str:
    data = api_request(api_key, "POST", endpoint_for(kind), payload)
    task_id = data.get("result") if isinstance(data, dict) else None
    if isinstance(task_id, dict):
        task_id = task_id.get("id")
    if not isinstance(task_id, str) or not task_id:
        raise MeshyError(f"Unexpected create response: {json.dumps(data)[:400]}", "unknown_submission")
    return task_id


def get_task(api_key: str, kind: str, task_id: str) -> dict[str, Any]:
    data = api_request(api_key, "GET", f"{endpoint_for(kind)}/{parse.quote(task_id)}")
    # Rig/animate tasks carry their assets in a nested "result" object, so only unwrap an
    # envelope that is not itself a task.
    if isinstance(data, dict) and "status" not in data and isinstance(data.get("result"), dict):
        data = data["result"]
    if not isinstance(data, dict) or not isinstance(data.get("status"), str):
        raise MeshyError(f"Unexpected task response: {json.dumps(data)[:400]}", "transient")
    return data


def discover_kind(api_key: str, task_id: str, hint: str | None = None) -> tuple[str, dict[str, Any]]:
    if hint and hint not in ENDPOINTS:
        raise MeshyError(f"Unknown --kind {hint!r}. Valid: {', '.join(ENDPOINTS)}")
    order = [hint] if hint else list(KIND_ORDER)
    for kind in order:
        try:
            return kind, get_task(api_key, kind, task_id)
        except MeshyError as exc:
            if "HTTP 404" in str(exc) or "HTTP 400" in str(exc):
                continue
            raise
    raise MeshyError(f"Task {task_id} not found on any endpoint. Pass --kind to disambiguate.")


def wait_for_task(api_key: str, kind: str, task_id: str, interval: int, timeout: int,
                  on_update: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Poll until the task reaches a final status; a failed task is returned, not raised."""
    deadline = time.time() + timeout
    last = ""
    while True:
        task = get_task(api_key, kind, task_id)
        if on_update is not None:
            on_update(task)
        status = str(task.get("status", "UNKNOWN"))
        line = f"{status} {task.get('progress', 0)}%"
        if line != last:
            eprint(f"[{kind}:{task_id}] {line}")
            last = line
        if status in FINAL_STATUSES:
            return task
        if time.time() > deadline:
            raise MeshyError(f"Timed out after {timeout}s waiting for {task_id} (last: {line})", "transient")
        time.sleep(interval)


def require_success(task: dict[str, Any]) -> dict[str, Any]:
    status = str(task.get("status", "UNKNOWN"))
    if status == "SUCCEEDED":
        return task
    message = str((task.get("task_error") or {}).get("message", "")).strip()
    category = "exhausted_credits" if "credit" in message.lower() else "task_failed"
    raise MeshyError(f"Task {task.get('id')} ended {status}: {message}".strip(), category)


def safe_name(value: str) -> str:
    out = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value).strip("-")
    return (out or "meshy")[:60]


def collect_urls(node: Any, prefix: str = "") -> list[tuple[str, str]]:
    """Walk a task object and return (label, url) for every downloadable asset."""
    found: list[tuple[str, str]] = []
    if isinstance(node, str):
        if node.startswith("http") and prefix:
            found.append((prefix, node))
        return found
    if isinstance(node, dict):
        for key, value in node.items():
            label = key[:-4] if key.endswith("_url") else key
            found.extend(collect_urls(value, f"{prefix}-{label}" if prefix else label))
        return found
    if isinstance(node, list):
        for idx, value in enumerate(node):
            found.extend(collect_urls(value, f"{prefix}{idx}" if prefix else str(idx)))
    return found


def extension_for(url: str, label: str, content_type: str | None) -> str:
    path = parse.urlparse(url).path
    ext = Path(path).suffix
    if ext and len(ext) <= 6:
        return ext
    for fmt in FORMATS + ("png", "jpg", "gif", "bvh", "mtl"):
        if label.endswith(fmt) or f"-{fmt}" in label:
            return f".{fmt}"
    if content_type:
        guess = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guess:
            return guess
    return ".bin"


def download_one(url: str, out_dir: Path, base: str, label: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload, headers = safe_get(lambda: request_once(request.Request(url, method="GET"), 300))
    target = out_dir / f"{base}-{safe_name(label)}{extension_for(url, label, headers.get('Content-Type'))}"
    target.write_bytes(payload)
    return target


def clean_label(label: str) -> str:
    for noise in ("model_urls-", "result-", "urls-"):
        label = label.replace(noise, "")
    return label


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path.resolve()), "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def file_matches(record: dict[str, Any]) -> bool:
    try:
        path = Path(record["path"])
        return (path.is_file() and record["size"] > 0 and path.stat().st_size == record["size"]
                and hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"])
    except (OSError, KeyError, TypeError):
        return False


def download_outputs(task: dict[str, Any], out_dir: Path, base: str | None = None,
                     formats: set[str] | None = None, job: "Checkpoint | None" = None,
                     stage_name: str = "task") -> list[Path]:
    """formats filters model files only (Meshy returns every format it baked);
    thumbnails, textures, rigs and clips always come through."""
    base = base or safe_name(str(task.get("id", "task"))[:12])
    records = job.stage(stage_name)["files"] if job is not None else {}
    written: list[Path] = []
    for raw_label, url in collect_urls(task):
        if raw_label.startswith(("task_error", "preceding")):
            continue
        label = clean_label(raw_label)
        suffix = label.rsplit("-", 1)[-1].rsplit("_", 1)[-1]
        if formats and suffix in FORMATS and suffix not in formats:
            continue
        try:
            path = download_one(url, out_dir, base, label)
        except MeshyError as exc:
            # Expired or throttled links are recoverable from a refreshed task, so surface
            # them; a single malformed asset URL must not kill the rest of the batch.
            if exc.category in {"expired_download", "transient", "credentials", "exhausted_credits"}:
                raise
            eprint(f"  ! failed {label}: {exc}")
            continue
        except OSError as exc:
            eprint(f"  ! failed {label}: {exc}")
            continue
        written.append(path)
        records[label] = file_record(path)
        print(f"  saved {path}")
    if job is not None:
        job.stage(stage_name)["downloads_complete"] = bool(written)
        job.save()
    if not written:
        eprint("  (no downloadable URLs in task result)")
    return written


def image_ref(value: str) -> str:
    """Meshy takes a public URL or a base64 data URI; local files become data URIs."""
    if value.startswith(("http://", "https://", "data:")):
        return value
    path = Path(value).expanduser()
    if not path.is_file():
        raise MeshyError(f"File not found: {path}")
    size = path.stat().st_size
    if size > DATA_URI_WARN_BYTES:
        eprint(f"! {path.name} is {size / 1e6:.1f} MB; large data URIs may be rejected.")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def csv_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def load_animation_library() -> list[dict[str, str]]:
    if not ANIMATIONS_CSV.is_file():
        raise MeshyError(f"Animation library missing: {ANIMATIONS_CSV}")
    with ANIMATIONS_CSV.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def resolve_action(token: str) -> tuple[int, str]:
    token = token.strip()
    library = load_animation_library()
    if token.isdigit():
        wanted = int(token)
        for row in library:
            if int(row["action_id"]) == wanted:
                return wanted, row["name"]
        return wanted, "id-not-in-bundled-library"
    lower = ACTION_ALIASES.get(token.lower(), token.lower())
    exact = [r for r in library if r["name"].lower() == lower]
    if exact:
        return int(exact[0]["action_id"]), exact[0]["name"]
    # A bare gameplay word ("walk", "run", "jump") means the plain locomotion clip, not the
    # first alphabetical name containing it - match the subcategory and take the canonical
    # lowest id (Idle=0, Walking_Woman=1, Run_02=14) instead of Running_Reload or walking_2.
    subcat = [r for r in library if r["subcategory"].lower() == lower]
    if subcat:
        best = min(subcat, key=lambda r: int(r["action_id"]))
        return int(best["action_id"]), best["name"]
    starts = [r for r in library if r["name"].lower().startswith(lower)]
    pool = starts or [r for r in library if lower in r["name"].lower()]
    if not pool:
        raise MeshyError(
            f"No animation matches {token!r}. Browse with: meshy_3d_asset.py list-animations --search {token}"
        )
    pool.sort(key=lambda r: (len(r["name"]), int(r["action_id"])))
    best = pool[0]
    if len(pool) > 1:
        others = ", ".join(f"{r['name']}({r['action_id']})" for r in pool[1:6])
        eprint(f"  {token!r} -> {best['name']} (id {best['action_id']}); other matches: {others}")
    return int(best["action_id"]), best["name"]


CHECKPOINT_ARGS = set("""
command name prompt negative_prompt art_style pose_mode seed no_refine ai_model model_type
topology target_polycount decimation_mode no_remesh ultra auto_size origin_at alpha_thumbnail
target_formats texture_resolution texture_prompt texture_image pbr keep_lighting image images
no_texture no_image_enhancement multi_view_thumbnails preview_task_id input_task_id model_url
text_style_prompt image_style multiview_images original_uv height_meters rig_task_id animations
motion_task_id fps duration mode model_task_id wait download out_dir download_formats
all_formats interval timeout
""".split())
PATH_ARGS = ("image", "texture_image", "image_style", "model_url")
LIST_PATH_ARGS = ("images", "multiview_images")
RESUMABLE_STAGES = {
    "text": {"preview", "refine"},
    "refine": {"task"},
    "image": {"model"},
    "multi-image": {"model"},
    "retexture": {"task"},
    "remesh": {"task"},
    "rig": {"task"},
    "motion": {"task"},
}
CHARACTER_STAGES = {"preview", "refine", "remesh", "rig", "rig-remeshed"}
INTEGER_ARGS = {"seed", "target_polycount", "decimation_mode", "fps", "interval", "timeout"}
NUMERIC_ARGS = {"height_meters", "duration"}


def portable_reference(value: str | None) -> str | None:
    """Local paths survive a resume; a signed URL or inline data URI does not.

    A reference that cannot be restored is dropped rather than stored, so a resume
    re-supplies it explicitly instead of replaying a link that has since expired.
    """
    if not value:
        return value
    items = [item.strip() for item in value.split(",") if item.strip()]
    resolved = []
    for item in items:
        if item.startswith(("http://", "https://", "data:")):
            return None
        resolved.append(str(Path(item).expanduser().resolve()))
    return ",".join(resolved)


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


class Checkpoint:
    """An operational journal: no credentials, image data, or signed asset URLs.

    A persisted 'submitting' intent without an accepted ID is ambiguous, even if the
    process died before the request left. Only explicit task-ID reconciliation clears
    it; rerunning the command never submits a replacement paid task.
    """

    def __init__(self, path: Path | None, data: dict[str, Any]):
        self.path = path
        self.data = data

    def save(self) -> None:
        if self.path is not None:
            atomic_write(self.path, json.dumps(self.data, indent=2).encode("utf-8"))

    def stage(self, name: str) -> dict[str, Any]:
        return self.data["stages"].setdefault(name, {"state": "prepared", "files": {}})

    def record_task(self, name: str, kind: str, task: dict[str, Any]) -> None:
        stage = self.stage(name)
        status = task.get("status")
        record: dict[str, Any] = {"id": stage.get("task_id") or task.get("id"), "status": status}
        if type(task.get("progress")) is int:
            record["progress"] = task["progress"]
        stage["kind"] = kind
        stage["task"] = record
        stage["state"] = status if status in FINAL_STATUSES else "submitted"
        stage.pop("last_error", None)
        self.save()


@contextmanager
def checkpoint_file(path: Path) -> Iterator[None]:
    """OS locks release on process death; the stable lock file is intentionally kept."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = Path(f"{path}.lock").open("a+b")
    except OSError as exc:
        raise MeshyError(f"Cannot use checkpoint path {path}: {exc.strerror}.", "checkpoint_error") from exc
    with handle:
        if os.name == "nt":
            import msvcrt
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            acquire = lambda: msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            release = lambda: msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            acquire = lambda: fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            release = lambda: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        try:
            acquire()
        except OSError as exc:
            raise MeshyError(f"Checkpoint already in use: {path}", "checkpoint_error") from exc
        try:
            yield
        finally:
            handle.seek(0)
            release()


@contextmanager
def job_context(args: argparse.Namespace) -> Iterator[Checkpoint]:
    if getattr(args, "_job", None) is not None:
        yield args._job
        return
    options = {key: value for key, value in vars(args).items() if key in CHECKPOINT_ARGS}
    options["out_dir"] = str(Path(args.out_dir).expanduser().resolve())
    for key in PATH_ARGS + LIST_PATH_ARGS:
        if key in options:
            options[key] = portable_reference(options[key])
    data = {"version": 1, "command": args.command, "args": options, "stages": {}}
    checkpoint = getattr(args, "checkpoint", None)
    if checkpoint is None:
        yield Checkpoint(None, data)
        return
    path = Path(checkpoint).expanduser().resolve()
    with checkpoint_file(path):
        if path.exists():
            raise MeshyError(f"Checkpoint already exists; use resume {path}.", "checkpoint_error")
        job = Checkpoint(path, data)
        job.save()
        args.out_dir = options["out_dir"]
        yield job


def ensure_task(api_key: str, job: Checkpoint, name: str, kind: str,
                payload: dict[str, Any] | Callable[[], dict[str, Any]]) -> str:
    stage = job.stage(name)
    if stage.get("task_id"):
        return stage["task_id"]
    if stage["state"] in {"submitting", "unknown_submission"}:
        raise MeshyError(
            f"Stage {name!r} has an uncertain POST outcome. Find its task ID in the Meshy "
            "dashboard, then use resume CHECKPOINT --task-id ID to reconcile it. No new task "
            "was submitted.",
            "unknown_submission",
        )
    built = payload() if callable(payload) else payload
    intent = {"kind": kind}
    for key in ("preview_task_id", "input_task_id", "rig_task_id", "motion_task_id", "action_id"):
        if key in built:
            intent[key] = built[key]
    stage["kind"] = kind
    stage["request"] = intent
    stage["state"] = "submitting"
    stage.pop("last_error", None)
    job.save()
    try:
        task_id = create_task(api_key, kind, built)
    except BaseException as exc:
        category = exc.category if isinstance(exc, MeshyError) else "unknown_submission"
        stage["state"] = "unknown_submission" if category == "unknown_submission" else "rejected"
        stage["last_error"] = category
        job.save()
        raise
    stage.update(task_id=task_id, state="submitted")
    job.save()
    return task_id


def finish_stage(api_key: str, job: Checkpoint, name: str, args: argparse.Namespace,
                 out_dir: Path | None = None, base: str | None = None,
                 formats: set[str] | None = None) -> tuple[dict[str, Any], list[Path]]:
    stage = job.stage(name)
    task_id = stage["task_id"]
    kind = stage["kind"]
    task = stage.get("task")
    fresh_task = False
    try:
        if task is None or task.get("status") not in FINAL_STATUSES:
            task = wait_for_task(api_key, kind, task_id, args.interval, args.timeout,
                                 on_update=lambda result: job.record_task(name, kind, result))
            job.record_task(name, kind, task)
            fresh_task = True
        if task.get("status") != "SUCCEEDED" or out_dir is None:
            return task, []
        records = stage["files"]
        if stage.get("downloads_complete") and records and all(file_matches(r) for r in records.values()):
            return task, [Path(record["path"]) for record in records.values()]
        if not fresh_task:
            # Meshy asset links expire in about three days; read them from the task again.
            task = get_task(api_key, kind, task_id)
            job.record_task(name, kind, task)
            if task.get("status") != "SUCCEEDED":
                return task, []
        return task, download_outputs(task, out_dir, base, formats, job=job, stage_name=name)
    except MeshyError as exc:
        stage["last_error"] = exc.category
        job.save()
        raise


def apply_optional(payload: dict[str, Any], args: argparse.Namespace, mapping: dict[str, str]) -> None:
    for attr, field in mapping.items():
        value = getattr(args, attr, None)
        if value is None or value is False:
            continue
        payload[field] = value


def wanted_formats(args: argparse.Namespace) -> set[str] | None:
    if getattr(args, "all_formats", False):
        return None
    return set(csv_list(getattr(args, "download_formats", None) or "glb"))


def run_single(api_key: str, job: Checkpoint, args: argparse.Namespace, kind: str, name: str,
               payload: dict[str, Any] | Callable[[], dict[str, Any]],
               base: str | None = None) -> dict[str, Any] | None:
    task_id = ensure_task(api_key, job, name, kind, payload)
    print(f"{kind} task: {task_id}")
    if not getattr(args, "wait", False):
        print(f"Poll with: status {task_id} --kind {kind}")
        return None
    out_dir = Path(args.out_dir) if getattr(args, "download", False) else None
    task, _paths = finish_stage(api_key, job, name, args, out_dir, base, wanted_formats(args))
    require_success(task)
    print(f"credits: {task.get('consumed_credits')}")
    return task


def apply_remesh_flag(payload: dict[str, Any], args: argparse.Namespace) -> None:
    """target_polycount and topology are IGNORED unless should_remesh is on, and its
    default varies by model: a 20k request came back with 1.9M faces (too dense to rig)."""
    if getattr(args, "no_remesh", False):
        payload["should_remesh"] = False
    elif payload.get("target_polycount") or payload.get("topology"):
        payload["should_remesh"] = True


def build_text_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {"mode": "preview", "prompt": args.prompt}
    apply_optional(payload, args, {
        "ai_model": "ai_model",
        "model_type": "model_type",
        "art_style": "art_style",
        "pose_mode": "pose_mode",
        "topology": "topology",
        "target_polycount": "target_polycount",
        "decimation_mode": "decimation_mode",
        "negative_prompt": "negative_prompt",
        "seed": "seed",
        "ultra": "ultra_mode",
        "auto_size": "auto_size",
        "origin_at": "origin_at",
        "alpha_thumbnail": "alpha_thumbnail",
    })
    apply_remesh_flag(payload, args)
    formats = csv_list(getattr(args, "target_formats", None))
    if formats:
        payload["target_formats"] = formats
    return payload


def build_refine_payload(args: argparse.Namespace, preview_task_id: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"mode": "refine", "preview_task_id": preview_task_id}
    apply_optional(payload, args, {
        "ai_model": "ai_model",
        "texture_resolution": "texture_resolution",
        "texture_prompt": "texture_prompt",
        "pbr": "enable_pbr",
        "auto_size": "auto_size",
        "origin_at": "origin_at",
        "alpha_thumbnail": "alpha_thumbnail",
    })
    if getattr(args, "texture_image", None):
        payload["texture_image_url"] = image_ref(args.texture_image)
    if getattr(args, "keep_lighting", False):
        payload["remove_lighting"] = False
    formats = csv_list(getattr(args, "target_formats", None))
    if formats:
        payload["target_formats"] = formats
    return payload


def cmd_text(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    with job_context(args) as job:
        run_text(api_key, job, args)


def run_text(api_key: str, job: Checkpoint, args: argparse.Namespace) -> str:
    base = safe_name(args.name or args.prompt[:40])
    out_dir = Path(args.out_dir)
    preview_id = ensure_task(api_key, job, "preview", "text", lambda: build_text_payload(args))
    print(f"preview task: {preview_id}")
    if not args.wait:
        print(f"Poll with: status {preview_id} --kind text")
        print(f"Then texture with: refine --preview-task-id {preview_id} --wait --download")
        return preview_id
    preview_target = out_dir if (args.download and args.no_refine) else None
    preview, _ = finish_stage(api_key, job, "preview", args, preview_target,
                              f"{base}-preview", wanted_formats(args))
    require_success(preview)
    if args.no_refine:
        return preview_id
    refine_id = ensure_task(api_key, job, "refine", "text", lambda: build_refine_payload(args, preview_id))
    print(f"refine task: {refine_id}")
    task, _ = finish_stage(api_key, job, "refine", args, out_dir if args.download else None,
                           base, wanted_formats(args))
    require_success(task)
    print(f"credits: {task.get('consumed_credits')}")
    return refine_id


def cmd_refine(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    with job_context(args) as job:
        run_single(api_key, job, args, "text", "task",
                   lambda: build_refine_payload(args, args.preview_task_id),
                   safe_name(args.name or "refine"))


def build_image_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    apply_optional(payload, args, {
        "ai_model": "ai_model",
        "model_type": "model_type",
        "topology": "topology",
        "target_polycount": "target_polycount",
        "decimation_mode": "decimation_mode",
        "texture_resolution": "texture_resolution",
        "texture_prompt": "texture_prompt",
        "pbr": "enable_pbr",
        "pose_mode": "pose_mode",
        "ultra": "ultra_mode",
        "auto_size": "auto_size",
        "origin_at": "origin_at",
        "alpha_thumbnail": "alpha_thumbnail",
        "multi_view_thumbnails": "multi_view_thumbnails",
    })
    if args.no_texture:
        payload["should_texture"] = False
    apply_remesh_flag(payload, args)
    if args.no_image_enhancement:
        payload["image_enhancement"] = False
    if args.keep_lighting:
        payload["remove_lighting"] = False
    if getattr(args, "texture_image", None):
        payload["texture_image_url"] = image_ref(args.texture_image)
    formats = csv_list(args.target_formats)
    if formats:
        payload["target_formats"] = formats
    return payload


def resupply(value: str | None, flag: str) -> str:
    """A remote or inline source is never stored, so only a new submission needs it back."""
    if not value:
        raise MeshyError(f"{flag} was a URL or data URI and is not stored in the checkpoint. "
                         f"Re-supply it with resume CHECKPOINT {flag} PATH.", "checkpoint_error")
    return value


def cmd_image(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    with job_context(args) as job:
        def payload() -> dict[str, Any]:
            built = build_image_payload(args)
            built["image_url"] = image_ref(resupply(args.image, "--image"))
            return built

        base = safe_name(args.name or (Path(args.image).stem if args.image else "image"))
        run_single(api_key, job, args, "image", "model", payload, base)


def cmd_multi_image(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    with job_context(args) as job:
        def payload() -> dict[str, Any]:
            images = csv_list(resupply(args.images, "--images"))
            if not 1 <= len(images) <= 4:
                raise MeshyError("--images takes 1 to 4 comma-separated paths or URLs.")
            built = build_image_payload(args)
            built["image_urls"] = [image_ref(item) for item in images]
            return built

        run_single(api_key, job, args, "multi-image", "model", payload,
                   safe_name(args.name or "multiview"))


def source_payload(args: argparse.Namespace) -> dict[str, Any]:
    if bool(args.input_task_id) == bool(args.model_url):
        raise MeshyError("Pass exactly one of --input-task-id or --model-url.")
    if args.input_task_id:
        return {"input_task_id": args.input_task_id}
    return {"model_url": image_ref(args.model_url)}


def build_retexture_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload = source_payload(args)
    styles = [bool(args.text_style_prompt), bool(args.image_style), bool(args.multiview_images)]
    if sum(styles) != 1:
        raise MeshyError("Pass exactly one of --text-style-prompt, --image-style, --multiview-images.")
    if args.text_style_prompt:
        payload["text_style_prompt"] = args.text_style_prompt
    if args.image_style:
        payload["image_style_url"] = image_ref(args.image_style)
    if args.multiview_images:
        payload["multiview_image_urls"] = [image_ref(i) for i in csv_list(args.multiview_images)]
        payload.setdefault("ai_model", "meshy-7")
    apply_optional(payload, args, {
        "ai_model": "ai_model",
        "texture_resolution": "texture_resolution",
        "pbr": "enable_pbr",
        "original_uv": "enable_original_uv",
        "alpha_thumbnail": "alpha_thumbnail",
    })
    if args.keep_lighting:
        payload["remove_lighting"] = False
    formats = csv_list(args.target_formats)
    if formats:
        payload["target_formats"] = formats
    return payload


def cmd_retexture(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    with job_context(args) as job:
        run_single(api_key, job, args, "retexture", "task", lambda: build_retexture_payload(args),
                   safe_name(args.name or "retexture"))


def build_remesh_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload = source_payload(args)
    apply_optional(payload, args, {
        "topology": "topology",
        "target_polycount": "target_polycount",
        "decimation_mode": "decimation_mode",
    })
    payload["target_formats"] = csv_list(args.target_formats) or ["glb"]
    return payload


def cmd_remesh(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    with job_context(args) as job:
        run_single(api_key, job, args, "remesh", "task", lambda: build_remesh_payload(args),
                   safe_name(args.name or "remesh"))


def build_rig_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload = source_payload(args)
    if args.height_meters is not None:
        payload["height_meters"] = args.height_meters
    if args.texture_image:
        payload["texture_image_url"] = image_ref(args.texture_image)
    return payload


def cmd_rig(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    with job_context(args) as job:
        run_single(api_key, job, args, "rig", "task", lambda: build_rig_payload(args),
                   safe_name(args.name or "rig"))


def animation_payload(rig_task_id: str, action: str | None, motion_task_id: str | None,
                      fps: int | None) -> tuple[dict[str, Any], str]:
    payload: dict[str, Any] = {"rig_task_id": rig_task_id}
    if motion_task_id:
        payload["motion_task_id"] = motion_task_id
        label = f"motion-{motion_task_id[:8]}"
    else:
        action_id, name = resolve_action(action or "")
        payload["action_id"] = action_id
        label = f"{action_id:03d}-{safe_name(name)}"
    if fps:
        payload["post_process"] = {"operation_type": "change_fps", "fps": fps}
    return payload, label


def run_animations(api_key: str, job: Checkpoint, args: argparse.Namespace, rig_task_id: str,
                   base: str, validate: bool = False) -> None:
    """One clip per animation task; stage names follow request order so a resume maps back."""
    tokens = [None] if args.motion_task_id else csv_list(args.animations)
    stages = []
    for index, token in enumerate(tokens, start=1):
        payload, label = animation_payload(rig_task_id, token, args.motion_task_id, args.fps)
        name = f"animation-{index}"
        task_id = ensure_task(api_key, job, name, "animate", payload)
        print(f"animate task {task_id} ({label})")
        stages.append((name, label))
    if not args.wait:
        return
    for name, label in stages:
        out_dir = Path(args.out_dir) if args.download else None
        task, paths = finish_stage(api_key, job, name, args, out_dir, f"{base}-{label}",
                                   wanted_formats(args))
        require_success(task)
        if not validate:
            continue
        for clip in paths:
            if clip.suffix != ".glb":
                continue
            report, problems = validate_animation_glb(clip)
            for line in report:
                print(f"  {line}")
            for problem in problems:
                eprint(f"  ! {problem}")


def cmd_animate(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    if bool(args.animations) == bool(args.motion_task_id):
        raise MeshyError("Pass exactly one of --animations or --motion-task-id.")
    with job_context(args) as job:
        run_animations(api_key, job, args, args.rig_task_id, safe_name(args.name or "clip"))


def cmd_motion(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    with job_context(args) as job:
        run_single(api_key, job, args, "motion", "task",
                   {"prompt": args.prompt, "duration": args.duration, "mode": args.mode},
                   safe_name(args.name or args.prompt[:30]))


def cmd_status(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    kind, task = discover_kind(api_key, args.task_id, args.kind)
    print(f"kind: {kind}")
    print(json.dumps(task, indent=2)[:6000])


def cmd_download(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    kind, task = discover_kind(api_key, args.task_id, args.kind)
    if task.get("status") != "SUCCEEDED":
        raise MeshyError(f"Task {args.task_id} is {task.get('status')}, nothing to download.", "task_failed")
    download_outputs(task, Path(args.out_dir), safe_name(args.name) if args.name else None,
                     wanted_formats(args))


def cmd_balance(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    print(json.dumps(api_request(api_key, "GET", "/openapi/v1/balance"), indent=2))


def cmd_probe(args: argparse.Namespace) -> None:
    """Print the SET|MISSING credential contract line used by skip rules and audits."""
    print(f"MESHY_API_KEY={'SET' if os.environ.get('MESHY_API_KEY') else 'MISSING'}")


def cmd_list_animations(args: argparse.Namespace) -> None:
    library = load_animation_library()
    needle = (args.search or "").lower()
    category = (args.category or "").lower()
    rows = [
        r for r in library
        if (not needle or needle in r["name"].lower() or needle in r["subcategory"].lower())
        and (not category or category in r["category"].lower())
    ]
    for row in rows[:args.limit]:
        print(f"{row['action_id']:>4}  {row['name']:<38} {row['category']}/{row['subcategory']}")
    print(f"-- {len(rows)} match(es), showing {min(len(rows), args.limit)} of {len(library)} animations")


def cmd_character_pipeline(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    with job_context(args) as job:
        run_character_pipeline(api_key, job, args)


def rig_source_from(api_key: str, job: Checkpoint, args: argparse.Namespace, base: str,
                    out_dir: Path) -> str:
    if args.model_task_id:
        return args.model_task_id
    if not args.prompt:
        raise MeshyError("Pass --prompt or --model-task-id.")
    pose_words = "full body, arms away from the body, symmetric, facing forward, no props fused to the body"
    prompt = args.prompt if "full body" in args.prompt.lower() else f"{args.prompt}, {pose_words}"
    model_args = argparse.Namespace(**vars(args))
    model_args.prompt = prompt
    preview_id = ensure_task(api_key, job, "preview", "text", lambda: build_text_payload(model_args))
    print(f"preview task: {preview_id}")
    require_success(finish_stage(api_key, job, "preview", args)[0])
    refine_id = ensure_task(api_key, job, "refine", "text", lambda: build_refine_payload(args, preview_id))
    print(f"refine task: {refine_id}")
    task, _ = finish_stage(api_key, job, "refine", args, out_dir, f"{base}-model", wanted_formats(args))
    require_success(task)
    return refine_id


def run_character_pipeline(api_key: str, job: Checkpoint, args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    base = safe_name(args.name or (args.prompt or "character")[:40])
    model_task_id = rig_source_from(api_key, job, args, base, out_dir)
    if args.stop_after == "model":
        print(f"\nmodel task: {model_task_id}\nstopped after model; resume the checkpoint to rig")
        return

    rig_stage = "rig"
    try:
        rig_id = ensure_task(api_key, job, rig_stage, "rig", {"input_task_id": model_task_id,
                                                              **({"height_meters": args.height_meters}
                                                                 if args.height_meters is not None else {})})
    except MeshyError as exc:
        if exc.category != "invalid_input" or ("face limit" not in str(exc) and "exceeds" not in str(exc)):
            raise
        eprint("rig rejected the mesh density; remeshing first")
        budget = min(args.target_polycount or RIG_FACE_BUDGET, RIG_FACE_LIMIT)
        remesh_id = ensure_task(api_key, job, "remesh", "remesh", {
            "input_task_id": model_task_id,
            "target_polycount": budget,
            "topology": args.topology or "triangle",
            "target_formats": ["glb"],
        })
        print(f"remesh task: {remesh_id} (target_polycount {budget})")
        remesh_task, _ = finish_stage(api_key, job, "remesh", args, out_dir, f"{base}-remesh",
                                      wanted_formats(args))
        require_success(remesh_task)
        model_task_id = remesh_id
        rig_stage = "rig-remeshed"
        rig_id = ensure_task(api_key, job, rig_stage, "rig", {"input_task_id": remesh_id,
                                                              **({"height_meters": args.height_meters}
                                                                 if args.height_meters is not None else {})})
    print(f"rig task: {rig_id}")
    rig_task, rig_files = finish_stage(api_key, job, rig_stage, args, out_dir, f"{base}-rig",
                                       wanted_formats(args))
    require_success(rig_task)

    for path in rig_files:
        if path.suffix == ".glb" and "character" in path.name:
            description, problems = validate_rig_glb(path)
            print(f"rig check: {description}")
            for problem in problems:
                eprint(f"  ! {problem}")
            break

    if args.stop_after == "rig":
        print(f"\nmodel task: {model_task_id}\nrig task: {rig_id}\nstopped after rig; resume the checkpoint to animate")
        return

    run_animations(api_key, job, args, rig_id, base, validate=True)
    print(f"\nmodel task: {model_task_id}\nrig task: {rig_id}\noutput: {out_dir}")


def reconcile_submission(api_key: str, job: Checkpoint, task_id: str) -> None:
    uncertain = [stage for stage in job.data["stages"].values()
                 if not stage.get("task_id") and stage["state"] in {"submitting", "unknown_submission"}]
    if len(uncertain) != 1:
        raise MeshyError("--task-id requires exactly one uncertain submission in the checkpoint.")
    stage = uncertain[0]
    intent = stage.get("request", {})
    task = get_task(api_key, intent["kind"], task_id)
    for key in ("preview_task_id", "input_task_id", "rig_task_id", "motion_task_id"):
        if key in intent and key in task and task[key] != intent[key]:
            raise MeshyError(f"Reconciled task {key} does not match the saved submission intent.")
    stage.update(task_id=task_id, state="submitted")
    stage.pop("last_error", None)
    job.save()


def cmd_resume(args: argparse.Namespace) -> None:
    """Resume an accepted job: never a new paid submission for work already accepted.

    Single jobs always wait and download on resume; they never grow into a rigging
    pipeline. A character checkpoint continues through animations by default,
    independently of the previous invocation's --stop-after limit.
    """
    api_key = api_key_from(args)
    path = Path(args.checkpoint).expanduser().resolve()
    if not path.is_file():
        raise MeshyError(f"Checkpoint not found: {path}.", "checkpoint_error")
    with checkpoint_file(path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise MeshyError(f"Cannot read checkpoint {path}.", "checkpoint_error") from exc
        validate_checkpoint(data)
        command = data["command"]
        if args.stop_after is not None and command != "character-pipeline":
            raise MeshyError("--stop-after requires a character-pipeline checkpoint. Single jobs never add paid stages.")
        for flag, owner in (("image", "image"), ("images", "multi-image")):
            if getattr(args, flag) is not None and command != owner:
                raise MeshyError(f"--{flag} is only for resuming a {owner} submission.")
        job = Checkpoint(path, data)
        if args.task_id:
            reconcile_submission(api_key, job, args.task_id)
        saved = argparse.Namespace(**{key: value for key, value in data["args"].items() if key in CHECKPOINT_ARGS})
        saved.command = command
        saved.api_key = args.api_key
        saved._job = job
        saved.stop_after = args.stop_after or "animations"
        for flag in ("interval", "timeout", "image", "images"):
            value = getattr(args, flag)
            if value is not None:
                setattr(saved, flag, value)
        if command != "character-pipeline":
            saved.wait = True
            saved.download = True
        RESUME_COMMANDS[command](saved)


def validate_checkpoint(data: Any) -> None:
    """Validate before dispatch: a damaged accepted ID must never look like a new job."""
    defaults_argv = {
        "text": ["text", "--prompt", "checkpoint"],
        "refine": ["refine", "--preview-task-id", "checkpoint-task"],
        "image": ["image", "--image", "checkpoint.png"],
        "multi-image": ["multi-image", "--images", "checkpoint.png"],
        "retexture": ["retexture"],
        "remesh": ["remesh"],
        "rig": ["rig"],
        "motion": ["motion", "--prompt", "checkpoint"],
        "animate": ["animate", "--rig-task-id", "checkpoint-task"],
        "character-pipeline": ["character-pipeline"],
    }

    def invalid(detail: str) -> None:
        raise MeshyError(f"Malformed checkpoint: {detail}.", "checkpoint_error")

    if not isinstance(data, dict) or data.get("version") != 1:
        invalid("unsupported version")
    command = data.get("command")
    if not isinstance(command, str) or command not in defaults_argv:
        invalid("unknown command")
    options = data.get("args")
    stages = data.get("stages")
    if not isinstance(options, dict) or not isinstance(stages, dict):
        invalid("args and stages must be objects")
    defaults = vars(build_parser().parse_args(defaults_argv[command]))
    expected_keys = CHECKPOINT_ARGS.intersection(defaults)
    if set(options) != expected_keys or options.get("command") != command:
        invalid("missing, unknown, or mismatched command arguments")
    for key in expected_keys:
        value = options[key]
        default = defaults[key]
        if value is None:
            if default is not None and key not in PATH_ARGS + LIST_PATH_ARGS:
                invalid(f"argument {key} cannot be null")
        elif type(default) is bool:
            if type(value) is not bool:
                invalid(f"argument {key} must be a boolean")
        elif key in INTEGER_ARGS:
            if type(value) is not int:
                invalid(f"argument {key} must be an integer")
        elif key in NUMERIC_ARGS:
            if type(value) not in {int, float}:
                invalid(f"argument {key} must be numeric")
        elif not isinstance(value, str):
            invalid(f"argument {key} must be text")
    if not options["out_dir"] or options["interval"] < 0 or options["timeout"] < 0:
        invalid("empty output directory or negative polling timings")
    clips = 1 if options.get("motion_task_id") else len(csv_list(options.get("animations")))
    if command == "character-pipeline":
        valid_stages = set(CHARACTER_STAGES)
        valid_stages.update(f"animation-{index}" for index in range(1, clips + 1))
    elif command == "animate":
        valid_stages = {f"animation-{index}" for index in range(1, clips + 1)}
    else:
        valid_stages = set(RESUMABLE_STAGES[command])
    if not set(stages).issubset(valid_stages):
        invalid("unexpected stage names")
    for name, stage in stages.items():
        if not isinstance(stage, dict) or not isinstance(stage.get("state"), str):
            invalid(f"stage {name} must have a state")
        state = stage["state"]
        if state not in STAGE_STATES:
            invalid(f"stage {name} has an unknown state")
        task_id = stage.get("task_id")
        if "task_id" in stage and (not isinstance(task_id, str) or not task_id.strip() or "/" in task_id):
            invalid(f"stage {name} has an invalid accepted task ID")
        if (state == "submitted" or state in FINAL_STATUSES) and not task_id:
            invalid(f"stage {name} lost its accepted task ID")
        intent = stage.get("request")
        if state in {"submitting", "unknown_submission"} or intent is not None:
            if not isinstance(intent, dict) or intent.get("kind") not in ENDPOINTS:
                invalid(f"stage {name} has a malformed submission intent")
            for key in ("preview_task_id", "input_task_id", "rig_task_id", "motion_task_id"):
                if key in intent and not isinstance(intent[key], str):
                    invalid(f"stage {name} has an invalid parent task ID")
        if "kind" in stage and stage["kind"] not in ENDPOINTS:
            invalid(f"stage {name} has an unknown task kind")
        task = stage.get("task")
        if task is not None:
            if (not isinstance(task, dict) or not isinstance(task.get("status"), str)
                    or task.get("id") != task_id):
                invalid(f"stage {name} has malformed task status")
            if "progress" in task and type(task["progress"]) is not int:
                invalid(f"stage {name} has malformed task progress")
        if not isinstance(stage.get("files"), dict):
            invalid(f"stage {name} files must be an object")
        for record in stage["files"].values():
            if (not isinstance(record, dict) or not isinstance(record.get("path"), str)
                    or type(record.get("size")) is not int or not isinstance(record.get("sha256"), str)):
                invalid(f"stage {name} has a malformed file record")
        if "downloads_complete" in stage and type(stage["downloads_complete"]) is not bool:
            invalid(f"stage {name} has malformed download status")


def load_glb(path: Path) -> tuple[dict[str, Any], bytes]:
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise MeshyError(f"Not a GLB file: {path}")
    offset = 12
    gltf: dict[str, Any] | None = None
    bin_chunk = b""
    while offset < len(data):
        clen, ctype = struct.unpack_from("<II", data, offset)
        chunk = data[offset + 8:offset + 8 + clen]
        if ctype == 0x4E4F534A:
            gltf = json.loads(chunk)
        elif ctype == 0x004E4942:
            bin_chunk = chunk
        offset += 8 + clen
    if gltf is None:
        raise MeshyError(f"No JSON chunk in GLB: {path}")
    return gltf, bin_chunk


def _read_accessor(gltf: dict[str, Any], bin_chunk: bytes, idx: int) -> list[tuple[float, ...]]:
    comp = {5126: ("f", 4), 5123: ("H", 2), 5125: ("I", 4)}
    ncomp = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}
    acc = gltf["accessors"][idx]
    bv = gltf["bufferViews"][acc["bufferView"]]
    start = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    n = ncomp[acc["type"]]
    fmt, _ = comp[acc["componentType"]]
    count = acc["count"]
    vals = struct.unpack_from(f"<{count * n}{fmt}", bin_chunk, start)
    return [vals[i * n:(i + 1) * n] for i in range(count)]


def validate_rig_glb(path: Path) -> tuple[str, list[str]]:
    """Meshy auto-rigs are humanoid with Mixamo-like bone names. Check the core chain
    exists and that left/right limbs are present and equally deep."""
    gltf, _ = load_glb(path)
    names = [n.get("name", "") for n in gltf.get("nodes", []) if n.get("name")]
    bones = [n.split(":")[-1] for n in names]
    joined = " ".join(bones).lower()
    problems: list[str] = []
    if not bones:
        return "no named nodes", ["rig GLB has no named nodes"]
    for core in HUMANOID_CORE:
        if core.lower() not in joined:
            problems.append(f"missing core bone {core}")
    for part in HUMANOID_PAIRED:
        left = sum(1 for b in bones if b.lower().startswith("left") and part.lower() in b.lower())
        right = sum(1 for b in bones if b.lower().startswith("right") and part.lower() in b.lower())
        if left == 0 or right == 0:
            problems.append(f"missing Left/Right {part} (L={left} R={right})")
        elif abs(left - right) > 1:
            problems.append(f"{part} chain asymmetric (L={left} R={right})")
    if len(bones) < 20:
        problems.append(f"suspiciously small skeleton ({len(bones)} nodes)")
    return f"{len(bones)} nodes, e.g. {', '.join(bones[:8])}", problems


def validate_animation_glb(path: Path) -> tuple[list[str], list[str]]:
    """Keyframe-level QA. Warp signatures: scale tracks, or translation tracks on
    non-root bones that deviate far from the bone's rest offset (limb stretching)."""
    gltf, bin_chunk = load_glb(path)
    nodes = gltf.get("nodes", [])
    roots = {"armature", "root", "hips", "hip", "pelvis"}
    report: list[str] = []
    problems: list[str] = []
    animations = gltf.get("animations", [])
    if not animations:
        return ["no animations in file"], ["no animation clips found"]
    for anim in animations:
        dur = 0.0
        flat_scale = 0
        rescale: dict[str, float] = {}
        rot_bones: set[str] = set()
        big_rot: dict[str, int] = {}
        for ch in anim["channels"]:
            sampler = anim["samplers"][ch["sampler"]]
            times = _read_accessor(gltf, bin_chunk, sampler["input"])
            out = _read_accessor(gltf, bin_chunk, sampler["output"])
            node = nodes[ch["target"]["node"]] if ch["target"].get("node") is not None else {}
            name = node.get("name", "?")
            dur = max(dur, times[-1][0])
            path_kind = ch["target"]["path"]
            if path_kind == "rotation":
                rot_bones.add(name)
                first = out[0]
                amp = 0.0
                for quat in out:
                    dot = abs(sum(a * b for a, b in zip(first, quat)))
                    amp = max(amp, 2 * math.acos(min(1.0, dot)))
                if math.degrees(amp) > 170:
                    big_rot[name] = round(math.degrees(amp))
            elif path_kind == "scale":
                # Meshy bakes a constant scale track on every bone; only a track that
                # actually leaves the rest scale can warp the mesh.
                rest = node.get("scale", [1.0, 1.0, 1.0])
                spread = max(max(v[i] for v in out) - min(v[i] for v in out) for i in range(3))
                offset = max(abs(out[0][i] - rest[i]) for i in range(3))
                if spread > 0.05:
                    problems.append(
                        f"{anim.get('name')}: scale track on {name} varies by {spread:.2f} (warp risk)"
                    )
                elif offset > 0.05:
                    # Constant but off rest: the clip was authored for a different rig size,
                    # so this clip renders the character larger/smaller than its neighbours.
                    rescale[name] = round(out[0][0], 3)
                else:
                    flat_scale += 1
            elif path_kind == "translation" and name.split(":")[-1].lower() not in roots:
                rest = node.get("translation", [0, 0, 0])
                restlen = math.sqrt(sum(c * c for c in rest)) or 1e-9
                dev = max(math.sqrt(sum((v[i] - rest[i]) ** 2 for i in range(3))) for v in out)
                if dev / restlen > 0.5:
                    problems.append(
                        f"{anim.get('name')}: translation track on non-root bone {name} deviates "
                        f"{dev / restlen:.1f}x its rest offset (limb stretch warp)"
                    )
        report.append(
            f"{anim.get('name')}: {dur:.2f}s, {len(anim['channels'])} channels, "
            f"{len(rot_bones)} bones rotating, {flat_scale} constant scale tracks"
        )
        if rescale:
            report.append(f"  constant rescale vs rest pose (size mismatch between clips): {rescale}")
        if big_rot:
            report.append(f"  rotation amplitude >170deg (check visually): {big_rot}")
    return report, problems


def cmd_validate_rig(args: argparse.Namespace) -> None:
    description, problems = validate_rig_glb(Path(args.glb_path))
    print(description)
    if problems:
        raise MeshyError("Rig validation failed: " + "; ".join(problems), "task_failed")
    print("Rig looks structurally valid.")


def cmd_validate_animation(args: argparse.Namespace) -> None:
    report, problems = validate_animation_glb(Path(args.glb_path))
    for line in report:
        print(line)
    if problems:
        raise MeshyError("Animation validation failed: " + "; ".join(problems), "task_failed")
    print("Clips look structurally sound (verify motion visually in the engine).")


def add_runtime_args(parser: argparse.ArgumentParser, default_out: str = "meshy-output") -> None:
    parser.add_argument("--api-key")
    parser.add_argument("--name", help="filename base for downloads")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--out-dir", default=default_out)
    parser.add_argument("--download-formats", default="glb",
                        help="which model formats to save (default glb; Meshy bakes all of them)")
    parser.add_argument("--all-formats", action="store_true", help="save every returned model format")
    parser.add_argument("--interval", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--checkpoint", metavar="PATH",
                        help="create a resumable job journal; existing paths require resume")


def add_geometry_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ai-model", choices=["meshy-5", "meshy-6", "meshy-7", "latest"])
    parser.add_argument("--model-type", choices=["standard", "smart-topology", "lowpoly"])
    parser.add_argument("--topology", choices=["quad", "triangle"])
    parser.add_argument("--target-polycount", type=int)
    parser.add_argument("--decimation-mode", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--no-remesh", action="store_true")
    parser.add_argument("--ultra", action="store_true", help="ultra_mode (meshy-7 only)")
    parser.add_argument("--auto-size", action="store_true")
    parser.add_argument("--origin-at", choices=["bottom", "center"])
    parser.add_argument("--alpha-thumbnail", action="store_true")
    parser.add_argument("--target-formats", help="comma list: glb,fbx,obj,stl,usdz,3mf")


def add_texture_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--texture-resolution", choices=["2k", "4k", "8k"])
    parser.add_argument("--texture-prompt")
    parser.add_argument("--texture-image", help="style image path or URL")
    parser.add_argument("--pbr", action="store_true", help="enable_pbr")
    parser.add_argument("--keep-lighting", action="store_true", help="remove_lighting=false")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Meshy OpenAPI client for Three.js asset pipelines")
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe", help="print MESHY_API_KEY=SET|MISSING")
    probe.set_defaults(func=cmd_probe)

    text = sub.add_parser("text", help="text to 3D (preview, then refine/texture)")
    text.add_argument("--prompt", required=True)
    text.add_argument("--negative-prompt")
    text.add_argument("--art-style", choices=["realistic", "sculpture"])
    text.add_argument("--pose-mode", choices=["a-pose", "t-pose", "empty"])
    text.add_argument("--seed", type=int)
    text.add_argument("--no-refine", action="store_true", help="stop after the untextured preview")
    add_geometry_args(text)
    add_texture_args(text)
    add_runtime_args(text)
    text.set_defaults(func=cmd_text)

    refine = sub.add_parser("refine", help="texture an existing preview task")
    refine.add_argument("--preview-task-id", required=True)
    refine.add_argument("--ai-model", choices=["meshy-5", "meshy-6", "meshy-7", "latest"])
    refine.add_argument("--auto-size", action="store_true")
    refine.add_argument("--origin-at", choices=["bottom", "center"])
    refine.add_argument("--alpha-thumbnail", action="store_true")
    refine.add_argument("--target-formats")
    add_texture_args(refine)
    add_runtime_args(refine)
    refine.set_defaults(func=cmd_refine)

    image = sub.add_parser("image", help="image to 3D (local path or URL)")
    image.add_argument("--image", required=True)
    image.add_argument("--pose-mode", choices=["a-pose", "t-pose", "empty"])
    image.add_argument("--no-texture", action="store_true")
    image.add_argument("--no-image-enhancement", action="store_true")
    image.add_argument("--multi-view-thumbnails", action="store_true")
    add_geometry_args(image)
    add_texture_args(image)
    add_runtime_args(image)
    image.set_defaults(func=cmd_image)

    multi = sub.add_parser("multi-image", help="1-4 view images to 3D")
    multi.add_argument("--images", required=True, help="comma list of paths or URLs (1-4)")
    multi.add_argument("--pose-mode", choices=["a-pose", "t-pose", "empty"])
    multi.add_argument("--no-texture", action="store_true")
    multi.add_argument("--no-image-enhancement", action="store_true")
    multi.add_argument("--multi-view-thumbnails", action="store_true")
    add_geometry_args(multi)
    add_texture_args(multi)
    add_runtime_args(multi)
    multi.set_defaults(func=cmd_multi_image)

    retex = sub.add_parser("retexture", help="restyle an existing model's textures")
    retex.add_argument("--input-task-id")
    retex.add_argument("--model-url", help="public URL or local .glb/.obj/.fbx path")
    retex.add_argument("--text-style-prompt")
    retex.add_argument("--image-style")
    retex.add_argument("--multiview-images", help="1-4 images, requires meshy-7")
    retex.add_argument("--ai-model", choices=["meshy-5", "meshy-6", "meshy-7", "latest"])
    retex.add_argument("--original-uv", action="store_true", help="enable_original_uv")
    retex.add_argument("--alpha-thumbnail", action="store_true")
    retex.add_argument("--target-formats")
    add_texture_args(retex)
    add_runtime_args(retex)
    retex.set_defaults(func=cmd_retexture)

    remesh = sub.add_parser("remesh", help="retopologize / decimate an existing model")
    remesh.add_argument("--input-task-id")
    remesh.add_argument("--model-url")
    remesh.add_argument("--topology", choices=["quad", "triangle"])
    remesh.add_argument("--target-polycount", type=int)
    remesh.add_argument("--decimation-mode", type=int, choices=[1, 2, 3, 4])
    remesh.add_argument("--target-formats")
    add_runtime_args(remesh)
    remesh.set_defaults(func=cmd_remesh)

    rig = sub.add_parser("rig", help="auto-rig a humanoid model")
    rig.add_argument("--input-task-id")
    rig.add_argument("--model-url", help="public URL or local .glb path")
    rig.add_argument("--height-meters", type=float)
    rig.add_argument("--texture-image")
    add_runtime_args(rig)
    rig.set_defaults(func=cmd_rig)

    animate = sub.add_parser("animate", help="apply library or generated motion to a rig task")
    animate.add_argument("--rig-task-id", required=True)
    animate.add_argument("--animations", help="comma list of action ids or names (idle,walking,running)")
    animate.add_argument("--motion-task-id", help="text-to-motion task id instead of a library action")
    animate.add_argument("--fps", type=int, choices=[24, 25, 30, 60])
    add_runtime_args(animate)
    animate.set_defaults(func=cmd_animate)

    motion = sub.add_parser("motion", help="text to motion (custom clip)")
    motion.add_argument("--prompt", required=True)
    motion.add_argument("--duration", type=float, default=4.0, help="2-10s in 0.5 steps")
    motion.add_argument("--mode", choices=["prime", "swift"], default="prime")
    add_runtime_args(motion)
    motion.set_defaults(func=cmd_motion)

    status = sub.add_parser("status", help="show a task")
    status.add_argument("task_id")
    status.add_argument("--kind", choices=list(ENDPOINTS))
    status.add_argument("--api-key")
    status.set_defaults(func=cmd_status)

    download = sub.add_parser("download", help="download a succeeded task's outputs")
    download.add_argument("task_id")
    download.add_argument("--kind", choices=list(ENDPOINTS))
    download.add_argument("--api-key")
    download.add_argument("--name")
    download.add_argument("--out-dir", default="meshy-output")
    download.add_argument("--download-formats", default="glb")
    download.add_argument("--all-formats", action="store_true")
    download.set_defaults(func=cmd_download)

    resume = sub.add_parser("resume", help="continue an existing checkpoint without resubmitting")
    resume.add_argument("checkpoint")
    resume.add_argument("--api-key")
    resume.add_argument("--task-id", help="reconcile one uncertain submission with its real task ID")
    resume.add_argument("--image", help="re-supply an image source that was a URL or data URI")
    resume.add_argument("--images", help="re-supply multi-view sources that were URLs or data URIs")
    resume.add_argument("--interval", type=int)
    resume.add_argument("--timeout", type=int)
    resume.add_argument("--stop-after", choices=["model", "rig", "animations"])
    resume.set_defaults(func=cmd_resume)

    balance = sub.add_parser("balance", help="show remaining credits")
    balance.add_argument("--api-key")
    balance.set_defaults(func=cmd_balance)

    listanim = sub.add_parser("list-animations", help="search the bundled animation library")
    listanim.add_argument("--search")
    listanim.add_argument("--category")
    listanim.add_argument("--limit", type=int, default=40)
    listanim.set_defaults(func=cmd_list_animations)

    vrig = sub.add_parser("validate-rig", help="check a downloaded rig GLB skeleton")
    vrig.add_argument("glb_path")
    vrig.set_defaults(func=cmd_validate_rig)

    vanim = sub.add_parser("validate-animation", help="keyframe QA for a downloaded clip GLB")
    vanim.add_argument("glb_path")
    vanim.set_defaults(func=cmd_validate_animation)

    pipeline = sub.add_parser("character-pipeline", help="generate -> texture -> rig -> animate -> download")
    pipeline.add_argument("--prompt")
    pipeline.add_argument("--model-task-id", help="resume from an existing textured task")
    pipeline.add_argument("--animations", default="idle,walking,running")
    pipeline.add_argument("--height-meters", type=float, default=1.7)
    pipeline.add_argument("--fps", type=int, choices=[24, 25, 30, 60])
    pipeline.add_argument("--pose-mode", choices=["a-pose", "t-pose", "empty"], default="t-pose")
    pipeline.add_argument("--art-style", choices=["realistic", "sculpture"])
    pipeline.add_argument("--negative-prompt")
    pipeline.add_argument("--seed", type=int)
    pipeline.add_argument("--no-refine", action="store_true")
    pipeline.add_argument("--motion-task-id", help="use a text-to-motion clip instead of library actions")
    pipeline.add_argument("--stop-after", choices=["model", "rig", "animations"], default="animations",
                          help="stop after this stage for inspection; use --checkpoint to continue later")
    add_geometry_args(pipeline)
    pipeline.set_defaults(target_polycount=30000)
    add_texture_args(pipeline)
    add_runtime_args(pipeline, default_out="meshy-character")
    pipeline.set_defaults(func=cmd_character_pipeline, wait=True, download=True)

    return parser


RESUME_COMMANDS = {
    "text": cmd_text,
    "refine": cmd_refine,
    "image": cmd_image,
    "multi-image": cmd_multi_image,
    "retexture": cmd_retexture,
    "remesh": cmd_remesh,
    "rig": cmd_rig,
    "motion": cmd_motion,
    "animate": cmd_animate,
    "character-pipeline": cmd_character_pipeline,
}


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.func(args)
    except MeshyError as exc:
        eprint(f"meshy_3d_asset.py: [{exc.category}] {exc}")
        return 1
    except KeyboardInterrupt:
        eprint("interrupted")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
