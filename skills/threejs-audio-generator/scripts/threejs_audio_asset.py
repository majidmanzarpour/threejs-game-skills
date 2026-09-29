#!/usr/bin/env python3
"""Generate and process Three.js game audio assets (SFX, music, voice) with ElevenLabs."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


BASE_URL = "https://api.elevenlabs.io/v1"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_TTS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"


class AudioGeneratorError(RuntimeError):
    pass


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def api_key(args: argparse.Namespace) -> str:
    key = getattr(args, "api_key", None) or os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise AudioGeneratorError("Missing API key. Set ELEVENLABS_API_KEY or pass --api-key.")
    return key


def build_url(path: str, query: dict[str, Any] | None = None) -> str:
    url = f"{BASE_URL}{path}"
    clean = {key: value for key, value in (query or {}).items() if value is not None}
    if clean:
        url = f"{url}?{urllib.parse.urlencode(clean)}"
    return url


def request_bytes(
    method: str,
    path: str,
    key: str,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    query: dict[str, Any] | None = None,
    timeout: int = 300,
) -> bytes:
    req = urllib.request.Request(build_url(path, query), data=body, method=method)
    req.add_header("xi-api-key", key)
    for name, value in (headers or {}).items():
        req.add_header(name, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AudioGeneratorError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise AudioGeneratorError(f"Network error: {exc.reason}") from exc


def post_json_audio(
    args: argparse.Namespace, path: str, payload: dict[str, Any], out: Path, timeout: int = 300
) -> None:
    body = json.dumps(payload).encode("utf-8")
    data = request_bytes(
        "POST",
        path,
        api_key(args),
        body=body,
        headers={"Content-Type": "application/json", "Accept": "audio/mpeg"},
        query={"output_format": args.output_format},
        timeout=timeout,
    )
    write_file(out, data)


def multipart_body(fields: dict[str, Any], files: dict[str, Path]) -> tuple[bytes, str]:
    boundary = f"----threejs-audio-{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    for name, value in fields.items():
        if value is None:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(str(value).encode())
        chunks.append(b"\r\n")

    for name, path in files.items():
        if not path.exists():
            raise AudioGeneratorError(f"Input file not found: {path}")
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'.encode()
        )
        chunks.append(f"Content-Type: {mime}\r\n\r\n".encode())
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def post_multipart_audio(
    args: argparse.Namespace,
    path: str,
    fields: dict[str, Any],
    files: dict[str, Path],
    out: Path,
    query: dict[str, Any] | None = None,
) -> None:
    body, boundary = multipart_body(fields, files)
    data = request_bytes(
        "POST",
        path,
        api_key(args),
        body=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Accept": "audio/mpeg"},
        query=query,
    )
    write_file(out, data)


def write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"Audio saved: {path.resolve()}")


def voice_settings(args: argparse.Namespace) -> dict[str, Any] | None:
    settings: dict[str, Any] = {}
    for field in ("stability", "similarity_boost", "style"):
        value = getattr(args, field, None)
        if value is not None:
            settings[field] = value
    if getattr(args, "speaker_boost", False):
        settings["use_speaker_boost"] = True
    return settings or None


def cmd_probe(args: argparse.Namespace) -> int:
    marker = "SET" if (args.api_key or os.environ.get("ELEVENLABS_API_KEY")) else "MISSING"
    print(f"ELEVENLABS_API_KEY={marker}")
    if args.validate and marker == "SET":
        data = request_bytes("GET", "/user", api_key(args))
        user = json.loads(data.decode("utf-8"))
        print(f"VALID_USER={user.get('email') or user.get('user_id') or 'ok'}")
    return 0


def cmd_sfx(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "text": args.prompt,
        "model_id": args.model_id,
        "prompt_influence": args.prompt_influence,
        "loop": args.loop,
    }
    if args.duration is not None:
        payload["duration_seconds"] = args.duration
    post_json_audio(args, "/sound-generation", payload, Path(args.out))
    return 0


def cmd_music(args: argparse.Namespace) -> int:
    if bool(args.prompt) == bool(args.plan):
        raise AudioGeneratorError("Pass exactly one of --prompt or --plan.")
    payload: dict[str, Any] = {}
    if args.model_id:
        payload["model_id"] = args.model_id
    if args.prompt:
        if args.seed is not None:
            raise AudioGeneratorError("--seed only applies with --plan; the API rejects it with --prompt.")
        payload["prompt"] = args.prompt
        if args.duration is not None:
            if not 3 <= args.duration <= 600:
                raise AudioGeneratorError("--duration must be between 3 and 600 seconds.")
            payload["music_length_ms"] = int(args.duration * 1000)
        if args.instrumental:
            payload["force_instrumental"] = True
    else:
        if args.duration is not None or args.instrumental:
            raise AudioGeneratorError("--duration and --instrumental only apply with --prompt; set section lengths in the plan.")
        plan_path = Path(args.plan)
        if not plan_path.exists():
            raise AudioGeneratorError(f"Composition plan not found: {plan_path}")
        try:
            payload["composition_plan"] = json.loads(plan_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AudioGeneratorError(f"Composition plan is not valid JSON: {exc}") from exc
        if args.seed is not None:
            payload["seed"] = args.seed
    post_json_audio(args, "/music", payload, Path(args.out), timeout=900)
    return 0


def cmd_tts(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "text": args.text,
        "model_id": args.model_id,
    }
    settings = voice_settings(args)
    if settings:
        payload["voice_settings"] = settings
    post_json_audio(args, f"/text-to-speech/{urllib.parse.quote(args.voice_id)}", payload, Path(args.out))
    return 0


def cmd_isolate(args: argparse.Namespace) -> int:
    fields = {"file_format": args.file_format}
    post_multipart_audio(
        args,
        "/audio-isolation",
        fields,
        {"audio": Path(args.input)},
        Path(args.out),
        query={"output_format": args.output_format},
    )
    return 0


def cmd_voice_change(args: argparse.Namespace) -> int:
    fields: dict[str, Any] = {
        "model_id": args.model_id,
        "remove_background_noise": args.remove_background_noise,
        "file_format": args.file_format,
    }
    settings = voice_settings(args)
    if settings:
        fields["voice_settings"] = json.dumps(settings)
    if args.seed is not None:
        fields["seed"] = args.seed
    post_multipart_audio(
        args,
        f"/speech-to-speech/{urllib.parse.quote(args.voice_id)}",
        fields,
        {"audio": Path(args.input)},
        Path(args.out),
        query={
            "output_format": args.output_format,
            "optimize_streaming_latency": args.optimize_streaming_latency,
        },
    )
    return 0


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-key", help="ElevenLabs API key; defaults to ELEVENLABS_API_KEY")


def add_output_format(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output-format", default=DEFAULT_OUTPUT_FORMAT)


def add_voice_settings(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--stability", type=float)
    parser.add_argument("--similarity-boost", type=float)
    parser.add_argument("--style", type=float)
    parser.add_argument("--speaker-boost", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and process Three.js game audio assets.")
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe", help="Report whether ELEVENLABS_API_KEY is available.")
    add_common(probe)
    probe.add_argument("--validate", action="store_true", help="Call /user to validate the key.")
    probe.set_defaults(func=cmd_probe)

    sfx = sub.add_parser("sfx", help="Generate sound effects or ambience from a prompt.")
    add_common(sfx)
    add_output_format(sfx)
    sfx.add_argument("--prompt", required=True)
    sfx.add_argument("--out", required=True)
    sfx.add_argument("--duration", type=float, help="Duration in seconds, typically 0.5-30.")
    sfx.add_argument("--prompt-influence", type=float, default=0.55)
    sfx.add_argument("--loop", action="store_true")
    sfx.add_argument("--model-id", default="eleven_text_to_sound_v2")
    sfx.set_defaults(func=cmd_sfx)

    music = sub.add_parser("music", help="Compose a music track from a prompt or a composition plan.")
    add_common(music)
    add_output_format(music)
    music.add_argument("--prompt", help="Style, instrumentation, tempo, mood, and game use.")
    music.add_argument("--plan", help="Path to a composition_plan JSON file (instead of --prompt).")
    music.add_argument("--out", required=True)
    music.add_argument("--duration", type=float, help="Length in seconds, 3-600 (prompt mode only).")
    music.add_argument("--instrumental", action="store_true", help="Guarantee no vocals (prompt mode only).")
    music.add_argument("--seed", type=int, help="Seed for reproducible output (plan mode only).")
    music.add_argument("--model-id", help="Music model, e.g. music_v1; defaults to the API default.")
    music.set_defaults(func=cmd_music)

    tts = sub.add_parser("tts", help="Generate a spoken line from text.")
    add_common(tts)
    add_output_format(tts)
    add_voice_settings(tts)
    tts.add_argument("--text", required=True)
    tts.add_argument("--out", required=True)
    tts.add_argument("--voice-id", default=DEFAULT_TTS_VOICE_ID)
    tts.add_argument("--model-id", default="eleven_multilingual_v2")
    tts.set_defaults(func=cmd_tts)

    isolate = sub.add_parser("isolate", help="Clean or isolate speech from a source audio file.")
    add_common(isolate)
    add_output_format(isolate)
    isolate.add_argument("--input", required=True)
    isolate.add_argument("--out", required=True)
    isolate.add_argument("--file-format", default="other")
    isolate.set_defaults(func=cmd_isolate)

    voice = sub.add_parser("voice-change", help="Convert source performance to a target voice.")
    add_common(voice)
    add_output_format(voice)
    add_voice_settings(voice)
    voice.add_argument("--input", required=True)
    voice.add_argument("--out", required=True)
    voice.add_argument("--voice-id", default=DEFAULT_TTS_VOICE_ID)
    voice.add_argument("--model-id", default="eleven_multilingual_sts_v2")
    voice.add_argument("--file-format", default="other")
    voice.add_argument("--seed", type=int)
    voice.add_argument("--remove-background-noise", action="store_true")
    voice.add_argument("--optimize-streaming-latency", type=int, choices=range(0, 5))
    voice.set_defaults(func=cmd_voice_change)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except AudioGeneratorError as exc:
        eprint(f"threejs_audio_asset.py: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
