#!/usr/bin/env python3
"""Contract tests for the dependency-free Atlas 3D client."""

from __future__ import annotations

import importlib.util
import json
import os
import struct
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT = Path(__file__).with_name("atlas_3d_asset.py")
SPEC = importlib.util.spec_from_file_location("atlas_3d_asset", SCRIPT)
assert SPEC and SPEC.loader
atlas = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = atlas
SPEC.loader.exec_module(atlas)


class AtlasHandler(BaseHTTPRequestHandler):
    post_count = 0
    upload_count = 0
    poll_count = 0
    last_payload: dict[str, object] | None = None
    download_authorization: str | None = None
    submit_error = False

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def send_json(self, value: object, status: int = 200) -> None:
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/v1/models":
            self.send_json(
                {
                    "code": "200",
                    "data": [
                        {
                            "model": "test/text-to-3d",
                            "type": "Image",
                            "schema": f"{self.base_url}/schema/text.json",
                        },
                        {
                            "model": "test/image-to-3d",
                            "type": "Image",
                            "schema": f"{self.base_url}/schema/image.json",
                        },
                    ],
                }
            )
            return
        if self.path.startswith("/schema/"):
            image = self.path.endswith("image.json")
            required = ["model", "image_url"] if image else ["model", "prompt"]
            properties: dict[str, object] = {
                "model": {"type": "string"},
                "pbr": {"type": "boolean"},
                "format": {"type": "string", "enum": ["GLB"]},
            }
            properties["image_url" if image else "prompt"] = {"type": "string"}
            self.send_json(
                {
                    "paths": {
                        "/api/v1/model/generateImage": {"post": {}},
                        "/api/v1/model/prediction/{request_id}": {"get": {}},
                    },
                    "components": {
                        "schemas": {
                            "Input": {"properties": properties, "required": required}
                        }
                    },
                }
            )
            return
        if self.path == "/api/v1/model/prediction/pred-1":
            type(self).poll_count += 1
            status = "processing" if type(self).poll_count == 1 else "completed"
            data: dict[str, object] = {"id": "pred-1", "status": status}
            if status == "completed":
                data["files"] = [
                    {
                        "url": f"{self.base_url}/files/model.glb",
                        "type": "GLB",
                        "file_name": "model.glb",
                    }
                ]
            self.send_json({"code": 200, "data": data})
            return
        if self.path == "/files/model.glb":
            type(self).download_authorization = self.headers.get("Authorization")
            body = b"glTF" + struct.pack("<II", 2, 12)
            self.send_response(200)
            self.send_header("Content-Type", "model/gltf-binary")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/api/v1/model/uploadMedia":
            type(self).upload_count += 1
            length = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(length)
            self.send_json(
                {
                    "code": 200,
                    "data": {"download_url": f"{self.base_url}/files/source.png"},
                }
            )
            return
        if self.path == "/api/v1/model/generateImage":
            type(self).post_count += 1
            length = int(self.headers.get("Content-Length", "0"))
            type(self).last_payload = json.loads(self.rfile.read(length))
            if type(self).submit_error:
                self.send_json({"message": "temporary upstream error"}, status=503)
                return
            self.send_json({"code": 200, "data": {"id": "pred-1", "status": "created"}})
            return
        self.send_error(404)

    def log_message(self, *_: object) -> None:
        pass


class AtlasClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), AtlasHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self) -> None:
        AtlasHandler.post_count = 0
        AtlasHandler.upload_count = 0
        AtlasHandler.poll_count = 0
        AtlasHandler.last_payload = None
        AtlasHandler.download_authorization = None
        AtlasHandler.submit_error = False
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        os.environ["ATLASCLOUD_API_KEY"] = "test-key"
        self.addCleanup(os.environ.pop, "ATLASCLOUD_API_KEY", None)

    def test_text_generation_submits_once_and_downloads_valid_glb(self) -> None:
        out = Path(self.temp.name) / "text"
        result = atlas.main(
            [
                "text",
                "--prompt",
                "game-ready hover bike",
                "--model",
                "test/text-to-3d",
                "--format",
                "GLB",
                "--pbr",
                "--wait",
                "--download",
                "--interval",
                "0",
                "--api-base",
                self.base_url,
                "--out-dir",
                str(out),
            ]
        )
        self.assertEqual(result, 0)
        self.assertEqual(AtlasHandler.post_count, 1)
        self.assertEqual(AtlasHandler.last_payload["model"], "test/text-to-3d")
        self.assertTrue((out / "outputs/model.glb").is_file())
        self.assertIsNone(AtlasHandler.download_authorization)
        job = json.loads((out / "job.json").read_text())
        self.assertNotIn("test-key", json.dumps(job))

    def test_resume_never_submits_another_generation(self) -> None:
        job = Path(self.temp.name) / "job.json"
        job.write_text(
            json.dumps(
                {
                    "api_base": self.base_url,
                    "model": "test/text-to-3d",
                    "prediction_id": "pred-1",
                    "poll_path": "/api/v1/model/prediction/{request_id}",
                }
            )
        )
        result = atlas.main(["resume", "--job", str(job), "--wait", "--interval", "0"])
        self.assertEqual(result, 0)
        self.assertEqual(AtlasHandler.post_count, 0)
        self.assertGreaterEqual(AtlasHandler.poll_count, 2)

    def test_local_image_uploads_once_and_uses_schema_field(self) -> None:
        image = Path(self.temp.name) / "source.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n")
        result = atlas.main(
            [
                "image",
                "--image",
                str(image),
                "--model",
                "test/image-to-3d",
                "--api-base",
                self.base_url,
                "--out-dir",
                str(Path(self.temp.name) / "image"),
            ]
        )
        self.assertEqual(result, 0)
        self.assertEqual(AtlasHandler.upload_count, 1)
        self.assertEqual(AtlasHandler.post_count, 1)
        self.assertEqual(
            AtlasHandler.last_payload["image_url"], f"{self.base_url}/files/source.png"
        )

    def test_unknown_model_parameter_stops_before_billable_post(self) -> None:
        result = atlas.main(
            [
                "text",
                "--prompt",
                "asset",
                "--model",
                "test/text-to-3d",
                "--param",
                "not_supported=true",
                "--api-base",
                self.base_url,
                "--out-dir",
                str(Path(self.temp.name) / "invalid"),
            ]
        )
        self.assertEqual(result, 1)
        self.assertEqual(AtlasHandler.post_count, 0)

    def test_non_https_remote_url_is_rejected(self) -> None:
        with self.assertRaises(atlas.AtlasError):
            atlas.validate_url("http://example.com/model.glb", allow_loopback_http=True)

    def test_billable_post_is_not_retried_after_server_error(self) -> None:
        AtlasHandler.submit_error = True
        result = atlas.main(
            [
                "text",
                "--prompt",
                "asset",
                "--model",
                "test/text-to-3d",
                "--api-base",
                self.base_url,
                "--out-dir",
                str(Path(self.temp.name) / "server-error"),
            ]
        )
        self.assertEqual(result, 1)
        self.assertEqual(AtlasHandler.post_count, 1)

    def test_data_uri_is_rejected_for_url_only_model(self) -> None:
        result = atlas.main(
            [
                "image",
                "--image",
                "data:image/png;base64,iVBORw0KGgo=",
                "--model",
                "test/image-to-3d",
                "--api-base",
                self.base_url,
                "--out-dir",
                str(Path(self.temp.name) / "data-uri"),
            ]
        )
        self.assertEqual(result, 1)
        self.assertEqual(AtlasHandler.post_count, 0)


if __name__ == "__main__":
    unittest.main()
