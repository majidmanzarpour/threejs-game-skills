#!/usr/bin/env python3
"""Atlas Cloud text/image-to-3D client for skill-driven game assets."""

from __future__ import annotations

import argparse
import ipaddress
import json
import mimetypes
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, parse, request

DEFAULT_API_BASE = "https://api.atlascloud.ai"
DEFAULT_TEXT_MODEL = "tencent/hunyuan3d-rapid/text-to-3d"
DEFAULT_IMAGE_MODEL = "tencent/hunyuan3d-rapid/image-to-3d"
SUCCESS_STATUSES = {"completed", "succeeded", "success"}
FAILURE_STATUSES = {"failed", "cancelled", "canceled", "expired"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 1024 * 1024 * 1024
USER_AGENT = (
    "threejs-game-skills/0.1 (+https://github.com/majidmanzarpour/threejs-game-skills)"
)


class AtlasError(RuntimeError):
    """Raised when an Atlas request or downloaded artifact is invalid."""


@dataclass(frozen=True)
class ModelContract:
    """Runtime paths and input schema fetched from the live Atlas catalog."""

    model: str
    submit_path: str
    poll_path: str
    properties: dict[str, Any]
    required: set[str]


def eprint(*parts: object) -> None:
    print(*parts, file=sys.stderr)


def is_loopback(hostname: str | None) -> bool:
    if hostname in {"localhost", "localhost.localdomain"}:
        return True
    try:
        return ipaddress.ip_address(hostname or "").is_loopback
    except ValueError:
        return False


def validate_url(url: str, *, allow_loopback_http: bool = False) -> str:
    parsed = parse.urlparse(url)
    if parsed.username or parsed.password or not parsed.hostname:
        raise AtlasError(f"Unsafe URL: {url}")
    if parsed.scheme == "https":
        return url
    if allow_loopback_http and parsed.scheme == "http" and is_loopback(parsed.hostname):
        return url
    raise AtlasError(f"URL must use HTTPS: {url}")


def open_request(req: request.Request, *, timeout: int):
    """Open loopback test traffic directly while preserving normal proxy settings."""
    hostname = parse.urlparse(req.full_url).hostname
    if is_loopback(hostname):
        return request.build_opener(request.ProxyHandler({})).open(req, timeout=timeout)
    return request.urlopen(req, timeout=timeout)


def api_base_from(args: argparse.Namespace) -> str:
    raw = (
        args.api_base or os.environ.get("ATLASCLOUD_MEDIA_API_BASE") or DEFAULT_API_BASE
    )
    return validate_url(raw.rstrip("/"), allow_loopback_http=True)


def api_key_from(args: argparse.Namespace) -> str:
    key = args.api_key or os.environ.get("ATLASCLOUD_API_KEY")
    if not key:
        raise AtlasError("Missing API key. Set ATLASCLOUD_API_KEY or pass --api-key.")
    return key


def decode_json(raw: bytes, context: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AtlasError(f"{context} returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise AtlasError(f"{context} returned a non-object JSON response")
    return value


def unwrap_response(value: dict[str, Any], context: str) -> Any:
    code = value.get("code")
    if code not in {None, 0, 200, "0", "200"}:
        message = value.get("message") or value.get("msg") or value
        raise AtlasError(f"{context} failed: {message}")
    return value.get("data", value)


def http_json(
    url: str,
    *,
    method: str = "GET",
    api_key: str | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(
        validate_url(url, allow_loopback_http=True), data=body, method=method
    )
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", USER_AGENT)
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with open_request(req, timeout=timeout) as response:
            return decode_json(response.read(), url)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AtlasError(f"HTTP {exc.code} for {url}: {detail}") from exc
    except error.URLError as exc:
        raise AtlasError(f"Request failed for {url}: {exc.reason}") from exc


def fetch_catalog(api_base: str) -> list[dict[str, Any]]:
    value = unwrap_response(http_json(f"{api_base}/api/v1/models"), "model catalog")
    if not isinstance(value, list):
        raise AtlasError("Model catalog did not contain a list")
    return [item for item in value if isinstance(item, dict)]


def input_schema_from(document: dict[str, Any]) -> dict[str, Any]:
    schemas = document.get("components", {}).get("schemas", {})
    value = schemas.get("Input")
    if not isinstance(value, dict):
        raise AtlasError("Model schema did not define components.schemas.Input")
    return value


def contract_for(api_base: str, model: str) -> ModelContract:
    entry = next(
        (
            item
            for item in fetch_catalog(api_base)
            if (item.get("id") or item.get("model")) == model
        ),
        None,
    )
    if entry is None:
        raise AtlasError(f"Model is not present in the live Atlas catalog: {model}")
    if entry.get("type") != "Image" or "3d" not in model.lower():
        raise AtlasError(f"Model is not an Atlas Image-type 3D model: {model}")
    schema_url = entry.get("input_schema") or entry.get("schema")
    if not isinstance(schema_url, str):
        raise AtlasError(f"Model does not publish an input schema: {model}")
    document = http_json(schema_url)
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise AtlasError("Model schema did not define API paths")
    submit_path = next(
        (
            path
            for path, methods in paths.items()
            if isinstance(methods, dict) and "post" in methods
        ),
        None,
    )
    poll_path = next(
        (
            path
            for path, methods in paths.items()
            if isinstance(methods, dict)
            and "get" in methods
            and ("{request_id}" in path or "{id}" in path)
        ),
        None,
    )
    if not submit_path or not poll_path:
        raise AtlasError("Model schema did not define submit and result paths")
    input_schema = input_schema_from(document)
    properties = input_schema.get("properties") or {}
    required = input_schema.get("required") or []
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise AtlasError("Model input schema has invalid properties or required fields")
    return ModelContract(model, submit_path, poll_path, properties, set(required))


def parse_extra_params(values: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for raw in values:
        name, separator, encoded = raw.partition("=")
        if not separator or not name:
            raise AtlasError(f"--param must use NAME=JSON: {raw}")
        if name in {"model", "prompt", "image", "image_url"}:
            raise AtlasError(
                f"Use the dedicated CLI option instead of --param for {name}"
            )
        if name not in properties:
            raise AtlasError(
                f"Parameter is not supported by the selected model: {name}"
            )
        try:
            value = json.loads(encoded)
        except json.JSONDecodeError as exc:
            raise AtlasError(f"Invalid JSON value for {name}: {encoded}") from exc
        schema = properties[name]
        enum = schema.get("enum") if isinstance(schema, dict) else None
        if isinstance(enum, list) and value not in enum:
            raise AtlasError(f"{name} must be one of: {', '.join(map(str, enum))}")
        result[name] = value
    return result


def add_supported(
    payload: dict[str, Any], properties: dict[str, Any], name: str, value: Any
) -> None:
    if value is not None:
        if name not in properties:
            raise AtlasError(
                f"Parameter is not supported by the selected model: {name}"
            )
        payload[name] = value


def upload_image(api_base: str, api_key: str, image_path: Path) -> str:
    if not image_path.is_file():
        raise AtlasError(f"Image not found: {image_path}")
    size = image_path.stat().st_size
    if size > MAX_UPLOAD_BYTES:
        raise AtlasError(
            f"Image exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB upload limit"
        )
    mime = mimetypes.guess_type(image_path.name)[0]
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise AtlasError("Local image must be JPEG, PNG, or WebP")
    boundary = f"atlas-{uuid.uuid4().hex}"
    content = image_path.read_bytes()
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="file"; filename="{image_path.name}"\r\n'
                f"Content-Type: {mime}\r\n\r\n"
            ).encode(),
            content,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    url = f"{api_base}/api/v1/model/uploadMedia"
    req = request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("User-Agent", USER_AGENT)
    try:
        with open_request(req, timeout=120) as response:
            value = unwrap_response(decode_json(response.read(), url), "media upload")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AtlasError(f"Upload failed with HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise AtlasError(f"Upload failed: {exc.reason}") from exc
    if not isinstance(value, dict):
        raise AtlasError("Upload response did not contain an object")
    uploaded = value.get("download_url") or value.get("url")
    if not isinstance(uploaded, str):
        raise AtlasError("Upload response did not contain a download URL")
    return validate_url(uploaded, allow_loopback_http=True)


def image_value(api_base: str, api_key: str, raw: str) -> str:
    if raw.startswith("data:image/"):
        return raw
    if parse.urlparse(raw).scheme:
        return validate_url(raw, allow_loopback_http=True)
    return upload_image(api_base, api_key, Path(raw))


def payload_for(
    args: argparse.Namespace, contract: ModelContract, api_base: str, api_key: str
) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": contract.model}
    if args.command == "text":
        payload["prompt"] = args.prompt
    else:
        field = "image_url" if "image_url" in contract.properties else "image"
        if field not in contract.properties:
            raise AtlasError(
                f"Selected model does not accept image input: {contract.model}"
            )
        value = image_value(api_base, api_key, args.image)
        if field == "image_url" and value.startswith("data:"):
            raise AtlasError(f"Selected model requires an image URL: {contract.model}")
        payload[field] = value
    pbr_name = "enable_pbr" if "enable_pbr" in contract.properties else "pbr"
    add_supported(payload, contract.properties, pbr_name, args.pbr)
    add_supported(payload, contract.properties, "enable_geometry", args.enable_geometry)
    add_supported(payload, contract.properties, "format", args.format)
    add_supported(payload, contract.properties, "face_limit", args.face_limit)
    add_supported(payload, contract.properties, "texture_quality", args.texture_quality)
    add_supported(
        payload, contract.properties, "geometry_quality", args.geometry_quality
    )
    add_supported(payload, contract.properties, "quad", args.quad)
    payload.update(parse_extra_params(args.param, contract.properties))
    missing = sorted(name for name in contract.required if name not in payload)
    if missing:
        raise AtlasError(f"Missing required model inputs: {', '.join(missing)}")
    return payload


def prediction_id_from(value: Any) -> str:
    if not isinstance(value, dict):
        raise AtlasError("Submission response did not contain an object")
    prediction_id = (
        value.get("id") or value.get("request_id") or value.get("prediction_id")
    )
    if not isinstance(prediction_id, str) or not prediction_id:
        raise AtlasError("Submission response did not contain a prediction ID")
    return prediction_id


def resolved_poll_path(template: str, prediction_id: str) -> str:
    encoded = parse.quote(prediction_id, safe="")
    return template.replace("{request_id}", encoded).replace("{id}", encoded)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def submit(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    api_base = api_base_from(args)
    api_key = api_key_from(args)
    model = args.model or (
        DEFAULT_TEXT_MODEL if args.command == "text" else DEFAULT_IMAGE_MODEL
    )
    contract = contract_for(api_base, model)
    payload = payload_for(args, contract, api_base, api_key)
    value = unwrap_response(
        http_json(
            f"{api_base}{contract.submit_path}",
            method="POST",
            api_key=api_key,
            payload=payload,
            timeout=120,
        ),
        "generation submission",
    )
    prediction_id = prediction_id_from(value)
    job = {
        "api_base": api_base,
        "model": model,
        "prediction_id": prediction_id,
        "poll_path": contract.poll_path,
    }
    out_dir = Path(args.out_dir)
    job_path = out_dir / "job.json"
    write_json(job_path, job)
    print(prediction_id)
    eprint(f"Saved resumable job: {job_path}")
    return job, api_key


def poll_once(job: dict[str, Any], api_key: str) -> dict[str, Any]:
    api_base = validate_url(str(job["api_base"]), allow_loopback_http=True)
    poll_path = resolved_poll_path(str(job["poll_path"]), str(job["prediction_id"]))
    value = unwrap_response(
        http_json(f"{api_base}{poll_path}", api_key=api_key), "generation result"
    )
    if not isinstance(value, dict):
        raise AtlasError("Generation result did not contain an object")
    return value


def wait_for_result(
    job: dict[str, Any], api_key: str, interval: float, timeout: float
) -> dict[str, Any]:
    started = time.monotonic()
    while True:
        value = poll_once(job, api_key)
        status = str(value.get("status", "unknown")).lower()
        eprint(f"{job['prediction_id']}: {status}")
        if status in SUCCESS_STATUSES:
            return value
        if status in FAILURE_STATUSES:
            detail = value.get("error") or value.get("message") or status
            raise AtlasError(f"Generation ended as {status}: {detail}")
        if time.monotonic() - started >= timeout:
            raise AtlasError(
                f"Timed out waiting for {job['prediction_id']}; resume with: "
                "atlas_3d_asset.py resume --job <out-dir>/job.json --wait"
            )
        time.sleep(interval)


def safe_filename(raw: str, fallback: str) -> str:
    name = Path(parse.unquote(raw)).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return name or fallback


def output_entries(result: dict[str, Any]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for index, item in enumerate(result.get("files") or []):
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            continue
        filename = (
            item.get("file_name")
            or f"model-{index}.{str(item.get('type') or 'bin').lower()}"
        )
        entries.append(
            (item["url"], safe_filename(str(filename), f"model-{index}.bin"))
        )
    if entries:
        return entries
    for index, url in enumerate(result.get("outputs") or []):
        if isinstance(url, str):
            suffix = Path(parse.urlparse(url).path).suffix or ".bin"
            entries.append((url, f"model-{index}{suffix}"))
    return entries


def validate_glb(path: Path) -> None:
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"glTF":
        raise AtlasError(f"Downloaded file is not a GLB: {path}")
    declared_length = int.from_bytes(data[8:12], "little")
    if declared_length != len(data):
        raise AtlasError(
            f"GLB length mismatch for {path}: header={declared_length}, actual={len(data)}"
        )


def download_file(url: str, destination: Path) -> None:
    req = request.Request(validate_url(url, allow_loopback_http=True), method="GET")
    req.add_header("User-Agent", USER_AGENT)
    try:
        with (
            open_request(req, timeout=300) as response,
            destination.open("wb") as handle,
        ):
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise AtlasError(
                        f"Download exceeds {MAX_DOWNLOAD_BYTES} bytes: {url}"
                    )
                handle.write(chunk)
    except error.HTTPError as exc:
        raise AtlasError(f"Download failed with HTTP {exc.code}: {url}") from exc
    except error.URLError as exc:
        raise AtlasError(f"Download failed: {exc.reason}") from exc


def download_outputs(result: dict[str, Any], out_dir: Path) -> list[Path]:
    entries = output_entries(result)
    if not entries:
        raise AtlasError("Completed result did not contain downloadable files")
    output_dir = out_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for url, filename in entries:
        path = output_dir / safe_filename(filename, "model.bin")
        download_file(url, path)
        if path.suffix.lower() == ".glb":
            validate_glb(path)
        print(path)
        paths.append(path)
    return paths


def complete_job(
    job: dict[str, Any], api_key: str, args: argparse.Namespace
) -> dict[str, Any]:
    result = (
        wait_for_result(job, api_key, args.interval, args.timeout)
        if args.wait
        else poll_once(job, api_key)
    )
    out_dir = Path(args.out_dir)
    write_json(out_dir / "result.json", result)
    if args.download:
        status = str(result.get("status", "")).lower()
        if status not in SUCCESS_STATUSES:
            raise AtlasError(
                f"Cannot download while task status is {status or 'unknown'}"
            )
        download_outputs(result, out_dir)
    return result


def cmd_generate(args: argparse.Namespace) -> None:
    job, api_key = submit(args)
    if args.wait or args.download:
        complete_job(job, api_key, args)


def cmd_resume(args: argparse.Namespace) -> None:
    job_path = Path(args.job)
    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AtlasError(f"Cannot read job file: {job_path}") from exc
    if not isinstance(job, dict) or not {
        "api_base",
        "model",
        "prediction_id",
        "poll_path",
    }.issubset(job):
        raise AtlasError(f"Invalid job file: {job_path}")
    if args.out_dir is None:
        args.out_dir = str(job_path.parent)
    complete_job(job, api_key_from(args), args)


def cmd_models(args: argparse.Namespace) -> None:
    models = []
    for item in fetch_catalog(api_base_from(args)):
        model = item.get("id") or item.get("model")
        if (
            item.get("type") == "Image"
            and isinstance(model, str)
            and "3d" in model.lower()
        ):
            models.append(
                {
                    "id": model,
                    "pricing": item.get("pricing") or item.get("price"),
                    "input_schema": item.get("input_schema") or item.get("schema"),
                }
            )
    print(json.dumps(models, indent=2))


def cmd_probe(_: argparse.Namespace) -> None:
    status = "SET" if os.environ.get("ATLASCLOUD_API_KEY") else "MISSING"
    print(f"ATLASCLOUD_API_KEY={status}")


def add_generation_args(parser: argparse.ArgumentParser, default_out_dir: str) -> None:
    parser.add_argument("--model")
    parser.add_argument("--pbr", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument(
        "--enable-geometry", action=argparse.BooleanOptionalAction, default=None
    )
    parser.add_argument("--format", choices=["GLB", "OBJ", "USDZ", "FBX", "STL", "MP4"])
    parser.add_argument("--face-limit", type=int)
    parser.add_argument("--texture-quality", choices=["standard", "detailed"])
    parser.add_argument("--geometry-quality", choices=["standard", "detailed"])
    parser.add_argument("--quad", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--param", action="append", default=[], metavar="NAME=JSON")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--out-dir", default=default_out_dir)
    parser.add_argument("--interval", type=float, default=5)
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--api-key")
    parser.add_argument("--api-base")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Atlas Cloud 3D asset helper")
    sub = parser.add_subparsers(dest="command", required=True)
    probe = sub.add_parser("probe", help="print ATLASCLOUD_API_KEY=SET|MISSING")
    probe.set_defaults(func=cmd_probe)
    models = sub.add_parser("models", help="list live Atlas Image-type 3D models")
    models.add_argument("--api-base")
    models.set_defaults(func=cmd_models)
    text = sub.add_parser("text", help="submit Atlas text-to-3D generation")
    text.add_argument("--prompt", required=True)
    add_generation_args(text, "atlas-3d-output")
    text.set_defaults(func=cmd_generate)
    image = sub.add_parser("image", help="submit Atlas image-to-3D generation")
    image.add_argument("--image", required=True)
    add_generation_args(image, "atlas-3d-output")
    image.set_defaults(func=cmd_generate)
    resume = sub.add_parser(
        "resume", help="poll an existing job without another billable POST"
    )
    resume.add_argument("--job", required=True)
    resume.add_argument("--wait", action="store_true")
    resume.add_argument("--download", action="store_true")
    resume.add_argument("--out-dir")
    resume.add_argument("--interval", type=float, default=5)
    resume.add_argument("--timeout", type=float, default=900)
    resume.add_argument("--api-key")
    resume.set_defaults(func=cmd_resume)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except AtlasError as exc:
        eprint(f"atlas_3d_asset.py: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
