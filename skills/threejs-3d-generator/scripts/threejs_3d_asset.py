#!/usr/bin/env python3
"""Small Tripo OpenAPI client for skill-driven 3D asset generation."""

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
import sys
import tempfile
import time
from typing import Any, Callable, Iterator
from urllib import error, parse, request

BASE_URL = "https://api.tripo3d.ai/v2/openapi"
FINAL_STATUSES = {"success", "failed", "banned", "expired", "cancelled", "unknown"}
DOWNLOAD_KEYS = (
    "pbr_model",
    "model",
    "base_model",
    "rendered_image",
    "generated_image",
)

RIG_MODEL_VERSION = "v2.5-20260210"
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
}
KNOWN_PRESETS = set().union(*RIG_TYPE_PRESETS.values())
RETARGET_BATCH_LIMIT = 5
GET_ATTEMPTS = 4
RETRY_DELAY_CAP = 60


def validate_animations(animations: list[str], rig_type: str | None = None, rig_model_version: str | None = None) -> None:
    """Fail fast on presets the API will reject, before any credits are spent."""
    # None = server default (used when retargeting v1.0 rigs); allow both namespaces then.
    legacy = None if rig_model_version is None else rig_model_version.startswith("v1.0")
    for animation in animations:
        if not animation.startswith("preset:"):
            continue
        if animation.startswith("preset:biped:"):
            # The large legacy clip library only works on v1.0-20240301 rigs.
            if legacy is False:
                raise TripoError(
                    f"{animation} belongs to the v1.0-20240301 rig's preset library; retarget "
                    "with --model-version default on a v1.0 rig to use it."
                )
            continue
        if legacy:
            raise TripoError(
                f"{animation} is a v2.x preset; v1.0-20240301 rigs use the preset:biped:* "
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
    # Tripo reports exhausted credits as HTTP 403, code 2010 (not an auth error).
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
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), resp.headers
    except error.HTTPError as exc:
        try:
            data = json.loads(exc.read())
            code = data.get("code") if isinstance(data, dict) else None
        except (ValueError, OSError, IncompleteRead):
            code = None
        finally:
            exc.close()
        category = error_category(code, exc.code)
        if req.get_method() == "GET" and not req.full_url.startswith(BASE_URL + "/") and exc.code in {401, 403}:
            category = "expired_download"
        # A timed-out/5xx task POST may have committed before the error arrived.
        if req.get_method() != "GET" and category == "transient" and exc.code != 429:
            category = "unknown_submission"
        raise TripoError(
            f"HTTP {exc.code}; provider code {code}; {category}.", category,
            retry_after_seconds(exc.headers),
        ) from exc
    except (error.URLError, OSError, IncompleteRead) as exc:
        category = "transient" if req.get_method() == "GET" else "unknown_submission"
        raise TripoError(f"{req.get_method()} interrupted; {category}.", category) from exc


