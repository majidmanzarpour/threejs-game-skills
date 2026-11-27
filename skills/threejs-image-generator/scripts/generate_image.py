#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "pillow>=10.0.0",
# ]
# ///
"""
Generate and edit 2D game images using Google's Gemini Image API (GA models).

Usage:
    uv run generate_image.py --prompt "your image description" --filename "output.png" \
        [--model gemini-3-pro-image] [--aspect-ratio 16:9] [--resolution 512px|1K|2K|4K] \
        [--input-image ref.png ...] [--api-key KEY]
    uv run generate_image.py probe [--validate] [--model MODEL] [--api-key KEY]
"""

from __future__ import annotations

import argparse
import base64
from io import BytesIO
import os
from pathlib import Path
import sys
from typing import Any


DEFAULT_MODEL = "gemini-3-pro-image"
RECOMMENDED_MODELS = (
    "gemini-3-pro-image",
    "gemini-3.1-flash-image",
    "gemini-3.1-flash-lite-image",
    "gemini-2.5-flash-image",
)
DEPRECATED_MODELS = {
    "gemini-3-pro-image-preview": "gemini-3-pro-image",
    "gemini-3.1-flash-image-preview": "gemini-3.1-flash-image",
}
SUPPORTED_RESOLUTIONS = ("512px", "1K", "2K", "4K")
SUPPORTED_ASPECT_RATIOS = (
    "1:1", "3:2", "2:3", "4:3", "3:4", "4:5", "5:4", "16:9", "9:16", "21:9",
    "1:4", "4:1", "1:8", "8:1",
)
EXTENDED_ASPECT_RATIOS = {"1:4", "4:1", "1:8", "8:1"}


class ImageGeneratorError(RuntimeError):
    pass


def get_api_key(provided_key: str | None) -> str | None:
    """Get API key from argument first, then GEMINI_API_KEY env var."""
    if provided_key:
        return provided_key
    return os.environ.get("GEMINI_API_KEY")


def validate_model_name(model: str) -> str:
    replacement = DEPRECATED_MODELS.get(model)
    if replacement:
        raise ImageGeneratorError(
            f"Model {model!r} was shut down on June 25, 2026. "
            f"Use the stable GA replacement {replacement!r} instead."
        )
    return model


def detect_resolution_from_size(width: int, height: int) -> str:
    max_dim = max(width, height)
    if max_dim >= 3000:
        return "4K"
    if max_dim >= 1500:
        return "2K"
    return "1K"


def build_image_config_kwargs(resolution: str, aspect_ratio: str | None = None) -> dict[str, str]:
    kwargs: dict[str, str] = {"image_size": resolution}
    if aspect_ratio:
        kwargs["aspect_ratio"] = aspect_ratio
    return kwargs


def extract_response_parts(response: Any) -> tuple[list[str], list[bytes]]:
    """Safely extract text notes and raw image bytes from a generate_content response."""
    parts = getattr(response, "parts", None)
    if parts is None:
        candidates = getattr(response, "candidates", None) or []
        parts = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            cand_parts = getattr(content, "parts", None)
            if cand_parts:
                parts.extend(cand_parts)
    texts: list[str] = []
    images: list[bytes] = []
    for part in parts or []:
        text = getattr(part, "text", None)
        inline = getattr(part, "inline_data", None)
        if text is not None:
            texts.append(text)
        if inline is not None and getattr(inline, "data", None) is not None:
            raw = inline.data
            if isinstance(raw, str):
                raw = base64.b64decode(raw)
            images.append(bytes(raw))
    return texts, images


def build_probe_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate_image.py probe",
        description="Print GEMINI_API_KEY=SET|MISSING and optionally validate model access.",
    )
    parser.add_argument("--validate", action="store_true", help="Verify API key and model access via models.get.")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help=f"Model to verify (default: {DEFAULT_MODEL}).")
    parser.add_argument("--api-key", "-k", help="Gemini API key (overrides GEMINI_API_KEY env var).")
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate and edit 2D game images using Google's Gemini Image API.",
        epilog="Use `generate_image.py probe [--validate]` to check GEMINI_API_KEY availability.",
    )
    parser.add_argument("--prompt", "-p", required=True, help="Image description or edit instruction.")
    parser.add_argument("--filename", "-f", required=True, help="Output file path (PNG preserves alpha; JPG/JPEG flattens).")
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL,
        help=(
            f"Gemini image model (default: {DEFAULT_MODEL}). "
            f"Current GA models: {', '.join(RECOMMENDED_MODELS)}."
        ),
    )
    parser.add_argument(
        "--input-image", "-i",
        action="append",
        dest="input_images",
        help="Input image path for editing or style/character reference; repeat for multi-reference prompts.",
    )
    parser.add_argument(
        "--resolution", "-r",
        choices=list(SUPPORTED_RESOLUTIONS),
        default=None,
        help="Output resolution: 512px (Flash draft), 1K, 2K (default for generation), or 4K; "
             "when editing, defaults to match the first input image size.",
    )
    parser.add_argument(
        "--aspect-ratio", "-a",
        choices=list(SUPPORTED_ASPECT_RATIOS),
        default=None,
        help="Output aspect ratio (e.g. 1:1 textures/icons, 16:9 skies/menus, 3:4 character sheets; "
             "1:4/4:1/1:8/8:1 require gemini-3.1-flash-image).",
    )
    parser.add_argument("--api-key", "-k", help="Gemini API key (overrides GEMINI_API_KEY env var).")
    return parser


