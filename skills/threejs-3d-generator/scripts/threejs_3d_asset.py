#!/usr/bin/env python3
"""Small Tripo OpenAPI v3 client for skill-driven 3D asset generation."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from email.utils import parsedate_to_datetime
import hashlib
from http.client import IncompleteRead
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from typing import Any, Callable, Iterator
from urllib import error, parse, request

BASE_URL = "https://openapi.tripo3d.ai/v3"
FINAL_STATUSES = {"success", "failed", "banned", "expired", "cancelled", "unknown"}

# Map canonical local keys to (v3 primary key, legacy v2 fallback key).
DOWNLOAD_KEY_MAP: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pbr_model", ("pbr_model_url", "pbr_model")),
    ("model", ("model_url", "model")),
    ("base_model", ("base_model_url", "base_model")),
    ("rendered_image", ("rendered_image_url", "rendered_image")),
    ("generated_image", ("generated_image_url", "generated_image")),
)
DOWNLOAD_KEYS = tuple(key for key, _ in DOWNLOAD_KEY_MAP)

DEFAULT_MODEL_VERSION = "v3.1-20260211"
DEFAULT_TEXTURE_MODEL_VERSION = "v3.5-20260815"
DEFAULT_DECIMATE_MODEL_VERSION = "v2.0"
RIG_BIPED_MODEL_VERSION = "v3.0-20260909"
RIG_MODEL_VERSION = "v2.5-20260210"

RIG_TYPES = ("biped", "quadruped", "hexapod", "octopod", "avian", "serpentine", "aquatic", "others")
RIG_SPECS = ("tripo", "mixamo", "actorcore", "unity", "unreal", "vrm")

TASK_ENDPOINTS = {
    "text_to_model": "/generation/text-to-model",
    "image_to_model": "/generation/image-to-model",
    "multiview_to_model": "/generation/multiview-to-model",
    "texture_model": "/models/texture",
    "conversion": "/models/convert",
    "highpoly_to_lowpoly": "/mesh/decimate",
    "animate_prerigcheck": "/animations/rig-check",
    "animate_rig": "/animations/rig",
    "animate_retarget": "/animations/retarget",
}

BIPED_PRESETS = (
    "preset:idle",
    "preset:walk",
    "preset:run",
    "preset:dive",
    "preset:climb",
    "preset:jump",
    "preset:slash",
    "preset:shoot",
    "preset:hurt",
    "preset:fall",
    "preset:turn",
)
RIG_TYPE_PRESETS = {
    "biped": set(BIPED_PRESETS),
    "quadruped": {"preset:quadruped:walk"},
    "hexapod": {"preset:hexapod:walk"},
    "octopod": {"preset:octopod:walk"},
    "serpentine": {"preset:serpentine:march"},
    "aquatic": {"preset:aquatic:march"},
    "avian": set(),
    "others": set(),
}
KNOWN_PRESETS = set().union(*RIG_TYPE_PRESETS.values())
RETARGET_BATCH_LIMIT = 5
GET_ATTEMPTS = 4
RETRY_DELAY_CAP = 60


def active_base_url() -> str:
    return (os.environ.get("TRIPO_BASE_URL") or BASE_URL).rstrip("/")


def validate_animations(
    animations: list[str],
    rig_type: str | None = None,
    rig_model_version: str | None = None,
) -> None:
    """Fail fast on presets the API will reject, before any credits are spent."""
    is_v1 = rig_model_version is not None and rig_model_version.startswith("v1.0")
    is_v2 = rig_model_version is not None and rig_model_version.startswith("v2.")
    for animation in animations:
        if not animation.startswith("preset:"):
            continue
        if animation.startswith("preset:biped:"):
            # Legacy preset:biped:* works on v1.0 and v3.0 biped rigs, not v2.x creature rigs.
            if is_v2:
                raise TripoError(
                    f"{animation} is not supported on {rig_model_version} rigs; use a "
                    f"{RIG_BIPED_MODEL_VERSION} or v1.0-20240301 biped rig."
                )
            continue
        if is_v1:
            raise TripoError(
                f"{animation} is a v2.x/v3.0 preset; v1.0-20240301 rigs use the preset:biped:* "
                "library instead (e.g. preset:biped:idle, preset:biped:walk, preset:biped:run)."
            )
        if animation not in KNOWN_PRESETS:
            hint = ""
            if "attack" in animation:
                hint = " There is no preset:attack; use preset:slash or preset:shoot."
            raise TripoError(
                f"Unknown animation preset {animation!r}.{hint} "
                f"Valid presets: {', '.join(sorted(KNOWN_PRESETS))}"
            )
        if rig_type and rig_type in RIG_TYPE_PRESETS and animation not in RIG_TYPE_PRESETS[rig_type]:
            valid = ", ".join(sorted(RIG_TYPE_PRESETS[rig_type])) or "none documented for this rig type"
            raise TripoError(
                f"{animation} is not compatible with rig_type {rig_type!r}. Valid: {valid}"
            )


class TripoError(RuntimeError):
    def __init__(self, message: str, category: str = "invalid_input", retry_after: float | None = None):
        super().__init__(message)
        self.category = category
        self.retry_after = retry_after


def eprint(*parts: object) -> None:
    print(*parts, file=sys.stderr)


def api_key_from(args: argparse.Namespace) -> str:
    key = getattr(args, "api_key", None) or os.environ.get("TRIPO_API_KEY")
    if not key:
        raise TripoError("Missing API key. Set TRIPO_API_KEY or pass --api-key.", "missing_credentials")
    return key


def error_category(code: Any = None, http_status: int | None = None) -> str:
    # Tripo reports exhausted credits as code 2010 (HTTP 403/400/200) or HTTP 402.
    if str(code) == "2010" or http_status == 402:
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
    """Retry only idempotent reads, never a task or upload POST."""
    for attempt in range(GET_ATTEMPTS):
        try:
            return operation()
        except TripoError as exc:
            if exc.category != "transient" or attempt + 1 == GET_ATTEMPTS:
                raise
            delay = min(RETRY_DELAY_CAP, max(2 ** attempt, exc.retry_after or 0))
            eprint(f"Transient GET failure; retry {attempt + 1}/{GET_ATTEMPTS - 1} in {delay:g}s")
            time.sleep(delay)


def request_once(req: request.Request, timeout: int) -> tuple[bytes, Any]:
    base = active_base_url()
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), resp.headers
    except error.HTTPError as exc:
        try:
            data = json.loads(exc.read())
            code = data.get("code") if isinstance(data, dict) else None
            msg = data.get("message") if isinstance(data, dict) else None
        except (ValueError, OSError, IncompleteRead):
            code = None
            msg = None
        finally:
            exc.close()
        category = error_category(code, exc.code)
        if req.get_method() == "GET" and not req.full_url.startswith(base + "/") and exc.code in {401, 403}:
            category = "expired_download"
        # A timed-out/5xx task POST may have committed before the error arrived.
        if req.get_method() != "GET" and category == "transient" and exc.code != 429:
            category = "unknown_submission"
        detail = f" ({msg})" if msg else ""
        raise TripoError(
            f"HTTP {exc.code}; provider code {code}; {category}{detail}.",
            category,
            retry_after_seconds(exc.headers),
        ) from exc
    except (error.URLError, OSError, IncompleteRead) as exc:
        category = "transient" if req.get_method() == "GET" else "unknown_submission"
        raise TripoError(f"{req.get_method()} interrupted; {category}.", category) from exc


def json_request(api_key: str, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(f"{active_base_url()}{path}", data=body, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    if payload is not None:
        req.add_header("Content-Type", "application/json")

    def fetch() -> dict[str, Any]:
        raw, _headers = request_once(req, 60)
        try:
            data = json.loads(raw)
            if not isinstance(data, dict) or type(data.get("code")) is not int:
                raise ValueError("Missing numeric response code")
        except (ValueError, UnicodeError) as exc:
            category = "transient" if method == "GET" else "unknown_submission"
            raise TripoError("Invalid JSON response from Tripo.", category) from exc
        if data.get("code") != 0:
            category = error_category(data.get("code"))
            msg = f" ({data.get('message')})" if data.get("message") else ""
            raise TripoError(f"Provider code {data.get('code')}; {category}{msg}.", category)
        if method == "GET" and path.startswith("/tasks/"):
            task = data.get("data")
            if not isinstance(task, dict) or not isinstance(task.get("status"), str):
                raise TripoError("Status response did not include a task status.", "transient")
            if task.get("output") is not None and not isinstance(task["output"], dict):
                raise TripoError("Status response contained malformed task outputs.", "transient")
        return data

    return safe_get(fetch) if method == "GET" else fetch()


CHECKPOINT_ARGS = set("""
command prompt image negative_prompt model_version model_seed image_seed texture_seed
texture_quality geometry_quality face_limit no_texture no_pbr smart_low_poly quad auto_size
compress generate_parts no_export_uv enable_image_autofix texture_alignment orientation
type original_task_id texture_prompt no_delight out_format rig_type spec animation animations
animate_in_place no_bake_animation no_export_with_geometry format texture_size texture_format
bake force_symmetry flatten_bottom flatten_bottom_threshold pivot_to_center_bottom
scale_factor export_orientation texture_packaging smart_uv style block_size model_task_id
rig_retries rig_model_version force_rig wait download out_dir interval timeout
""".split())


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
    """An operational journal: no credentials, upload tokens, or output URLs.

    A persisted 'submitting' intent without an accepted ID is ambiguous, even if
    the process died before sending. Only explicit task-ID reconciliation clears
    it; restarting the command never creates a replacement paid task.
    """
    def __init__(self, path: Path | None, data: dict[str, Any]):
        self.path = path
        self.data = data

    def save(self) -> None:
        if self.path is not None:
            atomic_write(self.path, json.dumps(self.data, indent=2).encode("utf-8"))

    def stage(self, name: str) -> dict[str, Any]:
        return self.data["stages"].setdefault(name, {"state": "prepared", "files": {}})

    def record_task(self, name: str, task: dict[str, Any]) -> None:
        stage = self.stage(name)
        output = task.get("output") or {}
        stage["task"] = {key: task[key] for key in ("task_id", "status", "progress", "error_code") if key in task}
        stage["task"]["output"] = {}
        if type(output.get("riggable")) is bool:
            stage["task"]["output"]["riggable"] = output["riggable"]
        if isinstance(output.get("rig_type"), str):
            stage["task"]["output"]["rig_type"] = output["rig_type"]
        stage["state"] = task.get("status") if task.get("status") in FINAL_STATUSES else "submitted"
        stage.pop("last_error", None)
        self.save()


@contextmanager
def checkpoint_file(path: Path) -> Iterator[None]:
    """OS locks release on process death; the stable lock file is intentionally kept."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with Path(f"{path}.lock").open("a+b") as handle:
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
            raise TripoError(f"Checkpoint already in use: {path}", "checkpoint_error") from exc
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
    if options.get("image"):
        # A remote reference can be a signed URL. Re-supply it only if no task was
        # accepted; accepted jobs need just their IDs, never the source URL again.
        options["image"] = None if options["image"].startswith(("http://", "https://")) else str(Path(options["image"]).expanduser().resolve())
    data = {"version": 1, "command": args.command, "args": options, "stages": {}}
    checkpoint = getattr(args, "checkpoint", None)
    if checkpoint is None:
        yield Checkpoint(None, data)
        return
    path = Path(checkpoint).expanduser().resolve()
    with checkpoint_file(path):
        if path.exists():
            raise TripoError(f"Checkpoint already exists; use resume {path}.", "checkpoint_error")
        job = Checkpoint(path, data)
        job.save()
        args.out_dir = options["out_dir"]
        if options.get("image") is not None:
            args.image = options["image"]
        yield job


