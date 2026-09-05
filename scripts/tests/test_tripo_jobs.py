"""Offline CLI recovery tests; every provider request is intercepted by FakeTripo."""

from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
from email.message import Message
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
from urllib import error, parse


SCRIPT = Path(__file__).resolve().parents[2] / "skills/threejs-3d-generator/scripts/threejs_3d_asset.py"
SPEC = importlib.util.spec_from_file_location("tripo_jobs", SCRIPT)
tripo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tripo)


def glb(nodes=None, document=None):
    if document is None:
        document = {"asset": {"version": "2.0"}, "nodes": nodes or []}
    payload = json.dumps(document).encode()
    payload += b" " * (-len(payload) % 4)
    return b"glTF" + struct.pack("<II", 2, 20 + len(payload)) + struct.pack("<II", len(payload), 0x4E4F534A) + payload


def legacy_rig():
    return glb([{"name": side + part} for side in ("L_", "R_") for part in tripo.LEGACY_BIPED_PAIRED_BONES])


def creature_rig():
    return glb([{"name": f"tripo::{row}_{side}_Limb_{depth}"} for row in range(2) for side in ("Left", "Right") for depth in range(4)])


def http_error(status, code=None, retry_after=None):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return error.HTTPError("https://api.tripo3d.ai/task", status, "test failure", headers,
                           io.BytesIO(json.dumps({"code": code}).encode()))


class Response:
    def __init__(self, data, content_type="application/json"):
        self.data = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.data


class FakeTripo:
    def __init__(self):
        self.posts = []
        self.tasks = {}
        self.assets = {}
        self.status_reads = []
        self.download_reads = []
        self.status_events = {}
        self.download_events = {}
        self.post_events = []
        self.before_post = None
        self.upload_count = 0
        self.rig_count = 0
        self.bad_rigs = 0
        self.missing_rigs = False
        self.malformed_rigs = False
        self.rig_type = "biped"

    def close(self):
        queues = [self.post_events, *self.status_events.values(), *self.download_events.values()]
        for queue in queues:
            for event in queue:
                if isinstance(event, error.HTTPError):
                    event.close()

    def output(self, task_id, key, ext, content):
        url = f"https://assets.test/{task_id}/{key}.{ext}?Signature=private-download-signature"
        self.assets[url] = content
        return url

    def event(self, events):
        if not events:
            return None
        value = events.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    def __call__(self, req, timeout):
        url = req.full_url
        if req.get_method() == "POST" and url.endswith("/upload/sts"):
            self.upload_count += 1
            return Response({"code": 0, "data": {"image_token": "private-upload-token"}})
        if req.get_method() == "POST" and url.endswith("/task"):
            payload = json.loads(req.data)
            if self.before_post is not None:
                self.before_post(payload)
            self.posts.append(payload)
            task_id = f"task-{len(self.posts)}"
            kind = payload["type"]
            if kind == "animate_prerigcheck":
                output = {"riggable": True, "rig_type": self.rig_type}
            elif kind == "animate_rig":
                self.rig_count += 1
                content = legacy_rig() if payload.get("model_version", "").startswith("v1.0") else creature_rig()
                if self.rig_count <= self.bad_rigs:
                    content = glb([{"name": "tripo::Head"}])
                if self.malformed_rigs:
                    content = b"glTF\0broken"
                output = {} if self.missing_rigs else {"model": self.output(task_id, "model", "glb", content)}
            elif kind == "animate_retarget":
                ext = payload.get("out_format", "glb")
                output = {"model": self.output(task_id, "model", ext, b"FBX test" if ext == "fbx" else glb())}
            else:
                output = {"model": self.output(task_id, "model", "glb", glb()),
                          "rendered_image": self.output(task_id, "preview", "png", b"PNG preview")}
            self.tasks[task_id] = {"task_id": task_id, "type": kind, "status": "success", "progress": 100, "output": output}
            if "original_model_task_id" in payload:
                self.tasks[task_id]["original_model_task_id"] = payload["original_model_task_id"]
            event = self.event(self.post_events)
            return Response(event if event is not None else {"code": 0, "data": {"task_id": task_id}})
        if req.get_method() == "GET" and url.startswith(tripo.BASE_URL + "/task/"):
            task_id = parse.unquote(url.rsplit("/", 1)[-1])
            self.status_reads.append(task_id)
            event = self.event(self.status_events.get(task_id))
            task = event if event is not None else self.tasks[task_id]
            return Response({"code": 0, "data": copy.deepcopy(task)})
        if req.get_method() == "GET" and url.startswith("https://assets.test/"):
            self.download_reads.append(url)
            self.event(self.download_events.get(url))
            return Response(self.assets[url], "application/octet-stream")
        raise AssertionError(f"Unexpected network request: {req.get_method()} {url}")


class TripoJobTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix="tripo-jobs-")))
        self.checkpoint = self.root / "job.json"
        self.provider = FakeTripo()
        self.addCleanup(self.provider.close)
        self.stack.enter_context(mock.patch.object(tripo.request, "urlopen", side_effect=self.provider))
        self.sleeps = self.stack.enter_context(mock.patch.object(tripo.time, "sleep"))
        self.stack.enter_context(mock.patch.dict(os.environ, {"TRIPO_API_KEY": "private-api-key"}))
        self.stack.enter_context(redirect_stdout(io.StringIO()))
        self.stack.enter_context(redirect_stderr(io.StringIO()))

    def run_job(self, *argv):
        command = argv[0]
        cli = list(argv)
        if command in {"text", "image", "postprocess", "character-pipeline"}:
            cli.extend(["--out-dir", str(self.root / "outputs"), "--interval", "0"])
        args = tripo.build_parser().parse_args(cli)
        args.func(args)

    def saved(self):
        return json.loads(self.checkpoint.read_text())

    def text_job(self, *extra):
        self.run_job("text", "--prompt", "paladin", "--checkpoint", str(self.checkpoint), *extra)

    def pipeline(self, *extra):
        self.run_job("character-pipeline", "--prompt", "paladin", "--animations", "preset:idle,preset:walk",
                     "--checkpoint", str(self.checkpoint), *extra)

    def resume(self, *extra):
        self.run_job("resume", str(self.checkpoint), *extra)

    def test_accepted_task_interruption_resumes_without_generation(self):
        self.provider.status_events["task-1"] = [KeyboardInterrupt()]
        with self.assertRaises(KeyboardInterrupt):
            self.text_job("--wait", "--download")
        self.assertEqual(self.saved()["stages"]["task"]["task_id"], "task-1")
        self.resume()
        stage = self.saved()["stages"]["task"]
        self.assertEqual(stage["state"], "success")
        self.assertTrue(stage["downloads_complete"])
        self.assertEqual(len(stage["files"]), 2)
        self.assertEqual(len(self.provider.posts), 1)

    def test_id_is_saved_before_printing_task_id(self):
        def interrupted_print(*parts, **kwargs):
            if parts == ("task-1",):
                self.assertEqual(self.saved()["stages"]["task"]["task_id"], "task-1")
                raise KeyboardInterrupt()
        with mock.patch("builtins.print", side_effect=interrupted_print), self.assertRaises(KeyboardInterrupt):
            self.text_job()
        self.resume()
        self.assertEqual(len(self.provider.posts), 1)

    def test_unknown_post_records_intent_and_never_blindly_reposts(self):
        def inspect_intent(_payload):
            stage = self.saved()["stages"]["task"]
            self.assertEqual(stage["state"], "submitting")
            self.assertEqual(stage["request"]["type"], "text_to_model")
            self.assertNotIn("task_id", stage)
        self.provider.before_post = inspect_intent
        self.provider.post_events = [error.URLError("connection closed after acceptance")]
        with self.assertRaises(tripo.TripoError) as failed:
            self.text_job()
        self.assertEqual(failed.exception.category, "unknown_submission")
        with self.assertRaises(tripo.TripoError) as blocked:
            self.resume()
        self.assertEqual(blocked.exception.category, "unknown_submission")
        self.assertEqual(len(self.provider.posts), 1)
        self.resume("--task-id", "task-1")
        self.assertEqual(len(self.provider.posts), 1)
        self.assertEqual(self.saved()["stages"]["task"]["task_id"], "task-1")

    def test_interrupted_post_and_missing_response_id_are_uncertain(self):
        for index, event in enumerate((KeyboardInterrupt(), {"code": 0, "data": {}}, {"code": None}, b"invalid JSON")):
            with self.subTest(event=index):
                path = self.root / f"uncertain-{index}.json"
                self.provider.post_events = [event]
                with self.assertRaises((KeyboardInterrupt, tripo.TripoError)):
                    self.run_job("text", "--prompt", "paladin", "--checkpoint", str(path))
                self.assertEqual(json.loads(path.read_text())["stages"]["task"]["state"], "unknown_submission")
                previous = len(self.provider.posts)
                with self.assertRaises(tripo.TripoError):
                    self.run_job("resume", str(path))
                self.assertEqual(len(self.provider.posts), previous)

    def test_reconciliation_rejects_wrong_task_type(self):
        self.provider.post_events = [error.URLError("lost")]
        with self.assertRaises(tripo.TripoError):
            self.text_job()
        self.provider.tasks["wrong-task"] = {"task_id": "wrong-task", "status": "success", "type": "animate_rig"}
        with self.assertRaisesRegex(tripo.TripoError, "does not match"):
            self.resume("--task-id", "wrong-task")
        self.assertNotIn("task_id", self.saved()["stages"]["task"])

    def test_existing_checkpoint_refuses_new_submission(self):
        self.text_job()
        with self.assertRaises(tripo.TripoError) as failed:
            self.text_job()
        self.assertEqual(failed.exception.category, "checkpoint_error")
        self.assertEqual(len(self.provider.posts), 1)

    def test_malformed_checkpoint_args_fail_before_provider_calls(self):
        self.text_job()
        original = self.saved()
        invalid_options = [None, {}, {**original["args"], "prompt": []},
                           {**original["args"], "interval": "8"}, {**original["args"], "wait": "yes"},
                           {**original["args"], "command": "image"}, {**original["args"], "out_dir": None}]
        for options in invalid_options:
            with self.subTest(options=options):
                document = {**original, "args": options}
                self.checkpoint.write_text(json.dumps(document))
                with self.assertRaises(tripo.TripoError) as failed:
                    self.resume()
                self.assertEqual(failed.exception.category, "checkpoint_error")
                self.assertEqual(len(self.provider.posts), 1)
                self.assertEqual(self.provider.status_reads, [])

    def test_malformed_checkpoint_stage_cannot_lose_an_accepted_task(self):
        self.text_job()
        original = self.saved()
        mutations = [
            {"task_id": None}, {"task_id": {}}, {"state": []}, {"files": []},
            {"files": {"model": {"path": [], "size": "8", "sha256": False}}},
            {"task": {"task_id": "task-1", "status": "success", "output": []}},
            {"request": {"type": "text_to_model", "original_model_task_id": []}},
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                document = copy.deepcopy(original)
                document["stages"]["task"].update(mutation)
                self.checkpoint.write_text(json.dumps(document))
                with self.assertRaises(tripo.TripoError) as failed:
                    self.resume()
                self.assertEqual(failed.exception.category, "checkpoint_error")
                self.assertEqual(len(self.provider.posts), 1)
                self.assertEqual(self.provider.status_reads, [])

    def test_malformed_pipeline_animation_args_cannot_submit_new_stages(self):
        self.pipeline("--stop-after", "model")
        document = self.saved()
        document["args"]["animations"] = None
        self.checkpoint.write_text(json.dumps(document))
        previous_gets = len(self.provider.status_reads)
        with self.assertRaises(tripo.TripoError) as failed:
            self.resume()
        self.assertEqual(failed.exception.category, "checkpoint_error")
        self.assertEqual(len(self.provider.posts), 1)
        self.assertEqual(len(self.provider.status_reads), previous_gets)

    def test_remote_image_resume_needs_no_url_and_checkpoint_has_no_secrets(self):
        self.run_job("image", "--image", "https://images.test/hero.png?Signature=private-input-signature",
                     "--api-key", "private-explicit-key", "--checkpoint", str(self.checkpoint))
        self.resume()
        checkpoint_text = self.checkpoint.read_text()
        for secret in ("private-input-signature", "private-download-signature", "private-api-key", "private-explicit-key", "https://"):
            self.assertNotIn(secret, checkpoint_text)
        self.assertIsNone(self.saved()["args"]["image"])
        self.assertEqual(self.provider.upload_count, 0)
        self.assertEqual(len(self.provider.posts), 1)

    def test_local_image_upload_is_not_repeated_on_resume(self):
        image_path = self.root / "hero.png"
        image_path.write_bytes(b"PNG test")
        self.run_job("image", "--image", str(image_path), "--checkpoint", str(self.checkpoint))
        image_path.unlink()
        self.resume()
        self.assertEqual(self.provider.upload_count, 1)
        self.assertNotIn("private-upload-token", self.checkpoint.read_text())

    def test_rejected_remote_image_needs_fresh_input_before_submission(self):
        self.provider.post_events = [http_error(403, 2010)]
        with self.assertRaises(tripo.TripoError):
            self.run_job("image", "--image", "https://images.test/hero.png?Signature=old", "--checkpoint", str(self.checkpoint))
        with self.assertRaisesRegex(tripo.TripoError, "Resume with --image"):
            self.resume()
        self.assertEqual(len(self.provider.posts), 1)
        self.resume("--image", "https://images.test/hero.png?Signature=new")
        self.assertEqual(len(self.provider.posts), 2)
        self.assertNotIn("Signature=", self.checkpoint.read_text())

    def test_single_image_never_implicitly_starts_rigging(self):
        self.run_job("image", "--image", "https://images.test/hero.png", "--checkpoint", str(self.checkpoint))
        with self.assertRaisesRegex(tripo.TripoError, "requires a character-pipeline"):
            self.resume("--stop-after", "rig")
        self.resume("--stop-after", "model")
        self.assertEqual([p["type"] for p in self.provider.posts], ["image_to_model"])

    def test_postprocess_resume_keeps_legacy_fbx_workaround(self):
        self.run_job("postprocess", "--type", "retarget", "--original-task-id", "existing-rig",
                     "--animation", "preset:biped:walk", "--checkpoint", str(self.checkpoint))
        self.resume()
        payload = self.provider.posts[0]
        self.assertEqual(payload["out_format"], "fbx")
        self.assertNotIn("model_version", payload)
        self.assertEqual(len(self.provider.posts), 1)

    def test_pipeline_stops_for_model_and_rig_inspection_then_resumes(self):
        self.pipeline("--stop-after", "model")
        self.assertEqual(len(self.provider.posts), 1)
        self.assertTrue(self.saved()["stages"]["model"]["downloads_complete"])
        self.resume("--stop-after", "rig")
        self.assertEqual(len(self.provider.posts), 3)
        self.assertEqual(self.saved()["stages"]["rig-1"]["rig_validation"], "valid")
        self.resume()
        self.assertEqual(len(self.provider.posts), 5)
        self.assertEqual(self.provider.posts[0]["model_version"], "v3.1-20260211")
        self.assertEqual(self.provider.posts[2]["model_version"], "v1.0-20240301")
        for payload in self.provider.posts[3:]:
            self.assertEqual(payload["original_model_task_id"], "task-3")
            self.assertEqual(payload["out_format"], "fbx")
            self.assertNotIn("model_version", payload)
            self.assertNotIn("animate_in_place", payload)
            self.assertEqual(len(payload["animations"]), 1)
            self.assertTrue(payload["animations"][0].startswith("preset:biped:"))
        previous_gets = len(self.provider.status_reads)
        previous_downloads = len(self.provider.download_reads)
        self.resume()
        self.assertEqual(len(self.provider.posts), 5)
        self.assertEqual(len(self.provider.status_reads), previous_gets)
        self.assertEqual(len(self.provider.download_reads), previous_downloads)

    def test_pipeline_partial_animation_completion_reuses_every_accepted_stage(self):
        self.provider.status_events["task-5"] = [KeyboardInterrupt()]
        with self.assertRaises(KeyboardInterrupt):
            self.pipeline()
        self.assertEqual(self.saved()["stages"]["animation-1"]["state"], "success")
        self.assertEqual(self.saved()["stages"]["animation-2"]["task_id"], "task-5")
        before_downloads = list(self.provider.download_reads)
        self.resume()
        self.assertEqual(len(self.provider.posts), 5)
        for url in before_downloads:
            self.assertEqual(self.provider.download_reads.count(url), 1)

    def test_pipeline_unknown_downstream_post_preserves_upstream_stages(self):
        self.provider.post_events = [None, None, error.URLError("rig accepted, response lost")]
        with self.assertRaises(tripo.TripoError):
            self.pipeline()
        with self.assertRaises(tripo.TripoError):
            self.resume()
        self.assertEqual(len(self.provider.posts), 3)
        self.resume("--task-id", "task-3", "--stop-after", "rig")
        self.assertEqual(len(self.provider.posts), 3)
        self.assertEqual(self.saved()["stages"]["rig-1"]["rig_validation"], "valid")

    def test_pipeline_reuses_external_model_task(self):
        self.run_job("image", "--image", "https://images.test/hero.png")
        self.run_job("character-pipeline", "--model-task-id", "task-1", "--animations", "",
                     "--checkpoint", str(self.checkpoint))
        self.resume()
        self.assertEqual([p["type"] for p in self.provider.posts], ["image_to_model", "animate_prerigcheck", "animate_rig"])

    def test_paid_rig_retry_budget_survives_interruption(self):
        self.provider.bad_rigs = 2
        self.provider.status_events["task-4"] = [KeyboardInterrupt()]
        with self.assertRaises(KeyboardInterrupt):
            self.pipeline("--animations", "")
        self.resume()
        self.assertEqual(self.provider.rig_count, 3)
        self.assertEqual(self.saved()["stages"]["rig-3"]["rig_validation"], "valid")
        self.resume()
        self.assertEqual(self.provider.rig_count, 3)

    def test_selected_rig_resume_ignores_cleaned_up_failed_attempts(self):
        self.provider.bad_rigs = 1
        self.pipeline()
        self.assertEqual(self.saved()["rig_stage"], "rig-2")
        for record in self.saved()["stages"]["rig-1"]["files"].values():
            Path(record["path"]).unlink()
        self.provider.tasks["task-3"]["status"] = "expired"
        old_reads = self.provider.status_reads.count("task-3")
        previous_posts = len(self.provider.posts)
        self.resume()
        self.assertEqual(self.provider.status_reads.count("task-3"), old_reads)
        self.assertEqual(len(self.provider.posts), previous_posts)

    def test_missing_rigs_fail_even_when_forced_and_do_not_reset_retry_budget(self):
        self.provider.missing_rigs = True
        with self.assertRaises(tripo.TripoError) as failed:
            self.pipeline("--force-rig")
        self.assertEqual(failed.exception.category, "invalid_artifact")
        self.assertEqual(self.provider.rig_count, 3)
        with self.assertRaises(tripo.TripoError):
            self.resume()
        self.assertEqual(self.provider.rig_count, 3)
        self.assertFalse(any(p["type"] == "animate_retarget" for p in self.provider.posts))

    def test_failed_prerigcheck_cannot_be_forced_into_paid_rigging(self):
        self.provider.status_events["task-2"] = [{"task_id": "task-2", "status": "failed", "error_code": 1001}]
        with self.assertRaises(tripo.TripoError) as failed:
            self.pipeline("--force-rig")
        self.assertEqual(failed.exception.category, "task_failed")
        self.assertEqual(self.provider.rig_count, 0)

    def test_credit_rejection_during_rigging_does_not_consume_automatic_retries(self):
        self.provider.post_events = [None, None, http_error(403, 2010)]
        with self.assertRaises(tripo.TripoError) as failed:
            self.pipeline("--animations", "")
        self.assertEqual(failed.exception.category, "exhausted_credits")
        self.assertEqual(len(self.provider.posts), 3)
        self.assertEqual(self.saved()["stages"]["rig-1"]["state"], "rejected")
        self.resume()
        self.assertEqual(len(self.provider.posts), 4)
        self.assertNotIn("rig-2", self.saved()["stages"])

    def test_malformed_rig_files_fail_before_retarget(self):
        self.provider.malformed_rigs = True
        with self.assertRaises(tripo.TripoError) as failed:
            self.pipeline("--force-rig", "--rig-retries", "0")
        self.assertEqual(failed.exception.category, "invalid_artifact")
        self.assertEqual(self.provider.rig_count, 1)
        self.assertFalse(any(p["type"] == "animate_retarget" for p in self.provider.posts))

    def test_degenerate_but_readable_rig_force_override_is_preserved(self):
        self.provider.bad_rigs = 1
        self.pipeline("--force-rig", "--rig-retries", "0")
        self.assertEqual(self.provider.rig_count, 1)
        self.assertEqual(self.saved()["stages"]["rig-1"]["rig_validation"], "invalid")
        self.assertEqual(len([p for p in self.provider.posts if p["type"] == "animate_retarget"]), 2)

    def test_creature_rig_version_and_root_motion_options_are_preserved(self):
        self.provider.rig_type = "quadruped"
        self.pipeline("--rig-type", "quadruped", "--animations", "preset:quadruped:walk", "--animate-in-place")
        self.assertEqual(self.provider.posts[2]["model_version"], "v2.5-20260210")
        retarget = self.provider.posts[3]
        self.assertEqual(retarget["model_version"], "v2.5-20260210")
        self.assertEqual(retarget["out_format"], "glb")
        self.assertTrue(retarget["animate_in_place"])

    def test_status_reads_retry_transient_errors_and_honor_retry_after(self):
        self.text_job()
        self.provider.status_events["task-1"] = [http_error(503), http_error(429, retry_after=7), error.URLError("temporary")]
        self.resume()
        self.assertEqual(self.sleeps.call_args_list, [mock.call(1), mock.call(7), mock.call(4)])
        self.assertEqual(len(self.provider.posts), 1)

    def test_status_retries_are_bounded_and_next_resume_keeps_id(self):
        self.text_job()
        self.provider.status_events["task-1"] = [http_error(503) for _ in range(tripo.GET_ATTEMPTS)]
        with self.assertRaises(tripo.TripoError) as failed:
            self.resume()
        self.assertEqual(failed.exception.category, "transient")
        self.assertEqual(len(self.provider.status_reads), 4)
        self.assertEqual(self.saved()["stages"]["task"]["task_id"], "task-1")
        self.resume()
        self.assertEqual(len(self.provider.posts), 1)

    def test_partial_download_recovery_reuses_files_and_refreshes_urls(self):
        self.text_job()
        task = self.provider.tasks["task-1"]
        old_url = task["output"]["rendered_image"]
        model_url = task["output"]["model"]
        self.provider.download_events[old_url] = [http_error(503) for _ in range(tripo.GET_ATTEMPTS)]
        with self.assertRaises(tripo.TripoError):
            self.resume()
        self.assertEqual(set(self.saved()["stages"]["task"]["files"]), {"model"})
        task["output"]["rendered_image"] = self.provider.output("task-1", "new-preview", "png", b"PNG refreshed")
        self.resume()
        self.assertEqual(self.provider.download_reads.count(model_url), 1)
        self.assertIn(task["output"]["rendered_image"], self.provider.download_reads)
        self.assertEqual(len(self.provider.posts), 1)

    def test_corrupted_completed_file_is_redownloaded_without_generation(self):
        self.text_job("--wait", "--download")
        record = self.saved()["stages"]["task"]["files"]["model"]
        Path(record["path"]).write_bytes(b"corrupted")
        self.resume()
        self.assertTrue(tripo.file_matches(self.saved()["stages"]["task"]["files"]["model"]))
        self.assertEqual(len(self.provider.posts), 1)

    def test_expired_download_is_not_misclassified_as_missing_api_credentials(self):
        self.text_job()
        task = self.provider.tasks["task-1"]
        old_url = task["output"]["model"]
        self.provider.download_events[old_url] = [http_error(403)]
        with self.assertRaises(tripo.TripoError) as failed:
            self.resume()
        self.assertEqual(failed.exception.category, "expired_download")
        task["output"]["model"] = self.provider.output("task-1", "refreshed-model", "glb", glb())
        self.resume()
        self.assertEqual(len(self.provider.posts), 1)

    def test_keyboard_interrupt_during_download_preserves_prior_files(self):
        self.text_job()
        urls = self.provider.tasks["task-1"]["output"]
        self.provider.download_events[urls["rendered_image"]] = [KeyboardInterrupt()]
        with self.assertRaises(KeyboardInterrupt):
            self.resume()
        self.resume()
        self.assertEqual(self.provider.download_reads.count(urls["model"]), 1)
        self.assertEqual(len(self.provider.posts), 1)

    def test_credentials_credits_and_invalid_input_are_distinct(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(tripo.TripoError) as missing:
                tripo.api_key_from(tripo.argparse.Namespace(api_key=None))
        self.assertEqual(missing.exception.category, "missing_credentials")
        for status, code, category in ((401, None, "credentials"), (403, 2010, "exhausted_credits"), (400, 2017, "invalid_input")):
            with self.subTest(status=status, code=code):
                self.provider.post_events = [http_error(status, code)]
                path = self.root / f"error-{status}.json"
                with self.assertRaises(tripo.TripoError) as failed:
                    self.run_job("text", "--prompt", "paladin", "--checkpoint", str(path))
                self.assertEqual(failed.exception.category, category)
                self.assertEqual(json.loads(path.read_text())["stages"]["task"]["state"], "rejected")
        self.assertEqual(self.sleeps.call_count, 0)

    def test_credit_rejection_can_resume_explicitly_after_top_up(self):
        self.provider.post_events = [http_error(403, 2010)]
        with self.assertRaises(tripo.TripoError):
            self.text_job()
        self.assertNotIn("task_id", self.saved()["stages"]["task"])
        self.assertEqual(len(self.provider.posts), 1)
        self.resume()
        self.assertEqual(len(self.provider.posts), 2)
        self.assertEqual(self.saved()["stages"]["task"]["task_id"], "task-2")

    def test_credit_error_in_http_200_response_is_classified(self):
        self.provider.post_events = [{"code": 2010, "message": "You don't have enough credit"}]
        with self.assertRaises(tripo.TripoError) as failed:
            self.text_job()
        self.assertEqual(failed.exception.category, "exhausted_credits")
        self.assertEqual(self.saved()["stages"]["task"]["state"], "rejected")

    def test_post_5xx_is_uncertain_without_retries(self):
        self.provider.post_events = [http_error(503)]
        with self.assertRaises(tripo.TripoError) as failed:
            self.text_job()
        self.assertEqual(failed.exception.category, "unknown_submission")
        self.assertEqual(len(self.provider.posts), 1)
        self.assertEqual(self.sleeps.call_count, 0)

    def test_post_429_is_rejected_without_automatic_retry(self):
        self.provider.post_events = [http_error(429, retry_after=1)]
        with self.assertRaises(tripo.TripoError) as failed:
            self.text_job()
        self.assertEqual(failed.exception.category, "transient")
        self.assertEqual(self.saved()["stages"]["task"]["state"], "rejected")
        self.assertEqual(self.sleeps.call_count, 0)
        self.resume()
        self.assertEqual(len(self.provider.posts), 2)

    def test_failed_model_is_not_resubmitted_on_resume(self):
        self.text_job()
        self.provider.tasks["task-1"].update(status="failed", error_code=1001)
        for _ in range(2):
            with self.assertRaises(tripo.TripoError) as failed:
                self.resume()
            self.assertEqual(failed.exception.category, "task_failed")
        self.assertEqual(len(self.provider.posts), 1)

    def test_missing_status_response_is_retried(self):
        self.text_job()
        self.provider.status_events["task-1"] = [{}]
        self.resume()
        self.sleeps.assert_called_once_with(1)

    def test_retry_after_http_date_and_cap(self):
        with mock.patch.object(tripo.time, "time", return_value=0):
            self.assertEqual(tripo.retry_after_seconds({"Retry-After": "Thu, 01 Jan 1970 00:00:08 GMT"}), 8)
        self.assertEqual(tripo.retry_after_seconds({"Retry-After": "99999"}), 60)
        self.assertIsNone(tripo.retry_after_seconds({"Retry-After": "invalid"}))

    def test_malformed_glb_variants_return_classified_errors(self):
        for index, content in enumerate((b"", b"glTF", glb()[:-1], b"glTF" + struct.pack("<II", 2, 24) + struct.pack("<II", 4, 0x4E4F534A) + b"{bad")):
            path = self.root / f"bad-{index}.glb"
            path.write_bytes(content)
            with self.assertRaises(tripo.TripoError) as failed:
                tripo.validate_rig_glb(path, "biped")
            self.assertEqual(failed.exception.category, "invalid_artifact")

    def test_malformed_glb_nodes_and_skins_return_invalid_artifact(self):
        node = {"name": "tripo::Head"}
        documents = [
            {"nodes": None}, {"nodes": {}}, {"nodes": [None]}, {"nodes": [{"name": []}]},
            {"nodes": [{"children": ["0"]}]}, {"nodes": [node], "skins": {}},
            {"nodes": [node], "skins": [None]}, {"nodes": [node], "skins": [{}]},
            {"nodes": [node], "skins": [{"joints": {}}]},
            {"nodes": [node], "skins": [{"joints": [None]}]},
            {"nodes": [node], "skins": [{"joints": [9]}]},
            {"nodes": [node], "skins": [{"joints": [0], "skeleton": {}}]},
            {"nodes": [node], "skins": [{"joints": [0], "inverseBindMatrices": []}]},
            {"nodes": [{"name": "Hip", "skin": 0}], "skins": []},
        ]
        for index, document in enumerate(documents):
            with self.subTest(document=document):
                path = self.root / f"bad-structure-{index}.glb"
                path.write_bytes(glb(document=document))
                with self.assertRaises(tripo.TripoError) as failed:
                    tripo.validate_rig_glb(path, "biped")
                self.assertEqual(failed.exception.category, "invalid_artifact")

    def test_http_error_responses_are_closed(self):
        response_error = http_error(403, 2010)
        self.provider.post_events = [response_error]
        with self.assertRaises(tripo.TripoError):
            self.text_job()
        self.assertTrue(response_error.closed)

    def test_second_checkpoint_writer_is_rejected(self):
        with tripo.checkpoint_file(self.checkpoint):
            with self.assertRaises(tripo.TripoError) as failed:
                self.text_job()
        self.assertEqual(failed.exception.category, "checkpoint_error")
        self.assertEqual(len(self.provider.posts), 0)

    def test_without_checkpoint_default_pipeline_still_runs_to_completion(self):
        self.run_job("character-pipeline", "--prompt", "paladin", "--animations", "preset:idle")
        self.assertEqual([p["type"] for p in self.provider.posts], ["text_to_model", "animate_prerigcheck", "animate_rig", "animate_retarget"])
        self.assertFalse(self.checkpoint.exists())


if __name__ == "__main__":
    unittest.main()
