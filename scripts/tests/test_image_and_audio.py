"""Offline unit tests for Gemini Image (generate_image.py) and ElevenLabs (threejs_audio_asset.py)."""

from __future__ import annotations

import base64
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, rel_path: str):
    path = ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gemini_img = load_module("gemini_image_helper", "skills/threejs-image-generator/scripts/generate_image.py")
eleven_audio = load_module("eleven_audio_helper", "skills/threejs-audio-generator/scripts/threejs_audio_asset.py")


class GeminiImageTests(unittest.TestCase):
    def test_default_model_is_ga_and_shutdown_previews_fail_fast(self):
        self.assertEqual(gemini_img.DEFAULT_MODEL, "gemini-3-pro-image")
        for retired in ("gemini-3-pro-image-preview", "gemini-3.1-flash-image-preview"):
            with self.subTest(model=retired):
                with self.assertRaisesRegex(gemini_img.ImageGeneratorError, "shut down"):
                    gemini_img.validate_model_name(retired)

    def test_parser_accepts_model_aspect_ratio_512px_and_multiple_inputs(self):
        args = gemini_img.build_parser().parse_args([
            "--prompt", "wide twilight skyline",
            "--filename", "sky.png",
            "--model", "gemini-3.1-flash-image",
            "--aspect-ratio", "16:9",
            "--resolution", "512px",
            "-i", "ref1.png",
            "-i", "ref2.png",
        ])
        self.assertEqual(args.model, "gemini-3.1-flash-image")
        self.assertEqual(args.aspect_ratio, "16:9")
        self.assertEqual(args.resolution, "512px")
        self.assertEqual(args.input_images, ["ref1.png", "ref2.png"])
        self.assertEqual(
            gemini_img.build_image_config_kwargs(args.resolution, args.aspect_ratio),
            {"image_size": "512px", "aspect_ratio": "16:9"},
        )

    def test_probe_prints_contract_without_sdk_import(self):
        out = io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=True), redirect_stdout(out):
            rc = gemini_img.main(["probe"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue().strip(), "GEMINI_API_KEY=MISSING")

        out2 = io.StringIO()
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}), redirect_stdout(out2):
            rc2 = gemini_img.main(["probe"])
        self.assertEqual(rc2, 0)
        self.assertEqual(out2.getvalue().strip(), "GEMINI_API_KEY=SET")

    def test_extract_response_parts_handles_none_and_candidate_fallback(self):
        # Blocked/empty response with parts=None must not crash
        texts, images = gemini_img.extract_response_parts(SimpleNamespace(parts=None, candidates=[]))
        self.assertEqual((texts, images), ([], []))

        # Candidate fallback with base64 string inline_data
        raw = b"\x89PNG\r\n\x1a\nfake"
        b64 = base64.b64encode(raw).decode("ascii")
        resp = SimpleNamespace(
            parts=None,
            candidates=[
                SimpleNamespace(
                    content=SimpleNamespace(
                        parts=[
                            SimpleNamespace(text="generated sky", inline_data=None),
                            SimpleNamespace(text=None, inline_data=SimpleNamespace(data=b64)),
                        ]
                    )
                )
            ],
        )
        texts2, images2 = gemini_img.extract_response_parts(resp)
        self.assertEqual(texts2, ["generated sky"])
        self.assertEqual(images2, [raw])


class FakeAudioResponse:
    def __init__(self, data: bytes):
        self._data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._data