def ensure_task(
    api_key: str,
    job: Checkpoint,
    name: str,
    task_type: str,
    payload: dict[str, Any] | Callable[[], dict[str, Any]],
) -> str:
    stage = job.stage(name)
    if stage.get("task_id"):
        return stage["task_id"]
    if stage["state"] in {"submitting", "unknown_submission"}:
        raise TripoError(
            f"Stage {name!r} has an uncertain POST outcome. Find its task ID in Tripo, then "
            "use resume CHECKPOINT --task-id ID to reconcile it. No new task was submitted.",
            "unknown_submission",
        )
    endpoint = TASK_ENDPOINTS.get(task_type)
    if not endpoint:
        raise TripoError(f"Unsupported Tripo v3 task type: {task_type!r}.", "invalid_input")
    built = payload() if callable(payload) else payload
    intent: dict[str, Any] = {"type": task_type}
    # Never record raw signed URLs or upload tokens in the checkpoint intent; only parent task IDs.
    raw_input = built.get("input")
    if isinstance(raw_input, str) and not raw_input.startswith(("http://", "https://")) and task_type != "image_to_model":
        intent["input"] = raw_input
    stage["request"] = intent
    stage["state"] = "submitting"
    stage.pop("last_error", None)
    job.save()

    def accepted(task_id: str) -> None:
        stage.update(task_id=task_id, state="submitted")
        job.save()

    try:
        return submit_task(api_key, endpoint, built, on_accepted=accepted)
    except BaseException as exc:
        if not stage.get("task_id"):
            category = exc.category if isinstance(exc, TripoError) else "unknown_submission"
            stage["state"] = "unknown_submission" if category == "unknown_submission" else "rejected"
            stage["last_error"] = category
            job.save()
        raise


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path.resolve()), "size": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def file_matches(record: dict[str, Any]) -> bool:
    try:
        path = Path(record["path"])
        return path.is_file() and record["size"] > 0 and path.stat().st_size == record["size"] and hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
    except (OSError, KeyError, TypeError):
        return False


def finish_stage(api_key: str, job: Checkpoint, name: str, args: argparse.Namespace, out_dir: Path | None = None) -> tuple[dict[str, Any], list[Path]]:
    stage = job.stage(name)
    task_id = stage["task_id"]
    task = stage.get("task")
    fresh_task = False
    try:
        if task is None or task.get("status") not in FINAL_STATUSES:
            task = wait_for_task(api_key, task_id, args.interval, args.timeout,
                                 on_update=lambda result: job.record_task(name, result))
            job.record_task(name, task)
            fresh_task = True
        if task.get("status") != "success" or out_dir is None:
            return task, []
        records = stage["files"]
        if stage.get("downloads_complete") and all(file_matches(record) for record in records.values()):
            return task, [Path(record["path"]) for record in records.values()]
        if not fresh_task:
            # Refresh signed download URLs from the accepted task, never from disk.
            task = get_task(api_key, task_id)
            job.record_task(name, task)
            if task.get("status") != "success":
                return task, []
        paths = download_outputs(task, out_dir, job=job, stage_name=name)
        return task, paths
    except TripoError as exc:
        stage["last_error"] = exc.category
        job.save()
        raise


def require_success(task: dict[str, Any]) -> None:
    if task.get("status") != "success":
        category = "exhausted_credits" if str(task.get("error_code")) == "2010" else "task_failed"
        raise TripoError(f"Task {task.get('task_id')} ended as {task.get('status')} (error_code={task.get('error_code')}).", category)