def cmd_probe(argv: list[str]) -> int:
    args = build_probe_parser().parse_args(argv)
    model = validate_model_name(args.model)
    key = get_api_key(args.api_key)
    status = "SET" if key else "MISSING"
    print(f"GEMINI_API_KEY={status}")
    if args.validate and key:
        from google import genai
        client = genai.Client(api_key=key)
        info = client.models.get(model=model)
        name = getattr(info, "name", None) or model
        print(f"VALID_MODEL={name}")
    return 0


def save_image_bytes(image_bytes: bytes, output_path: Path) -> None:
    from PIL import Image as PILImage

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = PILImage.open(BytesIO(image_bytes))
    suffix = output_path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        if image.mode in ("RGBA", "LA", "P"):
            rgba = image.convert("RGBA")
            flat = PILImage.new("RGB", rgba.size, (255, 255, 255))
            flat.paste(rgba, mask=rgba.split()[3])
            flat.save(str(output_path), "JPEG", quality=92)
        else:
            image.convert("RGB").save(str(output_path), "JPEG", quality=92)
    else:
        if image.mode not in ("RGB", "RGBA"):
            has_alpha = "A" in image.mode or (image.mode == "P" and "transparency" in image.info)
            image = image.convert("RGBA" if has_alpha else "RGB")
        image.save(str(output_path), "PNG")
        if image.mode == "RGBA":
            print("Alpha channel preserved (RGBA PNG).")


def run_generate(args: argparse.Namespace) -> int:
    model = validate_model_name(args.model)
    if args.aspect_ratio in EXTENDED_ASPECT_RATIOS and "flash" not in model and "nano-banana-2" not in model:
        print(
            f"Warning: extreme aspect ratio {args.aspect_ratio!r} is best supported by "
            "gemini-3.1-flash-image; proceeding with requested model.",
            file=sys.stderr,
        )
    if args.resolution == "512px" and "pro" in model:
        print(
            "Warning: 512px resolution is intended for Flash models (e.g. gemini-3.1-flash-image); "
            "pro models may require >= 1K.",
            file=sys.stderr,
        )

    api_key = get_api_key(args.api_key)
    if not api_key:
        raise ImageGeneratorError(
            "No API key provided. Set GEMINI_API_KEY or pass --api-key."
        )

    from google import genai
    from google.genai import types
    from PIL import Image as PILImage

    client = genai.Client(api_key=api_key)
    output_path = Path(args.filename)

    input_images: list[Any] = []
    output_resolution = args.resolution
    for img_path in args.input_images or []:
        try:
            loaded = PILImage.open(img_path)
            input_images.append(loaded)
            print(f"Loaded input image: {img_path}")
        except Exception as exc:
            raise ImageGeneratorError(f"Error loading input image {img_path}: {exc}") from exc

    if input_images and output_resolution is None:
        width, height = input_images[0].size
        output_resolution = detect_resolution_from_size(width, height)
        print(f"Auto-detected resolution: {output_resolution} (from input {width}x{height})")
    if output_resolution is None:
        output_resolution = "2K"

    contents: Any = [*input_images, args.prompt] if input_images else args.prompt
    action = "Editing/referencing image" if input_images else "Generating image"
    ratio_note = f", aspect_ratio={args.aspect_ratio}" if args.aspect_ratio else ""
    print(f"{action} with model={model}, resolution={output_resolution}{ratio_note}...")

    image_cfg = types.ImageConfig(**build_image_config_kwargs(output_resolution, args.aspect_ratio))
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=image_cfg,
        ),
    )

    texts, images = extract_response_parts(response)
    for text in texts:
        print(f"Model response: {text}")
    if not images:
        candidates = getattr(response, "candidates", None) or []
        reasons = [str(getattr(c, "finish_reason", "")) for c in candidates if getattr(c, "finish_reason", None)]
        reason_detail = f" (finish_reason: {', '.join(reasons)})" if reasons else ""
        raise ImageGeneratorError(f"No image was generated in the response{reason_detail}.")

    save_image_bytes(images[-1], output_path)
    print(f"\nImage saved: {output_path.resolve()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        if argv and argv[0] == "probe":
            return cmd_probe(argv[1:])
        args = build_parser().parse_args(argv)
        return run_generate(args)
    except ImageGeneratorError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error generating image: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