def json_request(api_key: str, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(f"{BASE_URL}{path}", data=body, method=method)
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
            raise TripoError(f"Provider code {data.get('code')}; {category}.", category)
        if method == "GET" and path.startswith("/task/"):
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
type original_task_id texture_prompt out_format rig_type spec animation animations
animate_in_place no_bake_animation no_export_with_geometry format texture_size force_symmetry
flatten_bottom flatten_bottom_threshold style block_size model_task_id rig_retries
rig_model_version force_rig wait download out_dir interval timeout
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


def ensure_task(api_key: str, job: Checkpoint, name: str, payload: dict[str, Any] | Callable[[], dict[str, Any]]) -> str:
    stage = job.stage(name)
    if stage.get("task_id"):
        return stage["task_id"]
    if stage["state"] in {"submitting", "unknown_submission"}:
        raise TripoError(
            f"Stage {name!r} has an uncertain POST outcome. Find its task ID in Tripo, then "
            "use resume CHECKPOINT --task-id ID to reconcile it. No new task was submitted.",
            "unknown_submission",
        )
    built = payload() if callable(payload) else payload
    stage["request"] = {key: built[key] for key in ("type", "original_model_task_id") if key in built}
    stage["state"] = "submitting"
    stage.pop("last_error", None)
    job.save()

    def accepted(task_id: str) -> None:
        stage.update(task_id=task_id, state="submitted")
        job.save()

    try:
        return submit_task(api_key, built, on_accepted=accepted)
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
        raise TripoError(f"Image not found: {file_path}")
    if file_path.stat().st_size > 20 * 1024 * 1024:
        raise TripoError("Tripo upload limit is 20MB.")
    mime = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    ext = file_path.suffix.lower().lstrip(".")
    if ext == "jpg":
        ext = "jpeg"
    if ext not in {"png", "jpeg", "webp"}:
        raise TripoError("Direct image upload accepts png, jpeg/jpg, or webp.")

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
    req = request.Request(f"{BASE_URL}/upload/sts", data=body, method="POST")
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
    token = result.get("image_token") if isinstance(result, dict) else None
    if not isinstance(token, str) or not token:
        raise TripoError("Upload response did not include image_token; no generation task was submitted.", "transient")
    return token


def submit_task(api_key: str, payload: dict[str, Any], on_accepted: Callable[[str], None] | None = None) -> str:
    data = json_request(api_key, "POST", "/task", payload)
    result = data.get("data")
    task_id = result.get("task_id") if isinstance(result, dict) else None
    if not isinstance(task_id, str) or not task_id.strip() or "/" in task_id:
        raise TripoError("Task response did not include a valid task_id; submission outcome is unknown.", "unknown_submission")
    if on_accepted is not None:
        on_accepted(task_id)
    print(task_id)
    return task_id


def get_task(api_key: str, task_id: str) -> dict[str, Any]:
    task = json_request(api_key, "GET", f"/task/{parse.quote(task_id, safe='')}").get("data")
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


def download_outputs(task: dict[str, Any], out_dir: Path, *, job: Checkpoint | None = None, stage_name: str = "task") -> list[Path]:
    task_id = task["task_id"]
    output = task.get("output") or {}
    paths: list[Path] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{task_id}.json").write_text(json.dumps(task, indent=2), encoding="utf-8")
    urls = {key: output.get(key) for key in DOWNLOAD_KEYS}
    multiview = output.get("generate_multiview_image")
    if isinstance(multiview, dict):
        urls.update(multiview)
    records = job.stage(stage_name)["files"] if job is not None else {}
    for key, url in urls.items():
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            continue
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


def glb_node_names(path: Path) -> list[str]:
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
    return [node["name"] for node in nodes if node.get("name")]


def glb_bone_names(path: Path) -> list[str]:
    return [name for name in glb_node_names(path) if name.startswith("tripo::")]


LEGACY_BIPED_PAIRED_BONES = ("Clavicle", "Upperarm", "Forearm", "Hand", "Thigh", "Calf", "Foot")


def validate_rig_glb(path: Path, rig_type: str) -> tuple[str, list[str]]:
    """Validate either rig naming scheme. v2.x rigs use tripo::<row>_<side>_Limb_<n>
    chains; v1.0-20240301 rigs use an anatomical Mixamo-like skeleton (Hip, Spine01,
    L_Upperarm, R_Calf, twist bones, ...)."""
    names = glb_node_names(path)
    bones = [n for n in names if n.startswith("tripo::")]
    if bones:
        return f"{len(bones)} tripo:: bones: {', '.join(sorted(bones))}", validate_rig_bones(bones, rig_type)
    left = {n[2:] for n in names if n.startswith("L_")}
    right = {n[2:] for n in names if n.startswith("R_")}
    if not left and not right:
        return "no recognizable rig bones", ["no tripo:: or legacy L_/R_ bones found in rig GLB"]
    problems = []
    for part in LEGACY_BIPED_PAIRED_BONES:
        if part not in left or part not in right:
            problems.append(f"legacy rig missing L_/R_ {part}")
    if left != right:
        problems.append(f"legacy rig asymmetric bones: {sorted(left.symmetric_difference(right))}")
    if rig_type != "biped":
        problems.append(f"legacy anatomical skeleton is biped-only; requested rig_type {rig_type!r}")
    return f"legacy anatomical skeleton, {len(left)} paired L/R bones: {', '.join(sorted(left))}", problems


def validate_rig_bones(bones: list[str], rig_type: str) -> list[str]:
    """Return problems with a downloaded rig's skeleton. A passing prerigcheck does
    not guarantee a usable rig: degenerate rigs (e.g. spine plus one arm) do occur,
    and every later retarget inherits the damage."""
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
        # A knee-less leg or elbow-less arm warps every retargeted clip. Healthy
        # Tripo rigs are depth-symmetric (e.g. 5/5, 6/6, occasionally 6/5); broken
        # ones are 2/4, 9/4, or 4/1. Tolerate a 1-bone difference.
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
    parser.add_argument("--model-version", default="v3.1-20260211")
    parser.add_argument("--negative-prompt")
    parser.add_argument("--model-seed", type=int)
    parser.add_argument("--image-seed", type=int)
    parser.add_argument("--texture-seed", type=int)
    parser.add_argument("--texture-quality", choices=["standard", "detailed", "extreme"])
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
        "type": "text_to_model",
        "prompt": args.prompt,
        "model_version": args.model_version,
    }
    apply_common_model_args(args, payload)
    with job_context(args) as job:
        task_id = ensure_task(api_key, job, "task", payload)
        maybe_wait_and_download(api_key, task_id, args, job)