def multipart_upload(api_key: str, file_path: Path) -> str:
    if not file_path.is_file():
        raise TripoError(f"File not found: {file_path}")
    ext = file_path.suffix.lower().lstrip(".")
    if ext == "jpg":
        ext = "jpeg"
    image_exts = {"png", "jpeg", "webp"}
    model_exts = {"glb", "gltf", "fbx", "obj", "stl"}
    if ext not in image_exts and ext not in model_exts:
        raise TripoError("Tripo v3 file upload accepts png/jpeg/webp images or glb/gltf/fbx/obj/stl models.")
    max_bytes = (20 if ext in image_exts else 150) * 1024 * 1024
    if file_path.stat().st_size > max_bytes:
        raise TripoError(f"Tripo upload limit is {max_bytes // (1024 * 1024)}MB for {ext} files.")
    mime = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

    boundary = f"tripo-boundary-{int(time.time() * 1000)}"
    content = file_path.read_bytes()
    parts = [
        f"--{boundary}\r\n".encode(),
        (
            f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode(),
        content,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    body = b"".join(parts)
    req = request.Request(f"{active_base_url()}/files", data=body, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Content-Length", str(len(body)))
    raw, _headers = request_once(req, 120)
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise TripoError("Invalid upload response; no generation task was submitted.", "transient") from exc
    if not isinstance(data, dict):
        raise TripoError("Invalid upload response; no generation task was submitted.", "transient")
    if data.get("code") != 0:
        raise TripoError(f"Upload rejected; provider code {data.get('code')}.", error_category(data.get("code")))
    result = data.get("data")
    token = (result.get("file_token") or result.get("image_token")) if isinstance(result, dict) else None
    if not isinstance(token, str) or not token:
        raise TripoError("Upload response did not include file_token; no generation task was submitted.", "transient")
    return token


def submit_task(api_key: str, endpoint: str, payload: dict[str, Any], on_accepted: Callable[[str], None] | None = None) -> str:
    data = json_request(api_key, "POST", endpoint, payload)
    result = data.get("data")
    task_id = result.get("task_id") if isinstance(result, dict) else None
    if not isinstance(task_id, str) or not task_id.strip() or "/" in task_id:
        raise TripoError("Task response did not include a valid task_id; submission outcome is unknown.", "unknown_submission")
    if on_accepted is not None:
        on_accepted(task_id)
    print(task_id)
    return task_id


def get_task(api_key: str, task_id: str) -> dict[str, Any]:
    task = json_request(api_key, "GET", f"/tasks/{parse.quote(task_id, safe='')}").get("data")
    if not isinstance(task, dict):
        raise TripoError(f"Missing task data for {task_id}.", "transient")
    if task.get("task_id", task_id) != task_id:
        raise TripoError(f"Task response ID did not match {task_id}.", "invalid_input")
    task.setdefault("task_id", task_id)
    return task


def wait_for_task(api_key: str, task_id: str, interval: int, timeout: int, on_update: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    start = time.monotonic()
    while True:
        data = get_task(api_key, task_id)
        if on_update is not None:
            on_update(data)
        status = data.get("status", "unknown")
        progress = data.get("progress", 0)
        eprint(f"{task_id}: {status} {progress}%")
        if status in FINAL_STATUSES:
            return data
        if time.monotonic() - start > timeout:
            raise TripoError(f"Timed out waiting for task {task_id}; resume the accepted task.", "transient")
        time.sleep(interval)


def safe_name(value: str) -> str:
    keep = []
    for char in value.lower():
        if char.isalnum():
            keep.append(char)
        elif char in {"-", "_", " "}:
            keep.append("-")
    name = "".join(keep).strip("-")
    while "--" in name:
        name = name.replace("--", "-")
    return name or "asset"


def extension_for(key: str, url: str, content_type: str | None = None) -> str:
    path = parse.urlparse(url).path
    ext = Path(path).suffix
    if ext:
        return ext
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return guessed
    if "image" in key:
        return ".png"
    return ".glb"


def download_url(url: str, out_dir: Path, filename_base: str, key: str) -> Path:
    req = request.Request(url, method="GET")
    content, headers = safe_get(lambda: request_once(req, 300))
    if not content:
        raise TripoError(f"Empty downloaded artifact for {key}.", "invalid_artifact")
    ext = extension_for(key, url, headers.get("Content-Type"))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{safe_name(filename_base)}-{safe_name(key)}{ext}"
    atomic_write(path, content)
    return path


def extract_output_urls(output: dict[str, Any]) -> dict[str, str]:
    """Extract downloadable URLs preferring v3 *_url keys with legacy v2 fallback."""
    urls: dict[str, str] = {}
    seen_urls: set[str] = set()
    for canonical, candidates in DOWNLOAD_KEY_MAP:
        for candidate in candidates:
            value = output.get(candidate)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                if value not in seen_urls:
                    urls[canonical] = value
                    seen_urls.add(value)
                break
    for mv_key in ("generate_multiview_image_urls", "generate_multiview_image"):
        multiview = output.get(mv_key)
        if isinstance(multiview, dict):
            for key, value in multiview.items():
                if isinstance(value, str) and value.startswith(("http://", "https://")) and value not in seen_urls:
                    urls[key] = value
                    seen_urls.add(value)
    return urls


def download_outputs(task: dict[str, Any], out_dir: Path, *, job: Checkpoint | None = None, stage_name: str = "task") -> list[Path]:
    task_id = task["task_id"]
    output = task.get("output") or {}
    paths: list[Path] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{task_id}.json").write_text(json.dumps(task, indent=2), encoding="utf-8")
    urls = extract_output_urls(output)
    records = job.stage(stage_name)["files"] if job is not None else {}
    for key, url in urls.items():
        if key in records and file_matches(records[key]):
            path = Path(records[key]["path"])
        else:
            path = download_url(url, out_dir, task_id, key)
            records[key] = file_record(path)
            if job is not None:
                job.save()
        paths.append(path)
        print(path)
    if job is not None:
        job.stage(stage_name)["downloads_complete"] = True
        job.save()
    if not paths:
        eprint("No downloadable output URLs found.")
    return paths


def inspect_glb_structure(path: Path) -> tuple[list[str], list[str]]:
    """Validate GLB nodes/skins and return (all_node_names, skin_joint_names)."""
    gltf, _bin_chunk = load_glb(path)
    nodes = gltf.get("nodes", [])
    if not isinstance(nodes, list) or any(not isinstance(node, dict) or not isinstance(node.get("name", ""), str) for node in nodes):
        raise TripoError(f"Malformed GLB nodes: {path}", "invalid_artifact")
    skins = gltf.get("skins", [])
    if not isinstance(skins, list):
        raise TripoError(f"Malformed GLB skins: {path}", "invalid_artifact")

    def valid_index(value: Any, count: int) -> bool:
        return type(value) is int and 0 <= value < count

    for node in nodes:
        children = node.get("children", [])
        if not isinstance(children, list) or any(not valid_index(child, len(nodes)) for child in children):
            raise TripoError(f"Malformed GLB child node indices: {path}", "invalid_artifact")
        if "skin" in node and not valid_index(node["skin"], len(skins)):
            raise TripoError(f"Malformed GLB skin index: {path}", "invalid_artifact")
    joint_names: list[str] = []
    for skin in skins:
        if not isinstance(skin, dict) or not isinstance(skin.get("joints"), list) or not skin["joints"]:
            raise TripoError(f"Malformed GLB skin joints: {path}", "invalid_artifact")
        if any(not valid_index(joint, len(nodes)) for joint in skin["joints"]):
            raise TripoError(f"Invalid GLB joint index: {path}", "invalid_artifact")
        if "skeleton" in skin and not valid_index(skin["skeleton"], len(nodes)):
            raise TripoError(f"Invalid GLB skeleton index: {path}", "invalid_artifact")
        if "inverseBindMatrices" in skin:
            accessors = gltf.get("accessors", [])
            if not isinstance(accessors, list) or not valid_index(skin["inverseBindMatrices"], len(accessors)):
                raise TripoError(f"Invalid GLB inverse bind accessor: {path}", "invalid_artifact")
        for joint_idx in skin["joints"]:
            jname = nodes[joint_idx].get("name")
            if jname:
                joint_names.append(jname)
    all_names = [node["name"] for node in nodes if node.get("name")]
    return all_names, joint_names


def glb_node_names(path: Path) -> list[str]:
    names, _joints = inspect_glb_structure(path)
    return names


def glb_bone_names(path: Path) -> list[str]:
    return [name for name in glb_node_names(path) if name.startswith("tripo::")]


LEGACY_BIPED_PAIRED_BONES = ("Clavicle", "Upperarm", "Forearm", "Hand", "Thigh", "Calf", "Foot")


def _extract_lr_side(name: str) -> tuple[str, str] | None:
    """Detect left/right bone naming across Mixamo, Unity, Unreal, VRM, and ActorCore."""
    patterns = (
        (r"^(.*?)Left([A-Z_].*|$)", "L"),
        (r"^(.*?)Right([A-Z_].*|$)", "R"),
        (r"^([A-Za-z0-9:_-]+)[._-]L$", "L"),
        (r"^([A-Za-z0-9:_-]+)[._-]R$", "R"),
        (r"^([A-Za-z0-9:_-]+)_l$", "L"),
        (r"^([A-Za-z0-9:_-]+)_r$", "R"),
        (r"^L_(.+)$", "L"),
        (r"^R_(.+)$", "R"),
    )
    for pattern, side in patterns:
        m = re.match(pattern, name)
        if m:
            stem = "".join(m.groups())
            return side, stem
    return None


def validate_rig_glb(path: Path, rig_type: str) -> tuple[str, list[str]]:
    """Validate rig skeletons across v3.0 (tripo/mixamo/unity/unreal/vrm/actorcore),
    v2.x (tripo::<row>_<side>_Limb_<n>), and v1.0-20240301 (L_/R_ anatomical)."""
    names, skin_joints = inspect_glb_structure(path)
    bones = [n for n in names if n.startswith("tripo::")]
    if bones:
        return f"{len(bones)} tripo:: bones: {', '.join(sorted(bones))}", validate_rig_bones(bones, rig_type)

    left = {n[2:] for n in names if n.startswith("L_")}
    right = {n[2:] for n in names if n.startswith("R_")}
    if left or right:
        problems = []
        for part in LEGACY_BIPED_PAIRED_BONES:
            if part not in left or part not in right:
                problems.append(f"legacy rig missing L_/R_ {part}")
        if left != right:
            problems.append(f"legacy rig asymmetric bones: {sorted(left.symmetric_difference(right))}")
        if rig_type != "biped":
            problems.append(f"legacy anatomical skeleton is biped-only; requested rig_type {rig_type!r}")
        return f"legacy anatomical skeleton, {len(left)} paired L/R bones: {', '.join(sorted(left))}", problems

    # Standard v3.0 engine skeletons (mixamo, unity, unreal, vrm, actorcore, or others)
    if skin_joints:
        problems: list[str] = []
        min_joints = 12 if rig_type == "biped" else 4
        if len(skin_joints) < min_joints:
            problems.append(f"suspiciously small skinned skeleton ({len(skin_joints)} joints; expected >= {min_joints})")
        sided_l: set[str] = set()
        sided_r: set[str] = set()
        for joint in skin_joints:
            side_match = _extract_lr_side(joint)
            if side_match:
                side, stem = side_match
                (sided_l if side == "L" else sided_r).add(stem)
        if rig_type == "biped":
            if not sided_l and not sided_r:
                problems.append("skinned biped skeleton has no recognizable left/right paired limbs")
            elif sided_l != sided_r:
                diff = sorted(sided_l.symmetric_difference(sided_r))
                if len(diff) > 2:
                    problems.append(f"skinned biped skeleton has asymmetric L/R joints: {diff[:6]}")
        return f"standard skinned skeleton ({len(skin_joints)} joints, {len(sided_l)}/{len(sided_r)} L/R paired)", problems

    return "no recognizable rig bones", ["no tripo::, legacy L_/R_, or skinned joints found in rig GLB"]


def validate_rig_bones(bones: list[str], rig_type: str) -> list[str]:
    """Return problems with a downloaded tripo:: rig's skeleton."""
    problems: list[str] = []
    if not bones:
        problems.append("no tripo:: bones found in rig GLB")
        return problems
    rows: dict[str, dict[str, int]] = {}
    for bone in bones:
        if "_Limb_" not in bone:
            continue
        row, side = bone.split("::")[-1].split("_")[0:2]
        rows.setdefault(row, {}).setdefault(side, 0)
        rows[row][side] += 1
    for row, sides in sorted(rows.items()):
        if set(sides) != {"Left", "Right"}:
            problems.append(f"limb row {row} has only {'/'.join(sorted(sides))} (asymmetric rig)")
            continue
        left, right = sides["Left"], sides["Right"]
        if abs(left - right) > 1:
            problems.append(f"limb row {row} chain depth mismatch: Left={left} vs Right={right}")
        if rig_type in {"biped", "quadruped"} and min(left, right) < 3:
            problems.append(f"limb row {row} chain too shallow ({min(left, right)} bones; need >=3 for joint articulation)")
    if rig_type in {"biped", "quadruped"} and len(rows) < 2:
        problems.append(f"only {len(rows)} limb row(s); {rig_type} needs arms and legs (2 rows)")
    if rig_type == "biped" and not any(b.startswith("tripo::Head") for b in bones) and len(bones) < 12:
        problems.append(f"suspiciously small skeleton ({len(bones)} bones)")
    return problems


def add_common_model_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model", "--model-version", dest="model_version", default=DEFAULT_MODEL_VERSION,
        help=f"Tripo v3 model ID (default: {DEFAULT_MODEL_VERSION}; P-series quads: P2-20260801)",
    )
    parser.add_argument("--negative-prompt")
    parser.add_argument("--model-seed", type=int)
    parser.add_argument("--image-seed", type=int)
    parser.add_argument("--texture-seed", type=int)
    parser.add_argument("--texture-quality", choices=["fast", "standard", "detailed", "extreme"])
    parser.add_argument("--geometry-quality", choices=["standard", "detailed"])
    parser.add_argument("--face-limit", type=int)
    parser.add_argument("--no-texture", action="store_true")
    parser.add_argument("--no-pbr", action="store_true")
    parser.add_argument("--smart-low-poly", action="store_true")
    parser.add_argument("--quad", action="store_true")
    parser.add_argument("--auto-size", action="store_true")
    parser.add_argument("--compress", choices=["geometry", "meshopt"])
    parser.add_argument("--generate-parts", action="store_true")
    parser.add_argument("--no-export-uv", action="store_true")


def apply_common_model_args(args: argparse.Namespace, payload: dict[str, Any]) -> None:
    mapping = {
        "negative_prompt": args.negative_prompt,
        "model_seed": args.model_seed,
        "image_seed": args.image_seed,
        "texture_seed": args.texture_seed,
        "texture_quality": args.texture_quality,
        "geometry_quality": args.geometry_quality,
        "face_limit": args.face_limit,
        "smart_low_poly": True if args.smart_low_poly else None,
        "quad": True if args.quad else None,
        "auto_size": True if args.auto_size else None,
        "compress": args.compress,
        "generate_parts": True if args.generate_parts else None,
    }
    for key, value in mapping.items():
        if value is not None:
            payload[key] = value
    if args.no_texture:
        payload["texture"] = False
    if args.no_pbr:
        payload["pbr"] = False
    if args.no_export_uv:
        payload["export_uv"] = False


def maybe_wait_and_download(api_key: str, task_id: str, args: argparse.Namespace, job: Checkpoint | None = None) -> dict[str, Any] | None:
    if not args.wait:
        return None
    if job is not None:
        task, _paths = finish_stage(api_key, job, "task", args, Path(args.out_dir) if args.download else None)
    else:
        task = wait_for_task(api_key, task_id, args.interval, args.timeout)
    print(json.dumps(task, indent=2))
    require_success(task)
    if args.download and job is None:
        download_outputs(task, Path(args.out_dir))
    return task


def cmd_text(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    payload: dict[str, Any] = {
        "prompt": args.prompt,
        "model": args.model_version,
    }
    apply_common_model_args(args, payload)
    with job_context(args) as job:
        task_id = ensure_task(api_key, job, "task", "text_to_model", payload)
        maybe_wait_and_download(api_key, task_id, args, job)


def cmd_image(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)

    def payload() -> dict[str, Any]:
        image = args.image
        if not image:
            raise TripoError("Remote image URLs are not saved. Resume with --image URL (or a local path).")
        source_input = image if image.startswith(("http://", "https://")) else multipart_upload(api_key, Path(image))
        built: dict[str, Any] = {
            "input": source_input,
            "model": args.model_version,
        }
        if args.enable_image_autofix:
            built["enable_image_autofix"] = True
        if args.texture_alignment:
            built["texture_alignment"] = args.texture_alignment
        if args.orientation:
            built["orientation"] = args.orientation
        apply_common_model_args(args, built)
        return built

    with job_context(args) as job:
        task_id = ensure_task(api_key, job, "task", "image_to_model", payload)
        maybe_wait_and_download(api_key, task_id, args, job)


def cmd_status(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    print(json.dumps(get_task(api_key, args.task_id), indent=2))


def cmd_download(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    task = get_task(api_key, args.task_id)
    if task.get("status") != "success":
        raise TripoError(f"Task is {task.get('status')}; download URLs are available after success.")
    download_outputs(task, Path(args.out_dir))


def normalized_post_type(value: str) -> str:
    aliases = {
        "convert": "conversion",
        "convert_model": "conversion",
        "conversion": "conversion",
        "texture": "texture_model",
        "retarget": "animate_retarget",
        "rig": "animate_rig",
        "prerig": "animate_prerigcheck",
        "prerigcheck": "animate_prerigcheck",
        "rig-check": "animate_prerigcheck",
        "lowpoly": "highpoly_to_lowpoly",
        "decimate": "highpoly_to_lowpoly",
    }
    return aliases.get(value, value)


def cmd_postprocess(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    task_type = normalized_post_type(args.type)
    if task_type == "stylize_model":
        raise TripoError(
            "stylize_model was deprecated and removed in Tripo API v3. "
            "Use prompt styling on text/image generation or shader/voxel post-processing in Three.js instead.",
            "invalid_input",
        )
    if task_type not in TASK_ENDPOINTS:
        raise TripoError(f"Unknown postprocess type: {args.type!r}", "invalid_input")

    payload: dict[str, Any] = {
        "input": args.original_task_id,
    }
    default_versions = {
        "texture_model": DEFAULT_TEXTURE_MODEL_VERSION,
        "highpoly_to_lowpoly": DEFAULT_DECIMATE_MODEL_VERSION,
    }
    if task_type == "animate_prerigcheck":
        if args.model_version:
            eprint("warning: rig-check takes no model parameter; ignoring it")
    elif args.model_version and args.model_version.lower() in {"default", "none"}:
        # Omit model to let the API infer the compatible retarget path (required for v1.0 rigs).
        pass
    elif task_type == "animate_rig" and not args.model_version:
        rig_type = args.rig_type or "biped"
        resolved = resolve_rig_version(rig_type, None)
        payload["model"] = resolved
        eprint(f"Using model={resolved} for rig_type={rig_type}")
    elif task_type == "animate_retarget":
        if args.model_version:
            if args.model_version.startswith("v1.0"):
                eprint("note: v1.0-rig retarget omits explicit model (API rejects v1.0 in retarget)")
            else:
                payload["model"] = args.model_version
    else:
        model = args.model_version or default_versions.get(task_type)
        if model:
            payload["model"] = model

    if task_type == "texture_model":
        if not args.texture_prompt:
            raise TripoError("--texture-prompt is required for texture_model")
        payload["texture_prompt"] = {"text": args.texture_prompt}
        if args.texture_quality:
            payload["texture_quality"] = args.texture_quality
        if args.no_delight:
            payload["delight"] = False
    elif task_type == "animate_rig":
        if args.out_format:
            payload["out_format"] = args.out_format
        if args.rig_type:
            payload["rig_type"] = args.rig_type
        if args.spec:
            payload["spec"] = args.spec
    elif task_type == "animate_retarget":
        # v1.0 legacy rig retargets (explicit --model v1.0-20240301 or --model default with preset:biped:*)
        # require FBX output and one clip per task due to twist-bone GLB bake corruption.
        legacy_retarget = bool(
            args.model_version and (args.model_version.lower() in {"default", "none"} or args.model_version.startswith("v1.0"))
        )
        if legacy_retarget and (args.out_format or "glb") != "fbx":
            if args.out_format == "glb":
                raise TripoError(
                    "v1.0-rig retargets must use --out-format fbx: Tripo's v1.0 GLB bake corrupts "
                    "twist-bone transforms. Load the FBX with FBXLoader or rig with v3.0-20260909."
                )
            eprint("note: v1.0-rig retarget defaults to out_format=fbx (GLB bake is broken on v1.0)")
            payload["out_format"] = "fbx"
        if legacy_retarget and args.animations:
            raise TripoError(
                "v1.0-rig retargets must request ONE animation per task to avoid colliding armatures "
                "in FBX. Submit separate tasks with --animation, or use a v3.0-20260909 rig."
            )
        if args.animations:
            animations = [item.strip() for item in args.animations.split(",") if item.strip()]
            validate_animations(animations, rig_model_version=payload.get("model"))
            if len(animations) > RETARGET_BATCH_LIMIT:
                raise TripoError(
                    f"animate_retarget accepts at most {RETARGET_BATCH_LIMIT} animations per task; "
                    f"got {len(animations)}. Split into multiple tasks."
                )
            payload["animations"] = animations
        elif args.animation:
            validate_animations([args.animation], rig_model_version=payload.get("model"))
            payload["animation"] = args.animation
        else:
            raise TripoError("--animation or --animations is required for animate_retarget")
        if args.out_format:
            payload["out_format"] = args.out_format
        if args.animate_in_place:
            eprint(
                "warning: animate_in_place has historically corrupted baked root/limb motion on v1.0/v2.5 rigs. "
                "Prefer baked root motion and strip horizontal Root.position X/Z in Three.js."
            )
            payload["animate_in_place"] = True
        if args.no_bake_animation:
            payload["bake_animation"] = False
        if args.no_export_with_geometry:
            payload["export_with_geometry"] = False
    elif task_type == "conversion":
        if not args.format:
            raise TripoError("--format is required for conversion")
        payload["format"] = args.format
        for key in (
            "face_limit",
            "texture_size",
            "texture_format",
            "flatten_bottom_threshold",
            "scale_factor",
            "export_orientation",
            "texture_packaging",
        ):
            value = getattr(args, key)
            if value is not None:
                payload[key] = value
        for flag in ("quad", "force_symmetry", "flatten_bottom", "pivot_to_center_bottom", "bake"):
            if getattr(args, flag):
                payload[flag] = True
    elif task_type == "highpoly_to_lowpoly":
        if args.face_limit:
            payload["face_limit"] = args.face_limit
        if args.quad:
            payload["quad"] = True
        if args.smart_uv:
            payload["smart_uv"] = True

    with job_context(args) as job:
        task_id = ensure_task(api_key, job, "task", task_type, payload)
        maybe_wait_and_download(api_key, task_id, args, job)


def resolve_rig_version(rig_type: str, override: str | None) -> str:
    """Route rigging model by body plan under Tripo API v3:
    biped/others -> v3.0-20260909 (supports tripo/mixamo/unity/unreal/vrm/actorcore),
    non-biped creatures -> v2.5-20260210. Pass override='v1.0-20240301' for legacy bipeds."""
    if override:
        return override
    return RIG_BIPED_MODEL_VERSION if rig_type in {"biped", "others"} else RIG_MODEL_VERSION


def to_legacy_biped_presets(animations: list[str]) -> list[str]:
    """v1.0 rigs use the preset:biped:* library; map plain names onto it automatically."""
    mapped = []
    for animation in animations:
        suffix = animation[len("preset:"):] if animation.startswith("preset:") else None
        if suffix and ":" not in suffix:
            mapped.append(f"preset:biped:{suffix}")
        else:
            mapped.append(animation)
    return mapped


def cmd_character_pipeline(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    if not args.model_task_id and not args.prompt:
        raise TripoError("--prompt is required unless --model-task-id reuses an existing generation task")
    animations = [item.strip() for item in args.animations.split(",") if item.strip()]
    if animations and args.spec != "tripo":
        raise TripoError(
            f"spec={args.spec} rigs are intended for external animation pipelines, not Tripo animate_retarget. "
            "Use --animations '' to export the rigged model only, or keep --spec tripo for Tripo presets."
        )
    validate_animations(animations, None, None)

    with job_context(args) as job:
        run_character_pipeline(args, api_key, job, animations)


def run_character_pipeline(args: argparse.Namespace, api_key: str, job: Checkpoint, animations: list[str]) -> None:
    out_dir = Path(args.out_dir)
    if args.model_task_id:
        model_task_id = args.model_task_id
        eprint(f"Skipping generation; reusing model task {model_task_id}")
        stage = job.stage("model")
        if not stage.get("task_id"):
            stage.update(task_id=model_task_id, state="submitted")
            job.save()
    else:
        prompt = args.prompt
        if (args.rig_type in (None, "biped")
                and "t-pose" not in prompt.lower() and "a-pose" not in prompt.lower()):
            prompt = (
                f"{prompt}, full-body T-pose for rigging, arms straight out to the sides, "
                "legs apart and visible, front facing, symmetric, no props attached to the body"
            )
        text_payload: dict[str, Any] = {
            "prompt": prompt,
            "model": args.model_version,
            "texture_quality": args.texture_quality,
            "geometry_quality": args.geometry_quality,
            "pbr": True,
        }
        if args.face_limit:
            text_payload["face_limit"] = args.face_limit
        model_task_id = ensure_task(api_key, job, "model", "text_to_model", text_payload)
    model_task, _model_paths = finish_stage(api_key, job, "model", args, out_dir / "base")
    require_success(model_task)
    eprint("Check the downloaded rendered_image: the character must be in a clear T/A-pose before rigging.")
    if args.stop_after == "model":
        eprint(f"Stopped after model {model_task_id}. Inspect the downloads. " + (
            "Resume the checkpoint to continue rigging." if job.path else
            f"Continue with character-pipeline --model-task-id {model_task_id}."
        ))
        return

    ensure_task(api_key, job, "prerigcheck", "animate_prerigcheck", {
        "input": model_task_id,
    })
    check_task, _check_paths = finish_stage(api_key, job, "prerigcheck", args)
    print(json.dumps(check_task, indent=2))
    require_success(check_task)
    output = check_task.get("output") or {}
    if output.get("riggable") is False:
        if not args.force_rig:
            raise TripoError(
                f"Prerigcheck reports the model is not riggable: {output}. "
                "Best fix: regenerate with a clearer full-body T-pose (or a T-pose reference image). "
                "Pass --force-rig to attempt rigging anyway."
            )
        eprint("warning: proceeding despite riggable=false (--force-rig)")
    detected_rig_type = output.get("rig_type")
    rig_type = args.rig_type or detected_rig_type or "biped"
    if args.rig_type and detected_rig_type and args.rig_type != detected_rig_type:
        eprint(
            f"warning: prerigcheck detected rig_type={detected_rig_type} "
            f"but --rig-type {args.rig_type} was requested; using {args.rig_type}"
        )
    rig_model_version = resolve_rig_version(rig_type, args.rig_model_version)
    legacy = rig_model_version.startswith("v1.0")
    if legacy:
        animations = to_legacy_biped_presets(animations)
    eprint(f"Using rig_type={rig_type} model={rig_model_version}"
           + (f" animations={','.join(animations)}" if animations else ""))
    validate_animations(animations, rig_type if not legacy else None, rig_model_version)

    attempts = 1 + max(0, args.rig_retries)
    rig_id = None
    last_detail = "no rig attempt succeeded"
    last_usable_rig = None
    selected_rig_stage = job.data.get("rig_stage")
    stage_names = [f"rig-{attempt}" for attempt in range(1, attempts + 1)]
    if selected_rig_stage is not None and selected_rig_stage not in stage_names:
        raise TripoError("Checkpoint selected rig is outside the saved retry budget.", "checkpoint_error")
    attempt_numbers = [stage_names.index(selected_rig_stage) + 1] if selected_rig_stage else range(1, attempts + 1)
    for attempt in attempt_numbers:
        stage_name = f"rig-{attempt}"
        rig_payload: dict[str, Any] = {
            "input": model_task_id,
            "model": rig_model_version,
            "rig_type": rig_type,
            "out_format": "glb",
        }
        if rig_type == "biped":
            rig_payload["spec"] = args.spec
        candidate_id = ensure_task(api_key, job, stage_name, "animate_rig", rig_payload)
        suffix = "rig" if attempt == 1 else f"rig-attempt{attempt}"
        rig_task, rig_paths = finish_stage(api_key, job, stage_name, args, out_dir / suffix)
        last_usable_rig = None
        if rig_task.get("status") != "success":
            if str(rig_task.get("error_code")) == "2010":
                require_success(rig_task)
            last_detail = f"rig task ended as {rig_task.get('status')} (error_code={rig_task.get('error_code')})"
            eprint(f"rig attempt {attempt}/{attempts}: {last_detail}")
            continue
        rig_glbs = [p for p in rig_paths if p.suffix.lower() == ".glb" and p.is_file()]
        problems = ["no rig GLB artifact was downloaded"]
        if rig_glbs:
            try:
                description, problems = validate_rig_glb(rig_glbs[0], rig_type)
                last_usable_rig = candidate_id
                eprint(f"Rig skeleton ({attempt}/{attempts}): {description}")
            except TripoError as exc:
                problems = [str(exc)]
        job.stage(stage_name)["rig_validation"] = "valid" if not problems else "invalid"
        job.save()
        if not problems:
            rig_id = candidate_id
            break
        last_detail = "; ".join(problems)
        eprint(f"rig attempt {attempt}/{attempts} failed validation: {last_detail}")
    if rig_id is None:
        if not args.force_rig or last_usable_rig is None:
            raise TripoError(
                f"No structurally valid rig after {attempts} attempt(s) ({last_detail}). "
                "Retargets on a bad rig warp the character. Regenerate the base model with "
                "clearer limb separation (strict T-pose, arms horizontal, legs apart and visible, "
                "no long skirt/cape/props fusing limbs to the body). --force-rig can only use "
                "a readable GLB with structural problems; missing or malformed artifacts cannot be forced.",
                "invalid_artifact",
            )
        rig_id = last_usable_rig
        eprint(f"warning: using unvalidated rig ({last_detail}); continuing (--force-rig)")
    job.data["rig_stage"] = stage_name
    job.save()
    if args.stop_after == "rig":
        eprint(f"Stopped after rig {rig_id}. Inspect the skeleton. " + (
            "Resume the checkpoint for animations." if job.path else
            f"Use postprocess --type retarget --input {rig_id} with the desired animation presets."
        ))
        return

    # v3.0 and v2.5 rigs batch up to 5 presets per GLB retarget task;
    # legacy v1.0 rigs must run one clip per task with out_format=fbx.
    batch_size = 1 if legacy else RETARGET_BATCH_LIMIT
    for start in range(0, len(animations), batch_size):
        batch = animations[start:start + batch_size]
        retarget_payload: dict[str, Any] = {
            "input": rig_id,
            "out_format": "fbx" if legacy else "glb",
        }
        if len(batch) == 1:
            retarget_payload["animation"] = batch[0]
        else:
            retarget_payload["animations"] = batch
        if not legacy and rig_model_version.startswith("v2."):
            retarget_payload["model"] = rig_model_version
        if args.animate_in_place:
            eprint(
                "warning: animate_in_place has historically corrupted retargeted clips on v1.0/v2.5 rigs. "
                "Prefer baked root motion and strip horizontal Root.position X/Z in Three.js."
            )
            retarget_payload["animate_in_place"] = True
        stage_name = f"animation-{start // batch_size + 1}"
        ensure_task(api_key, job, stage_name, "animate_retarget", retarget_payload)
        batch_name = safe_name("-".join(item.split(":")[-1] for item in batch))
        anim_task, _anim_paths = finish_stage(api_key, job, stage_name, args, out_dir / batch_name)
        require_success(anim_task)
    eprint("Inspect gltf.animations clip names/counts in each download before wiring the AnimationMixer.")


def cmd_resume(args: argparse.Namespace) -> None:
    """Resume a single accepted job or its original character chain."""
    api_key = api_key_from(args)
    path = Path(args.checkpoint).expanduser().resolve()
    with checkpoint_file(path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise TripoError(f"Cannot read checkpoint {path}.", "checkpoint_error") from exc
        commands = {"text": cmd_text, "image": cmd_image, "postprocess": cmd_postprocess, "character-pipeline": cmd_character_pipeline}
        validate_checkpoint(data)
        command = data["command"]
        if command != "character-pipeline" and args.stop_after is not None:
            if command not in {"text", "image"} or args.stop_after != "model":
                raise TripoError("--stop-after rig|animations requires a character-pipeline checkpoint. Single jobs never add paid stages.")
        if args.image is not None and command != "image":
            raise TripoError("--image is only for resuming an image submission.")
        job = Checkpoint(path, data)
        if args.task_id:
            uncertain = [stage for stage in data["stages"].values() if not stage.get("task_id") and stage["state"] in {"submitting", "unknown_submission"}]
            if len(uncertain) != 1:
                raise TripoError("--task-id requires exactly one uncertain submission in the checkpoint.")
            stage = uncertain[0]
            task = get_task(api_key, args.task_id)
            expected = stage.get("request", {})
            if "type" in expected and "type" in task and task["type"] != expected["type"]:
                raise TripoError("Reconciled task type does not match the saved submission intent.")
            expected_parent = expected.get("input") or expected.get("original_model_task_id")
            actual_parent = task.get("input") or task.get("original_model_task_id")
            if expected_parent and actual_parent and actual_parent != expected_parent:
                raise TripoError("Reconciled task input does not match the saved submission intent.")
            stage.update(task_id=args.task_id, state="submitted")
            stage.pop("last_error", None)
            job.save()
        saved = argparse.Namespace(**{key: value for key, value in data["args"].items() if key in CHECKPOINT_ARGS})
        saved.command = command
        saved.api_key = args.api_key
        saved._job = job
        saved.stop_after = args.stop_after or "animations"
        if args.interval is not None:
            saved.interval = args.interval
        if args.timeout is not None:
            saved.timeout = args.timeout
        if args.image is not None:
            saved.image = args.image
        if command != "character-pipeline":
            saved.wait = True
            saved.download = True
        commands[command](saved)


def validate_checkpoint(data: Any) -> None:
    """Validate before dispatch: a damaged accepted ID must never look like a new job."""
    defaults_argv = {
        "text": ["text", "--prompt", "checkpoint"],
        "image": ["image", "--image", "checkpoint.png"],
        "postprocess": ["postprocess", "--type", "rig", "--input", "checkpoint-task"],
        "character-pipeline": ["character-pipeline"],
    }

    def invalid(detail: str) -> None:
        raise TripoError(f"Malformed checkpoint: {detail}.", "checkpoint_error")

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
    integer_keys = {"model_seed", "image_seed", "texture_seed", "face_limit", "texture_size", "block_size", "rig_retries", "interval", "timeout"}
    numeric_keys = {"flatten_bottom_threshold", "scale_factor"}
    for key in expected_keys:
        value = options[key]
        default = defaults[key]
        if value is None:
            if default is not None and key != "image":
                invalid(f"argument {key} cannot be null")
        elif type(default) is bool:
            if type(value) is not bool:
                invalid(f"argument {key} must be a boolean")
        elif key in integer_keys:
            if type(value) is not int:
                invalid(f"argument {key} must be an integer")
        elif key in numeric_keys:
            if type(value) not in {int, float}:
                invalid(f"argument {key} must be numeric")
        elif not isinstance(value, str):
            invalid(f"argument {key} must be text")
    if not options["out_dir"] or options["interval"] < 0 or options["timeout"] < 0:
        invalid("empty output directory or negative polling timings")
    valid_stages = {"task"}
    if command == "character-pipeline":
        animation_count = len(options["animations"].split(","))
        valid_stages = {"model", "prerigcheck"}
        valid_stages.update(f"rig-{index}" for index in range(1, 2 + max(0, options["rig_retries"])))
        valid_stages.update(f"animation-{index}" for index in range(1, animation_count + 1))
    if not set(stages).issubset(valid_stages):
        invalid("unexpected stage names")
    for name, stage in stages.items():
        if not isinstance(stage, dict) or not isinstance(stage.get("state"), str):
            invalid(f"stage {name} must have a state")
        state = stage["state"]
        if state not in FINAL_STATUSES | {"prepared", "submitting", "submitted", "unknown_submission", "rejected"}:
            invalid(f"stage {name} has an unknown state")
        task_id = stage.get("task_id")
        if "task_id" in stage and (not isinstance(task_id, str) or not task_id.strip() or "/" in task_id):
            invalid(f"stage {name} has an invalid accepted task ID")
        if (state == "submitted" or state in FINAL_STATUSES) and not task_id:
            invalid(f"stage {name} lost its accepted task ID")
        intent = stage.get("request")
        if state in {"submitting", "unknown_submission"} or intent is not None:
            if not isinstance(intent, dict) or not isinstance(intent.get("type"), str):
                invalid(f"stage {name} has a malformed submission intent")
            for parent_key in ("input", "original_model_task_id"):
                if parent_key in intent and not isinstance(intent[parent_key], str):
                    invalid(f"stage {name} has an invalid parent task ID")
        task = stage.get("task")
        if task is not None:
            if (not isinstance(task, dict) or not isinstance(task.get("status"), str)
                    or task.get("task_id") != task_id or not isinstance(task.get("output"), dict)):
                invalid(f"stage {name} has malformed task status")
            if "riggable" in task["output"] and type(task["output"]["riggable"]) is not bool:
                invalid(f"stage {name} has malformed riggability data")
            if "rig_type" in task["output"] and not isinstance(task["output"]["rig_type"], str):
                invalid(f"stage {name} has a malformed rig type")
        if not isinstance(stage.get("files"), dict):
            invalid(f"stage {name} files must be an object")
        for record in stage["files"].values():
            if (not isinstance(record, dict) or not isinstance(record.get("path"), str)
                    or type(record.get("size")) is not int or not isinstance(record.get("sha256"), str)):
                invalid(f"stage {name} has a malformed file record")
        if "downloads_complete" in stage and type(stage["downloads_complete"]) is not bool:
            invalid(f"stage {name} has malformed download status")
    if "rig_stage" in data:
        selected = data["rig_stage"]
        if not isinstance(selected, str) or selected not in stages or not stages[selected].get("task_id") or not selected.startswith("rig-"):
            invalid("selected rig must identify an accepted rig stage")


def load_glb(path: Path) -> tuple[dict[str, Any], bytes]:
    import struct
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise TripoError(f"Cannot read GLB: {path}", "invalid_artifact") from exc
    if len(data) < 20 or data[:4] != b"glTF":
        raise TripoError(f"Not a complete GLB file: {path}", "invalid_artifact")
    version, total = struct.unpack_from("<II", data, 4)
    if version != 2 or total != len(data):
        raise TripoError(f"Invalid GLB version or length: {path}", "invalid_artifact")
    offset = 12
    gltf: dict[str, Any] | None = None
    bin_chunk = b""
    while offset < len(data):
        if offset + 8 > len(data):
            raise TripoError(f"Truncated GLB chunk: {path}", "invalid_artifact")
        clen, ctype = struct.unpack_from("<II", data, offset)
        if clen % 4 or offset + 8 + clen > len(data):
            raise TripoError(f"Invalid GLB chunk length: {path}", "invalid_artifact")
        chunk = data[offset + 8:offset + 8 + clen]
        if ctype == 0x4E4F534A:
            try:
                gltf = json.loads(chunk)
            except (ValueError, UnicodeError) as exc:
                raise TripoError(f"Malformed GLB JSON: {path}", "invalid_artifact") from exc
        elif ctype == 0x004E4942:
            bin_chunk = chunk
        offset += 8 + clen
    if not isinstance(gltf, dict):
        raise TripoError(f"No valid JSON object in GLB: {path}", "invalid_artifact")
    return gltf, bin_chunk


def _read_accessor(gltf: dict[str, Any], bin_chunk: bytes, idx: int) -> list[tuple[float, ...]]:
    import struct
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


def validate_animation_glb(path: Path) -> tuple[list[str], list[str]]:
    """Keyframe-level QA for retargeted clips. Returns (report_lines, problems)."""
    import math
    gltf, bin_chunk = load_glb(path)
    nodes = gltf.get("nodes", [])
    roots = {"Armature", "Root", "Hip", "Hips", "Pelvis", "tripo::Root", "mixamorig:Hips"}
    report: list[str] = []
    problems: list[str] = []
    animations = gltf.get("animations", [])
    if not animations:
        return ["no animations in file"], ["no animation clips found"]
    for anim in animations:
        dur = 0.0
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
                base = out[0]
                amp = 0.0
                for q in out:
                    dot = abs(sum(a * b for a, b in zip(base, q)))
                    amp = max(amp, 2 * math.acos(min(1.0, dot)))
                if math.degrees(amp) > 170:
                    big_rot[name] = round(math.degrees(amp))
            elif path_kind == "scale":
                problems.append(f"{anim.get('name')}: scale track on {name} (warp risk)")
            elif path_kind == "translation" and name not in roots and name.split("::")[-1] not in roots:
                rest = node.get("translation", [0, 0, 0])
                restlen = math.sqrt(sum(c * c for c in rest)) or 1e-9
                dev = max(math.sqrt(sum((v[i] - rest[i]) ** 2 for i in range(3))) for v in out)
                if dev / restlen > 0.5:
                    problems.append(
                        f"{anim.get('name')}: translation track on non-root bone {name} deviates "
                        f"{dev / restlen:.1f}x its rest offset (limb stretch warp)"
                    )
        report.append(f"{anim.get('name')}: {dur:.2f}s, {len(anim['channels'])} channels, {len(rot_bones)} bones rotating")
        if big_rot:
            report.append(f"  rotation amplitude >170deg (check visually): {big_rot}")
    return report, problems


def cmd_validate_animation(args: argparse.Namespace) -> None:
    report, problems = validate_animation_glb(Path(args.glb_path))
    for line in report:
        print(line)
    if problems:
        raise TripoError("Animation validation failed: " + "; ".join(problems))
    print("Clips look structurally sound (verify motion visually in the engine).")


def cmd_validate_rig(args: argparse.Namespace) -> None:
    description, problems = validate_rig_glb(Path(args.glb_path), args.rig_type)
    print(description)
    if problems:
        raise TripoError("Rig validation failed: " + "; ".join(problems))
    print("Rig looks structurally valid.")


def cmd_probe(args: argparse.Namespace) -> None:
    """Print TRIPO_API_KEY=SET|MISSING and optionally validate via GET /v3/account/balance."""
    key = getattr(args, "api_key", None) or os.environ.get("TRIPO_API_KEY")
    status = "SET" if key else "MISSING"
    print(f"TRIPO_API_KEY={status}")
    if getattr(args, "validate", False) and key:
        data = json_request(key, "GET", "/account/balance").get("data") or {}
        balance = data.get("balance")
        frozen = data.get("frozen")
        if balance is not None:
            extra = f" frozen={frozen}" if frozen is not None else ""
            print(f"BALANCE={balance}{extra}")
        else:
            print("VALID_ACCOUNT=ok")


def add_shared_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-key")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--out-dir", default="tripo-output")
    parser.add_argument("--interval", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--checkpoint", metavar="PATH", help="create a resumable job journal; existing paths require resume")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tripo OpenAPI v3 3D asset helper")
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe", help="print TRIPO_API_KEY=SET|MISSING (optionally check /v3/account/balance)")
    probe.add_argument("--api-key")
    probe.add_argument("--validate", action="store_true", help="call GET /v3/account/balance to verify key and credits")
    probe.set_defaults(func=cmd_probe)

    text = sub.add_parser("text", help="submit POST /v3/generation/text-to-model")
    text.add_argument("--prompt", required=True)
    add_common_model_args(text)
    add_shared_runtime_args(text)
    text.set_defaults(func=cmd_text)

    image = sub.add_parser("image", help="submit POST /v3/generation/image-to-model from local path or URL")
    image.add_argument("--image", required=True)
    image.add_argument("--enable-image-autofix", action="store_true")
    image.add_argument("--texture-alignment", choices=["original_image", "geometry"])
    image.add_argument("--orientation", choices=["default", "align_image"])
    add_common_model_args(image)
    add_shared_runtime_args(image)
    image.set_defaults(func=cmd_image)

    status = sub.add_parser("status", help="get task status via GET /v3/tasks/{task_id}")
    status.add_argument("task_id")
    status.add_argument("--api-key")
    status.set_defaults(func=cmd_status)

    download = sub.add_parser("download", help="download successful task outputs")
    download.add_argument("task_id")
    download.add_argument("--api-key")
    download.add_argument("--out-dir", default="tripo-output")
    download.set_defaults(func=cmd_download)

    resume = sub.add_parser("resume", help="resume a checkpoint; wait/download single tasks or continue the saved character chain")
    resume.add_argument("checkpoint", metavar="CHECKPOINT")
    resume.add_argument("--api-key")
    resume.add_argument("--interval", type=int)
    resume.add_argument("--timeout", type=int)
    resume.add_argument("--stop-after", choices=["model", "rig", "animations"],
                        help="character checkpoint stage limit for this invocation (default: animations); single text/image jobs accept only model")
    resume.add_argument("--task-id", help="reconcile the one uncertain POST using its independently recovered Tripo task ID; never resubmit it")
    resume.add_argument("--image", help="re-supply an unsaved remote image URL or local path if the image task was never accepted")
    resume.set_defaults(func=cmd_resume)

    post = sub.add_parser("postprocess", help="submit Tripo v3 model/mesh/animation postprocess task")
    post.add_argument("--type", required=True, help="texture_model|conversion|decimate|rig-check|rig|retarget")
    post.add_argument("--input", "--original-task-id", dest="original_task_id", required=True,
                      help="source task_id, file_token, or model URL")
    post.add_argument("--model", "--model-version", dest="model_version")
    post.add_argument("--texture-prompt")
    post.add_argument("--texture-quality", choices=["fast", "standard", "detailed", "extreme"])
    post.add_argument("--no-delight", action="store_true", help="disable delighting on v3.5 texture_model")
    post.add_argument("--out-format", choices=["glb", "fbx"])
    post.add_argument("--rig-type", choices=list(RIG_TYPES))
    post.add_argument("--spec", choices=list(RIG_SPECS))
    post.add_argument("--animation")
    post.add_argument("--animations")
    post.add_argument("--animate-in-place", action="store_true")
    post.add_argument("--no-bake-animation", action="store_true")
    post.add_argument("--no-export-with-geometry", action="store_true")
    post.add_argument("--format", choices=["GLB", "GLTF", "USDZ", "FBX", "OBJ", "STL", "3MF"])
    post.add_argument("--face-limit", type=int)
    post.add_argument("--texture-size", type=int)
    post.add_argument("--texture-format", choices=["PNG", "JPG"])
    post.add_argument("--bake", action="store_true")
    post.add_argument("--quad", action="store_true")
    post.add_argument("--smart-uv", action="store_true", help="auto-unwrap UVs on v3/mesh/decimate (model v3.0)")
    post.add_argument("--force-symmetry", action="store_true")
    post.add_argument("--flatten-bottom", action="store_true")
    post.add_argument("--flatten-bottom-threshold", type=float)
    post.add_argument("--pivot-to-center-bottom", action="store_true")
    post.add_argument("--scale-factor", type=float)
    post.add_argument("--export-orientation", choices=["+x", "-x", "+y", "-y"])
    post.add_argument("--texture-packaging", choices=["embedded", "zip"])
    post.add_argument("--style", help=argparse.SUPPRESS)
    post.add_argument("--block-size", type=int, help=argparse.SUPPRESS)
    add_shared_runtime_args(post)
    post.set_defaults(func=cmd_postprocess)

    validate = sub.add_parser("validate-rig", help="check a downloaded rig GLB for degenerate auto-rig skeletons")
    validate.add_argument("glb_path")
    validate.add_argument("--rig-type", default="biped", choices=list(RIG_TYPES))
    validate.set_defaults(func=cmd_validate_rig)

    validate_anim = sub.add_parser("validate-animation", help="keyframe-level QA for retargeted clip GLBs (warp signatures)")
    validate_anim.add_argument("glb_path")
    validate_anim.set_defaults(func=cmd_validate_animation)

    pipeline = sub.add_parser("character-pipeline", help="generate, rig-check, rig, retarget, and download a character (v3)")
    pipeline.add_argument("--prompt")
    pipeline.add_argument("--model-task-id",
                          help="reuse an existing generation task instead of generating (skips --prompt)")
    pipeline.add_argument("--rig-retries", type=int, default=2,
                          help="extra rig attempts when validation fails; rigging is nondeterministic (default 2)")
    pipeline.add_argument("--rig-model-version", default=None,
                          help=f"rig model override. Default: auto by rig type — biped/others -> {RIG_BIPED_MODEL_VERSION}, "
                               f"creatures -> {RIG_MODEL_VERSION}. Pass v1.0-20240301 for legacy FBX bipeds.")
    pipeline.add_argument("--animations", default="preset:idle,preset:walk,preset:run")
    pipeline.add_argument("--model", "--model-version", dest="model_version", default=DEFAULT_MODEL_VERSION)
    pipeline.add_argument("--texture-quality", default="detailed", choices=["fast", "standard", "detailed", "extreme"])
    pipeline.add_argument("--geometry-quality", default="standard", choices=["standard", "detailed"])
    pipeline.add_argument("--face-limit", type=int)
    pipeline.add_argument(
        "--rig-type",
        choices=list(RIG_TYPES),
        help="override the rig-check-detected rig type (default: auto-detect, fallback biped)",
    )
    pipeline.add_argument("--spec", default="tripo", choices=list(RIG_SPECS),
                          help="skeleton naming spec for bipeds (only spec=tripo supports Tripo preset retargeting)")
    pipeline.add_argument("--force-rig", action="store_true",
                          help="attempt rigging even if rig-check reports riggable=false")
    pipeline.add_argument("--animate-in-place", action="store_true")
    pipeline.add_argument("--api-key")
    pipeline.add_argument("--out-dir", default="tripo-character")
    pipeline.add_argument("--interval", type=int, default=8)
    pipeline.add_argument("--timeout", type=int, default=900)
    pipeline.add_argument("--checkpoint", metavar="PATH", help="create a resumable character chain; accepted stages are never regenerated on resume")
    pipeline.add_argument("--stop-after", choices=["model", "rig", "animations"], default="animations",
                          help="stop after downloading this stage for inspection (default: animations); use --checkpoint to continue later")
    pipeline.set_defaults(func=cmd_character_pipeline)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except TripoError as exc:
        eprint(f"threejs_3d_asset.py: [{exc.category}] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
