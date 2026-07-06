#!/usr/bin/env python3
"""Small Tripo OpenAPI client for skill-driven 3D asset generation."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
from pathlib import Path
import sys
import time
from typing import Any
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
    pass


def eprint(*parts: object) -> None:
    print(*parts, file=sys.stderr)


def api_key_from(args: argparse.Namespace) -> str:
    key = args.api_key or os.environ.get("TRIPO_API_KEY")
    if not key:
        raise TripoError("Missing API key. Set TRIPO_API_KEY or pass --api-key.")
    return key


def json_request(api_key: str, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise TripoError(f"HTTP {exc.code} {exc.reason}: {raw}") from exc
    except error.URLError as exc:
        raise TripoError(f"Request failed: {exc.reason}") from exc
    data = json.loads(raw)
    if data.get("code") != 0:
        raise TripoError(json.dumps(data, indent=2))
    return data


def multipart_upload(api_key: str, file_path: Path) -> str:
    if not file_path.exists():
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
    try:
        with request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise TripoError(f"Upload failed: HTTP {exc.code} {exc.reason}: {raw}") from exc
    data = json.loads(raw)
    if data.get("code") != 0:
        raise TripoError(json.dumps(data, indent=2))
    token = data.get("data", {}).get("image_token")
    if not token:
        raise TripoError(f"Upload response did not include image_token: {raw}")
    return token


def submit_task(api_key: str, payload: dict[str, Any]) -> str:
    data = json_request(api_key, "POST", "/task", payload)
    task_id = data.get("data", {}).get("task_id")
    if not task_id:
        raise TripoError(f"Task response did not include task_id: {data}")
    print(task_id)
    return task_id


def get_task(api_key: str, task_id: str) -> dict[str, Any]:
    return json_request(api_key, "GET", f"/task/{task_id}")["data"]


def wait_for_task(api_key: str, task_id: str, interval: int, timeout: int) -> dict[str, Any]:
    start = time.monotonic()
    while True:
        data = get_task(api_key, task_id)
        status = data.get("status", "unknown")
        progress = data.get("progress", 0)
        eprint(f"{task_id}: {status} {progress}%")
        if status in FINAL_STATUSES:
            return data
        if time.monotonic() - start > timeout:
            raise TripoError(f"Timed out waiting for task {task_id}")
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
    with request.urlopen(req, timeout=300) as resp:
        content = resp.read()
        content_type = resp.headers.get("Content-Type")
    ext = extension_for(key, url, content_type)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{filename_base}-{key}{ext}"
    path.write_bytes(content)
    return path


def download_outputs(task: dict[str, Any], out_dir: Path) -> list[Path]:
    task_id = task["task_id"]
    output = task.get("output") or {}
    paths: list[Path] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{task_id}.json").write_text(json.dumps(task, indent=2), encoding="utf-8")
    for key in DOWNLOAD_KEYS:
        url = output.get(key)
        if isinstance(url, str) and url.startswith("http"):
            path = download_url(url, out_dir, task_id, key)
            paths.append(path)
            print(path)
    multiview = output.get("generate_multiview_image")
    if isinstance(multiview, dict):
        for key, url in multiview.items():
            if isinstance(url, str) and url.startswith("http"):
                path = download_url(url, out_dir, task_id, key)
                paths.append(path)
                print(path)
    if not paths:
        eprint("No downloadable output URLs found.")
    return paths


def glb_node_names(path: Path) -> list[str]:
    import struct
    with path.open("rb") as handle:
        header = handle.read(12)
        if len(header) < 12 or header[:4] != b"glTF":
            raise TripoError(f"Not a GLB file: {path}")
        chunk_len, _chunk_type = struct.unpack("<II", handle.read(8))
        gltf = json.loads(handle.read(chunk_len))
    return [node.get("name", "") for node in gltf.get("nodes", []) if node.get("name")]


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


def maybe_wait_and_download(api_key: str, task_id: str, args: argparse.Namespace) -> dict[str, Any] | None:
    if not args.wait:
        return None
    task = wait_for_task(api_key, task_id, args.interval, args.timeout)
    print(json.dumps(task, indent=2))
    if task.get("status") != "success":
        raise TripoError(f"Task {task_id} ended as {task.get('status')}")
    if args.download:
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
    task_id = submit_task(api_key, payload)
    maybe_wait_and_download(api_key, task_id, args)


def cmd_image(args: argparse.Namespace) -> None:
    api_key = api_key_from(args)
    image = args.image
    if image.startswith(("http://", "https://")):
        file_obj = {"type": "image", "url": image}
    else:
        token = multipart_upload(api_key, Path(image))
        file_obj = {"type": "image", "file_token": token}
    payload: dict[str, Any] = {
        "type": "image_to_model",
        "file": file_obj,
        "model_version": args.model_version,
    }
    if args.enable_image_autofix:
        payload["enable_image_autofix"] = True
    if args.texture_alignment:
        payload["texture_alignment"] = args.texture_alignment
    if args.orientation:
        payload["orientation"] = args.orientation
    apply_common_model_args(args, payload)
    task_id = submit_task(api_key, payload)
    maybe_wait_and_download(api_key, task_id, args)


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

    task_id = submit_task(api_key, payload)
    maybe_wait_and_download(api_key, task_id, args)


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

    out_dir = Path(args.out_dir)
    if args.model_task_id:
        model_task_id = args.model_task_id
        eprint(f"Skipping generation; reusing model task {model_task_id}")
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
        model_task_id = submit_task(api_key, text_payload)
        model_task = wait_for_task(api_key, model_task_id, args.interval, args.timeout)
        if model_task.get("status") != "success":
            raise TripoError(f"Model task failed: {model_task.get('status')}")
        download_outputs(model_task, out_dir / "base")
        eprint("Check the downloaded rendered_image: the character must be in a clear T/A-pose before rigging.")

    check_id = submit_task(api_key, {
        "type": "animate_prerigcheck",
        "original_model_task_id": model_task_id,
    })
    check_task = wait_for_task(api_key, check_id, args.interval, args.timeout)
    print(json.dumps(check_task, indent=2))
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
    for attempt in range(1, attempts + 1):
        candidate_id = submit_task(api_key, {
            "type": "animate_rig",
            "original_model_task_id": model_task_id,
            "model_version": rig_model_version,
            "rig_type": rig_type,
            "spec": args.spec,
            "out_format": "glb",
        })
        rig_task = wait_for_task(api_key, candidate_id, args.interval, args.timeout)
        if rig_task.get("status") != "success":
            last_detail = f"rig task ended as {rig_task.get('status')} (error_code={rig_task.get('error_code')})"
            eprint(f"rig attempt {attempt}/{attempts}: {last_detail}")
            continue
        suffix = "rig" if attempt == 1 else f"rig-attempt{attempt}"
        rig_paths = download_outputs(rig_task, out_dir / suffix)
        rig_glbs = [p for p in rig_paths if p.suffix == ".glb"]
        problems = []
        if rig_glbs:
            description, problems = validate_rig_glb(rig_glbs[0], rig_type)
            eprint(f"Rig skeleton ({attempt}/{attempts}): {description}")
        if not problems:
            rig_id = candidate_id
            break
        last_detail = "; ".join(problems)
        eprint(f"rig attempt {attempt}/{attempts} failed validation: {last_detail}")
    if rig_id is None:
        if not args.force_rig:
            raise TripoError(
                f"No structurally valid rig after {attempts} attempt(s) ({last_detail}). "
                "Retargets on a bad rig warp the character. Regenerate the base model with "
                "clearer limb separation (strict T-pose, arms horizontal, legs apart and visible, "
                "no long skirt/cape/props fusing limbs to the body), or pass --force-rig to use "
                "the last rig anyway."
            )
        rig_id = candidate_id
        eprint(f"warning: using unvalidated rig ({last_detail}); continuing (--force-rig)")

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
        anim_id = submit_task(api_key, retarget_payload)
        anim_task = wait_for_task(api_key, anim_id, args.interval, args.timeout)
        if anim_task.get("status") != "success":
            raise TripoError(f"Animation batch {batch} failed: {anim_task.get('status')}")
        batch_name = safe_name("-".join(item.split(":")[-1] for item in batch))
        download_outputs(anim_task, out_dir / batch_name)
    eprint("Inspect gltf.animations clip names/counts in each download before wiring the AnimationMixer.")


def load_glb(path: Path) -> tuple[dict[str, Any], bytes]:
    import struct
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise TripoError(f"Not a GLB file: {path}")
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
        raise TripoError(f"No JSON chunk in GLB: {path}")
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
    pipeline.set_defaults(func=cmd_character_pipeline)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except TripoError as exc:
        eprint(f"threejs_3d_asset.py: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