class ElevenLabsAudioTests(unittest.TestCase):
    def setUp(self):
        self.requests: list[dict] = []
        self.response_bytes = b"ID3fakeaudio"

    def fake_urlopen(self, req, timeout=300):
        self.requests.append({
            "method": req.get_method(),
            "url": req.full_url,
            "headers": {k.lower(): v for k, v in req.header_items()},
            "body": req.data,
        })
        return FakeAudioResponse(self.response_bytes)

    def run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}), \
             mock.patch.object(eleven_audio.urllib.request, "urlopen", side_effect=self.fake_urlopen), \
             redirect_stdout(out), redirect_stderr(err):
            parser = eleven_audio.build_parser()
            args = parser.parse_args(argv)
            try:
                rc = args.func(args)
            except eleven_audio.AudioGeneratorError as exc:
                err.write(str(exc))
                rc = 1
        return rc, out.getvalue(), err.getvalue()

    def test_sfx_defaults_to_v3_and_warns_on_v2(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "hit.mp3"
            rc, _out, err = self.run_cli(["sfx", "--prompt", "crisp laser hit", "--duration", "0.25", "--out", str(out_path)])
            self.assertEqual(rc, 0, err)
            payload = json.loads(self.requests[0]["body"])
            self.assertEqual(payload["model_id"], "eleven_text_to_sound_v3")
            self.assertEqual(payload["duration_seconds"], 0.25)
            self.assertEqual(self.requests[0]["headers"]["accept"], "audio/mpeg")

            rc2, _out2, err2 = self.run_cli([
                "sfx", "--prompt", "legacy hit", "--model-id", "eleven_text_to_sound_v2", "--duration", "1.0", "--out", str(out_path)
            ])
            self.assertEqual(rc2, 0)
            self.assertIn("retires March 1, 2027", err2)

    def test_music_defaults_to_v2_5_and_warns_on_v1(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "boss.mp3"
            rc, _out, err = self.run_cli([
                "music", "--prompt", "boss theme 140 BPM", "--duration", "30", "--instrumental", "--out", str(out_path)
            ])
            self.assertEqual(rc, 0, err)
            payload = json.loads(self.requests[0]["body"])
            self.assertEqual(payload["model_id"], "music_v2_5")
            self.assertEqual(payload["music_length_ms"], 30000)
            self.assertTrue(payload["force_instrumental"])

            rc2, _out2, err2 = self.run_cli([
                "music", "--prompt", "old loop", "--model-id", "music_v1", "--out", str(out_path)
            ])
            self.assertEqual(rc2, 0)
            self.assertIn("retires January 31, 2027", err2)

    def test_tts_defaults_to_v4_and_guards_style_slider(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "line.mp3"
            rc, _out, err = self.run_cli(["tts", "--text", "[shouts] Incoming!", "--out", str(out_path)])
            self.assertEqual(rc, 0, err)
            payload = json.loads(self.requests[0]["body"])
            self.assertEqual(payload["model_id"], "eleven_v4")

            # Passing --style with eleven_v4 fails cleanly before any HTTP call
            before = len(self.requests)
            rc_bad, _out_bad, err_bad = self.run_cli(["tts", "--text", "Hi", "--style", "0.5", "--out", str(out_path)])
            self.assertEqual(rc_bad, 1)
            self.assertIn("not supported on eleven_v4", err_bad)
            self.assertEqual(len(self.requests), before)

            # Legacy multilingual_v2 still accepts --style
            rc_v2, _out_v2, err_v2 = self.run_cli([
                "tts", "--text", "Hi", "--model-id", "eleven_multilingual_v2", "--style", "0.4", "--out", str(out_path)
            ])
            self.assertEqual(rc_v2, 0, err_v2)

    def test_dynamic_accept_header_and_voice_change_deprecation_warning(self):
        self.assertEqual(eleven_audio.accept_header_for("mp3_44100_128"), "audio/mpeg")
        self.assertEqual(eleven_audio.accept_header_for("pcm_44100"), "audio/pcm")
        self.assertEqual(eleven_audio.accept_header_for("opus_48000_128"), "audio/ogg")
        self.assertEqual(eleven_audio.accept_header_for("ulaw_8000"), "audio/basic")

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "scratch.wav"
            src.write_bytes(b"RIFFfake")
            out_path = Path(tmp) / "final.pcm"
            rc, _out, err = self.run_cli([
                "voice-change", "--input", str(src), "--out", str(out_path),
                "--output-format", "pcm_44100", "--optimize-streaming-latency", "2",
            ])
            self.assertEqual(rc, 0)
            self.assertIn("deprecated", err.lower())
            self.assertEqual(self.requests[0]["headers"]["accept"], "audio/pcm")

    def test_models_subcommand(self):
        self.response_bytes = json.dumps([{"model_id": "eleven_v4", "name": "Eleven v4"}]).encode("utf-8")
        rc, out, err = self.run_cli(["models"])
        self.assertEqual(rc, 0, err)
        self.assertIn("eleven_v4\tEleven v4", out)
        self.assertTrue(self.requests[0]["url"].endswith("/v1/models"))


if __name__ == "__main__":
    unittest.main()