def cmd_image(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)

    def payload() -> dict[str, Any]:
        image = args.image
        if not image:
            raise TripoError("Remote image URLs are not saved. Resume with --image URL (or a local path).")
        if image.startswith(("http://", "https://")):
            file_obj = {"type": "image", "url": image}
        else:
            token = multipart_upload(api_key, Path(image))
            file_obj = {"type": "image", "file_token": token}
        built: dict[str, Any] = {"type": "image_to_model", "file": file_obj, "model_version": args.model_version}
        if args.enable_image_autofix:
            built["enable_image_autofix"] = True
        if args.texture_alignment:
            built["texture_alignment"] = args.texture_alignment
        if args.orientation:
            built["orientation"] = args.orientation
        apply_common_model_args(args, built)
        return built

    with job_context(args) as job:
        task_id = ensure_task(api_key, job, "task", payload)
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
        "convert_model": "conversion",
        "conversion": "conversion",
        "retarget": "animate_retarget",
        "rig": "animate_rig",
        "prerig": "animate_prerigcheck",
        "prerigcheck": "animate_prerigcheck",
        "lowpoly": "highpoly_to_lowpoly",
    }
    return aliases.get(value, value)


def cmd_postprocess(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    task_type = normalized_post_type(args.type)
    payload: dict[str, Any] = {
        "type": task_type,
        "original_model_task_id": args.original_task_id,
    }
    default_versions = {
        "texture_model": "v3.0-20250812",
        "highpoly_to_lowpoly": "P-v2.0-20251225",
    }
    if task_type == "animate_prerigcheck":
        # The prerigcheck request schema has no model_version parameter.
        if args.model_version:
            eprint("warning: animate_prerigcheck takes no model_version; ignoring it")
    elif args.model_version and args.model_version.lower() in {"default", "none"}:
        # Omit model_version and let the API choose (needed when retargeting v1.0 rigs:
        # the retarget enum rejects v1.0-20240301 as an explicit value).
        pass
    elif task_type in {"animate_rig", "animate_retarget"} and not args.model_version:
        # Route by body plan, same as character-pipeline: the v2.x rigger fails on
        # humanoids (0/16, see api-notes.md), so biped must use v1.0.
        rig_type = args.rig_type or "biped"
        if not args.rig_type:
            eprint(
                "note: no --rig-type given; assuming biped when choosing the rig model "
                "version (pass --rig-type or an explicit --model-version to override)"
            )
        resolved = resolve_rig_version(rig_type, None)
        if task_type == "animate_retarget" and resolved.startswith("v1.0"):
            # The retarget schema rejects explicit v1.0; omitting model_version selects
            # the legacy path (which forces FBX output and one animation per task below).
            eprint("note: v1.0-rig retarget: omitting model_version (API rejects explicit v1.0)")
        else:
            payload["model_version"] = resolved
            eprint(f"Using model_version={resolved} for rig_type={rig_type}")
    else:
        model_version = args.model_version or default_versions.get(task_type)
        if model_version:
            payload["model_version"] = model_version
    if task_type == "texture_model":
        if not args.texture_prompt:
            raise TripoError("--texture-prompt is required for texture_model")
        payload["texture_prompt"] = {"text": args.texture_prompt}
        if args.texture_quality:
            payload["texture_quality"] = args.texture_quality
    elif task_type == "animate_rig":
        if args.out_format:
            payload["out_format"] = args.out_format
        if args.rig_type:
            payload["rig_type"] = args.rig_type
        if args.spec:
            payload["spec"] = args.spec
    elif task_type == "animate_retarget":
        # original_model_task_id must be the RIG task ID for retarget.
        # v1.0 rigs (legacy humanoid path): the GLB animation bake is DEFECTIVE —
        # limb mesh is skinned to twist bones whose GLB transforms are exported in
        # the wrong space, collapsing arms into the torso (verified June 2026; the
        # FBX export of the same task is correct). Force FBX on this path.
        legacy_retarget = "model_version" not in payload
        if legacy_retarget and (args.out_format or "glb") != "fbx":
            if args.out_format == "glb":
                raise TripoError(
                    "v1.0-rig retargets must use --out-format fbx: Tripo's GLB bake corrupts "
                    "twist-bone transforms (limbs collapse into the torso). Load the FBX with "
                    "three.js FBXLoader, or convert FBX->GLB offline (Blender/FBX2glTF)."
                )
            eprint("note: v1.0-rig retarget defaults to out_format=fbx (GLB bake is broken for this path)")
            payload["out_format"] = "fbx"
        if legacy_retarget and args.animations:
            raise TripoError(
                "v1.0-rig retargets must request ONE animation per task: batching produces an FBX "
                "with one armature per clip (Armature.001, .002, ...) whose name-colliding bones "
                "bind to the wrong skeleton and pitch the body. Submit separate tasks with --animation."
            )
        if args.animations:
            animations = [item.strip() for item in args.animations.split(",") if item.strip()]
            validate_animations(animations, rig_model_version=payload.get("model_version"))
            if len(animations) > RETARGET_BATCH_LIMIT:
                raise TripoError(
                    f"animate_retarget accepts at most {RETARGET_BATCH_LIMIT} animations per task; "
                    f"got {len(animations)}. Split into multiple tasks."
                )
            payload["animations"] = animations
        elif args.animation:
            validate_animations([args.animation], rig_model_version=payload.get("model_version"))
            payload["animation"] = args.animation
        else:
            raise TripoError("--animation or --animations is required for animate_retarget")
        if args.out_format:
            payload["out_format"] = args.out_format
        if args.animate_in_place:
            eprint(
                "warning: animate_in_place is VERIFIED to corrupt retargeted clips "
                "(mirrored/crossed limbs on v1.0 rigs, exploded skinning on v2.5 rigs, June 2026). "
                "Prefer baked root motion and strip the root translation track in the engine."
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
        for key in ("face_limit", "texture_size", "flatten_bottom_threshold"):
            value = getattr(args, key)
            if value is not None:
                payload[key] = value
        if args.quad:
            payload["quad"] = True
        if args.force_symmetry:
            payload["force_symmetry"] = True
        if args.flatten_bottom:
            payload["flatten_bottom"] = True
    elif task_type == "highpoly_to_lowpoly":
        if args.face_limit:
            payload["face_limit"] = args.face_limit
    elif task_type == "stylize_model":
        if not args.style:
            raise TripoError("--style is required for stylize_model")
        payload["style"] = args.style
        if args.block_size:
            payload["block_size"] = args.block_size

    with job_context(args) as job:
        task_id = ensure_task(api_key, job, "task", payload)
        maybe_wait_and_download(api_key, task_id, args, job)


def resolve_rig_version(rig_type: str, override: str | None) -> str:
    """Measured June 2026: the v2.x limb-chain rigger fails on humanoids (0/16,
    asymmetric chains) while v1.0 produces a proper anatomical skeleton; v2.x is
    solid for creatures. Route by body plan unless explicitly overridden."""
    if override:
        return override
    return "v1.0-20240301" if rig_type == "biped" else RIG_MODEL_VERSION


def to_legacy_biped_presets(animations: list[str]) -> list[str]:
    """v1.0 rigs use the preset:biped:* library; map plain v2.5-style names onto it
    so callers can say preset:idle regardless of which rig path gets chosen."""
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
    if animations and args.spec == "mixamo":
        raise TripoError(
            "spec=mixamo rigs cannot be used with Tripo animate_retarget. "
            "Use --animations '' and retarget external clips (e.g. Mixamo) onto the rig yourself, "
            "or keep --spec tripo for Tripo preset animations."
        )
    # Loose catalog check now (both namespaces allowed); strict per-rig-type
    # validation happens after prerigcheck, before rig credits are spent.
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
        # The T-pose suffix is biped-specific; creature prompts need their own stance language.
        if (args.rig_type in (None, "biped")
                and "t-pose" not in prompt.lower() and "a-pose" not in prompt.lower()):
            prompt = (
                f"{prompt}, full-body T-pose for rigging, arms straight out to the sides, "
                "legs apart and visible, front facing, symmetric, no props attached to the body"
            )
        text_payload: dict[str, Any] = {
            "type": "text_to_model",
            "prompt": prompt,
            "model_version": args.model_version,
            "texture_quality": args.texture_quality,
            "geometry_quality": args.geometry_quality,
            "pbr": True,
        }
        if args.face_limit:
            text_payload["face_limit"] = args.face_limit
        model_task_id = ensure_task(api_key, job, "model", text_payload)
    model_task, _model_paths = finish_stage(api_key, job, "model", args, out_dir / "base")
    require_success(model_task)
    eprint("Check the downloaded rendered_image: the character must be in a clear T/A-pose before rigging.")
    if args.stop_after == "model":
        eprint(f"Stopped after model {model_task_id}. Inspect the downloads. " + (
            "Resume the checkpoint to continue rigging." if job.path else
            f"Continue with character-pipeline --model-task-id {model_task_id}."
        ))
        return

    ensure_task(api_key, job, "prerigcheck", {
        "type": "animate_prerigcheck",
        "original_model_task_id": model_task_id,
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
                "Tripo docs note a false result is not always final; pass --force-rig to attempt anyway."
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
    eprint(f"Using rig_type={rig_type} rig_model_version={rig_model_version}"
           + (f" animations={','.join(animations)}" if animations else ""))
    validate_animations(animations, rig_type if not legacy else None, rig_model_version)

    # Auto-rigging is nondeterministic: the same model can produce a degenerate
    # skeleton on one attempt and a healthy one on the next. Retry before giving up.
    attempts = 1 + max(0, args.rig_retries)
    rig_id = None
    last_detail = "no rig attempt succeeded"
    last_usable_rig = None
    selected_rig_stage = job.data.get("rig_stage")
    stage_names = [f"rig-{attempt}" for attempt in range(1, attempts + 1)]
    if selected_rig_stage is not None and selected_rig_stage not in stage_names:
        raise TripoError("Checkpoint selected rig is outside the saved retry budget.", "checkpoint_error")
    # Once a rig is selected, its accepted task is the stable parent of every
    # animation. Old failed retries must not prevent resuming the chosen rig.
    attempt_numbers = [stage_names.index(selected_rig_stage) + 1] if selected_rig_stage else range(1, attempts + 1)
    for attempt in attempt_numbers:
        stage_name = f"rig-{attempt}"
        candidate_id = ensure_task(api_key, job, stage_name, {
            "type": "animate_rig",
            "original_model_task_id": model_task_id,
            "model_version": rig_model_version,
            "rig_type": rig_type,
            "spec": args.spec,
            "out_format": "glb",
        })
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
            f"Use postprocess --type retarget --original-task-id {rig_id} with the appropriate rig version and clips."
        ))
        return

    # Retarget references the RIG task ID. v2.5 rigs batch up to 5 presets per
    # task; v1.0 rigs must take ONE per task (batched FBX exports one armature
    # per clip whose name-colliding bones cross-bind and pitch the body).
    batch_size = 1 if legacy else RETARGET_BATCH_LIMIT
    for start in range(0, len(animations), batch_size):
        batch = animations[start:start + batch_size]
        # v1.0 GLB animation bake is defective (twist-bone space bug collapses limbs);
        # the FBX export of the same task is correct. See api-notes.md.
        retarget_payload: dict[str, Any] = {
            "type": "animate_retarget",
            "original_model_task_id": rig_id,
            "animations": batch,
            "out_format": "fbx" if legacy else "glb",
        }
        if not legacy:
            retarget_payload["model_version"] = rig_model_version
        if args.animate_in_place:
            eprint(
                "warning: animate_in_place is VERIFIED to corrupt retargeted clips "
                "(mirrored/crossed limbs on v1.0 rigs, exploded skinning on v2.5 rigs, June 2026). "
                "Prefer baked root motion and strip the root translation track in the engine."
            )
            retarget_payload["animate_in_place"] = True
        stage_name = f"animation-{start // batch_size + 1}"
        ensure_task(api_key, job, stage_name, retarget_payload)
        batch_name = safe_name("-".join(item.split(":")[-1] for item in batch))
        anim_task, _anim_paths = finish_stage(api_key, job, stage_name, args, out_dir / batch_name)
        require_success(anim_task)
    eprint("Inspect gltf.animations clip names/counts in each download before wiring the AnimationMixer.")


def cmd_resume(args: argparse.Namespace) -> None:
    """Resume a single accepted job or its original character chain.

    Single jobs always wait and download on resume; they never grow into a rigging
    pipeline. A character checkpoint continues through animations by default,
    independently of the previous invocation's --stop-after limit.
    """
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
            for key in ("type", "original_model_task_id"):
                if key in expected and key in task and task[key] != expected[key]:
                    raise TripoError(f"Reconciled task {key} does not match the saved submission intent.")
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
        "postprocess": ["postprocess", "--type", "rig", "--original-task-id", "checkpoint-task"],
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
        elif key == "flatten_bottom_threshold":
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
            if "original_model_task_id" in intent and not isinstance(intent["original_model_task_id"], str):
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
    """Keyframe-level QA for retargeted clips. Returns (report_lines, problems).
    Warp signatures: scale tracks, or translation tracks on non-root bones that
    deviate far from the bone's rest offset (limb stretching)."""
    import math
    gltf, bin_chunk = load_glb(path)
    nodes = gltf.get("nodes", [])
    roots = {"Armature", "Root", "Hip", "Pelvis", "tripo::Root"}
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
    """Print the SET|MISSING credential contract line used by skip rules and audits."""
    status = "SET" if os.environ.get("TRIPO_API_KEY") else "MISSING"
    print(f"TRIPO_API_KEY={status}")


def add_shared_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-key")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--out-dir", default="tripo-output")
    parser.add_argument("--interval", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--checkpoint", metavar="PATH", help="create a resumable job journal; existing paths require resume")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tripo OpenAPI 3D asset helper")
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe", help="print TRIPO_API_KEY=SET|MISSING")
    probe.set_defaults(func=cmd_probe)

    text = sub.add_parser("text", help="submit text_to_model")
    text.add_argument("--prompt", required=True)
    add_common_model_args(text)
    add_shared_runtime_args(text)
    text.set_defaults(func=cmd_text)

    image = sub.add_parser("image", help="submit image_to_model from local path or URL")
    image.add_argument("--image", required=True)
    image.add_argument("--enable-image-autofix", action="store_true")
    image.add_argument("--texture-alignment", choices=["original_image", "geometry"])
    image.add_argument("--orientation", choices=["default", "align_image"])
    add_common_model_args(image)
    add_shared_runtime_args(image)
    image.set_defaults(func=cmd_image)

    status = sub.add_parser("status", help="get task status")
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

    post = sub.add_parser("postprocess", help="submit Tripo postprocess task")
    post.add_argument("--type", required=True)
    post.add_argument("--original-task-id", required=True)
    post.add_argument("--model-version")
    post.add_argument("--texture-prompt")
    post.add_argument("--texture-quality", choices=["standard", "detailed", "extreme"])
    post.add_argument("--out-format", choices=["glb", "fbx"])
    post.add_argument("--rig-type", choices=["biped", "quadruped", "hexapod", "octopod", "avian", "serpentine", "aquatic"])
    post.add_argument("--spec", choices=["tripo", "mixamo"])
    post.add_argument("--animation")
    post.add_argument("--animations")
    post.add_argument("--animate-in-place", action="store_true")
    post.add_argument("--no-bake-animation", action="store_true")
    post.add_argument("--no-export-with-geometry", action="store_true")
    post.add_argument("--format", choices=["GLTF", "USDZ", "FBX", "OBJ", "STL", "3MF"])
    post.add_argument("--face-limit", type=int)
    post.add_argument("--texture-size", type=int)
    post.add_argument("--quad", action="store_true")
    post.add_argument("--force-symmetry", action="store_true")
    post.add_argument("--flatten-bottom", action="store_true")
    post.add_argument("--flatten-bottom-threshold", type=float)
    post.add_argument("--style", choices=["lego", "voxel", "voronoi", "minecraft"])
    post.add_argument("--block-size", type=int)
    add_shared_runtime_args(post)
    post.set_defaults(func=cmd_postprocess)

    validate = sub.add_parser("validate-rig", help="check a downloaded rig GLB for degenerate auto-rig skeletons")
    validate.add_argument("glb_path")
    validate.add_argument("--rig-type", default="biped", choices=["biped", "quadruped", "hexapod", "octopod", "avian", "serpentine", "aquatic"])
    validate.set_defaults(func=cmd_validate_rig)

    validate_anim = sub.add_parser("validate-animation", help="keyframe-level QA for retargeted clip GLBs (warp signatures)")
    validate_anim.add_argument("glb_path")
    validate_anim.set_defaults(func=cmd_validate_animation)

    pipeline = sub.add_parser("character-pipeline", help="generate, prereig-check, rig, animate, and download a character")
    pipeline.add_argument("--prompt")
    pipeline.add_argument("--model-task-id",
                          help="reuse an existing generation task instead of generating (skips --prompt)")
    pipeline.add_argument("--rig-retries", type=int, default=2,
                          help="extra rig attempts when validation fails; rigging is nondeterministic (default 2)")
    pipeline.add_argument("--rig-model-version", default=None,
                          help="rig model version override. Default: auto by rig type — "
                               "biped -> v1.0-20240301 (anatomical skeleton, FBX clips; the v2.x "
                               "biped rigger and GLB bake are broken), creatures -> v2.5-20260210 (GLB)")
    pipeline.add_argument("--animations", default="preset:idle,preset:walk,preset:run")
    pipeline.add_argument("--model-version", default="v3.1-20260211")
    pipeline.add_argument("--texture-quality", default="detailed", choices=["standard", "detailed", "extreme"])
    pipeline.add_argument("--geometry-quality", default="standard", choices=["standard", "detailed"])
    pipeline.add_argument("--face-limit", type=int)
    pipeline.add_argument(
        "--rig-type",
        choices=["biped", "quadruped", "hexapod", "octopod", "avian", "serpentine", "aquatic"],
        help="override the prerigcheck-detected rig type (default: auto-detect, fallback biped)",
    )
    pipeline.add_argument("--spec", default="tripo", choices=["tripo", "mixamo"],
                          help="mixamo rigs cannot use Tripo preset retargeting")
    pipeline.add_argument("--force-rig", action="store_true",
                          help="attempt rigging even if prerigcheck reports riggable=false")
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
