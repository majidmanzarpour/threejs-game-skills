#!/usr/bin/env python3
"""Shrink Meshy GLBs for embedding: animation-only clips, downscaled rig textures.

Meshy returns every clip as a full copy of the skinned mesh (~8 MB each) and bakes a
2k-4k texture into the rig, which is far more than a preview page or an inline viewer
needs. `clip` keeps only the animation data; `rig` re-encodes the embedded texture and
can split it out into a separate file.
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import struct
import sys
from typing import Any

JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


def read_glb(path: Path) -> tuple[dict[str, Any], bytes]:
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise SystemExit(f"not a GLB: {path}")
    offset, gltf, binary = 12, None, b""
    while offset < len(data):
        length, kind = struct.unpack_from("<II", data, offset)
        chunk = data[offset + 8:offset + 8 + length]
        if kind == JSON_CHUNK:
            gltf = json.loads(chunk)
        elif kind == BIN_CHUNK:
            binary = chunk
        offset += 8 + length
    if gltf is None:
        raise SystemExit(f"no JSON chunk: {path}")
    return gltf, binary


def write_glb(gltf: dict[str, Any], binary: bytes, out: Path) -> int:
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    bn = binary + b"\0" * ((4 - len(binary) % 4) % 4)
    total = 12 + 8 + len(js) + (8 + len(bn) if bn else 0)
    blob = bytearray(b"glTF" + struct.pack("<II", 2, total))
    blob += struct.pack("<II", len(js), JSON_CHUNK) + js
    if bn:
        blob += struct.pack("<II", len(bn), BIN_CHUNK) + bn
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)
    return total


def view_bytes(gltf: dict[str, Any], binary: bytes, index: int) -> bytes:
    view = gltf["bufferViews"][index]
    start = view.get("byteOffset", 0)
    return binary[start:start + view["byteLength"]]


def repack(gltf: dict[str, Any], views: dict[int, bytes]) -> tuple[list[dict[str, Any]], bytes, dict[int, int]]:
    binary = bytearray()
    remap: dict[int, int] = {}
    packed: list[dict[str, Any]] = []
    for old, payload in views.items():
        while len(binary) % 4:
            binary.append(0)
        view = dict(gltf["bufferViews"][old])
        view["byteOffset"] = len(binary)
        view["byteLength"] = len(payload)
        view["buffer"] = 0
        remap[old] = len(packed)
        packed.append(view)
        binary += payload
    return packed, bytes(binary), remap


def slim_clip(src: Path, out: Path) -> int:
    """Drop meshes, skins, materials and images; keep nodes plus animation samplers."""
    gltf, binary = read_glb(src)
    used = sorted({s[k] for anim in gltf.get("animations", []) for s in anim["samplers"] for k in ("input", "output")})
    if not used:
        raise SystemExit(f"no animation samplers in {src}")
    acc_remap = {old: i for i, old in enumerate(used)}
    accessors = [gltf["accessors"][i] for i in used]
    views = {a["bufferView"]: view_bytes(gltf, binary, a["bufferView"]) for a in accessors}
    packed, new_binary, view_remap = repack(gltf, views)

    new_accessors = []
    for acc in accessors:
        acc = dict(acc)
        acc["bufferView"] = view_remap[acc["bufferView"]]
        new_accessors.append(acc)

    animations = json.loads(json.dumps(gltf.get("animations", [])))
    for anim in animations:
        for sampler in anim["samplers"]:
            sampler["input"] = acc_remap[sampler["input"]]
            sampler["output"] = acc_remap[sampler["output"]]

    slim = {
        "asset": gltf["asset"],
        "scene": gltf.get("scene", 0),
        "scenes": gltf.get("scenes", [{"nodes": [0]}]),
        "nodes": [{k: v for k, v in node.items() if k not in ("mesh", "skin")} for node in gltf.get("nodes", [])],
        "accessors": new_accessors,
        "bufferViews": packed,
        "buffers": [{"byteLength": len(new_binary)}],
        "animations": animations,
    }
    return write_glb(slim, new_binary, out)


def slim_rig(src: Path, out: Path, max_px: int, quality: int, extract: Path | None) -> int:
    """Re-encode the embedded texture as JPEG, or split it out entirely.

    Splitting matters for pages under a strict CSP: a GLB texture is decoded through a
    blob: URL, and this material's emissiveFactor is 1,1,1 - if the decode is blocked the
    model renders as a white silhouette. A separate file can be fed through
    createImageBitmap, which loads no resource at all.
    """
    gltf, binary = read_glb(src)
    images = gltf.get("images", [])
    replaced: dict[int, bytes] = {}
    for image in images:
        if "bufferView" not in image:
            continue
        raw = view_bytes(gltf, binary, image["bufferView"])
        if max_px > 0:
            try:
                from PIL import Image
            except ImportError:
                if extract is None:
                    raise SystemExit("Pillow is required to resize textures; pass --max-px 0 to copy as-is")
                Image = None
            if Image is not None:
                im = Image.open(io.BytesIO(raw)).convert("RGB")
                im.thumbnail((max_px, max_px), Image.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=quality)
                raw = buf.getvalue()
                image["mimeType"] = "image/jpeg"
        if extract is not None:
            extract.parent.mkdir(parents=True, exist_ok=True)
            extract.write_bytes(raw)
        else:
            replaced[image["bufferView"]] = raw

    drop = set(replaced) if not extract else {i["bufferView"] for i in images if "bufferView" in i}
    views = {}
    for index in range(len(gltf["bufferViews"])):
        if extract and index in drop:
            continue
        views[index] = replaced.get(index) or view_bytes(gltf, binary, index)
    packed, new_binary, remap = repack(gltf, views)
    gltf["bufferViews"] = packed
    gltf["buffers"] = [{"byteLength": len(new_binary)}]
    for acc in gltf.get("accessors", []):
        if "bufferView" in acc:
            acc["bufferView"] = remap[acc["bufferView"]]
    if extract:
        for material in gltf.get("materials", []):
            pbr = material.setdefault("pbrMetallicRoughness", {})
            for slot in ("baseColorTexture", "metallicRoughnessTexture"):
                pbr.pop(slot, None)
            for slot in ("normalTexture", "emissiveTexture", "occlusionTexture"):
                material.pop(slot, None)
        for key in ("images", "textures", "samplers"):
            gltf.pop(key, None)
    else:
        for image in images:
            if "bufferView" in image:
                image["bufferView"] = remap[image["bufferView"]]
    return write_glb(gltf, new_binary, out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    clip = sub.add_parser("clip", help="strip a clip GLB down to its animation data")
    clip.add_argument("src")
    clip.add_argument("out")

    rig = sub.add_parser("rig", help="downscale or split out the rig's embedded texture")
    rig.add_argument("src")
    rig.add_argument("out")
    rig.add_argument("--max-px", type=int, default=1024)
    rig.add_argument("--quality", type=int, default=82)
    rig.add_argument("--extract-texture", help="write the texture here and remove it from the GLB")

    args = parser.parse_args()
    if args.command == "clip":
        size = slim_clip(Path(args.src), Path(args.out))
    else:
        size = slim_rig(
            Path(args.src), Path(args.out), args.max_px, args.quality,
            Path(args.extract_texture) if args.extract_texture else None,
        )
    print(f"{args.out}: {size / 1e6:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
