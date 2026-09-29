"""Offline CLI recovery tests; every provider request is intercepted by FakeMeshy."""

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


SCRIPT = Path(__file__).resolve().parents[2] / "skills/threejs-3d-generator-meshy/scripts/meshy_3d_asset.py"
SPEC = importlib.util.spec_from_file_location("meshy_jobs", SCRIPT)
meshy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(meshy)

HUMANOID = ["mixamorig:Hips", "mixamorig:Spine", "mixamorig:Spine1", "mixamorig:Spine2",
            "mixamorig:Neck", "mixamorig:Head", "mixamorig:HeadTop_End"]
HUMANOID += [f"mixamorig:{side}{bone}" for side in ("Left", "Right")
             for bone in ("Shoulder", "Arm", "ForeArm", "Hand", "UpLeg", "Leg", "Foot", "ToeBase")]


def glb(nodes=None):
    document = {"asset": {"version": "2.0"}, "nodes": [{"name": name} for name in (nodes or HUMANOID)]}
    payload = json.dumps(document).encode()
    payload += b" " * (-len(payload) % 4)
    return b"glTF" + struct.pack("<II", 2, 20 + len(payload)) + struct.pack("<II", len(payload), 0x4E4F534A) + payload


def http_error(status, body=None, retry_after=None):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return error.HTTPError("https://api.meshy.ai/openapi/v2/text-to-3d", status, "test failure", headers,
                           io.BytesIO(json.dumps(body or {"message": "test failure"}).encode()))


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


class FakeMeshy:
    """Meshy's task API: POST returns an id, GET returns the task, assets live off-domain."""

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

    def close(self):
        for queue in [self.post_events, *self.status_events.values(), *self.download_events.values()]:
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

    def kind_of(self, url, method):
        for kind, path in meshy.ENDPOINTS.items():
            full = f"{meshy.BASE_URL}{path}"
            if (method == "POST" and url == full) or (method == "GET" and url.startswith(full + "/")):
                return kind
        return None

    def __call__(self, req, timeout):
        url = req.full_url
        method = req.get_method()
        kind = self.kind_of(url, method)
        if method == "POST" and kind:
            payload = json.loads(req.data)
            if self.before_post is not None:
                self.before_post(payload)
            self.posts.append({"kind": kind, **payload})
            task_id = f"task-{len(self.posts)}"
            task = {"id": task_id, "status": "SUCCEEDED", "progress": 100, "consumed_credits": 5,
                    "model_urls": {"glb": self.output(task_id, "model", "glb", glb())},
                    "thumbnail_url": self.output(task_id, "thumb", "png", b"PNG preview")}
            for key in ("preview_task_id", "input_task_id", "rig_task_id", "motion_task_id", "action_id"):
                if key in payload:
                    task[key] = payload[key]
            self.tasks[task_id] = task
            event = self.event(self.post_events)
            return Response(event if event is not None else {"result": task_id})
        if method == "GET" and kind:
            task_id = parse.unquote(url.rsplit("/", 1)[-1])
            self.status_reads.append(task_id)
            event = self.event(self.status_events.get(task_id))
            task = copy.deepcopy(event if event is not None else self.tasks[task_id])
            # Rigging answers with an envelope around the task; the client unwraps it.
            return Response({"result": task} if kind == "rig" else task)
        if method == "GET" and url.startswith("https://assets.test/"):
            self.download_reads.append(url)
            self.event(self.download_events.get(url))
            return Response(self.assets[url], "application/octet-stream")
        raise AssertionError(f"Unexpected network request: {method} {url}")


class MeshyJobTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix="meshy-jobs-")))
        self.checkpoint = self.root / "job.json"
        self.provider = FakeMeshy()
        self.addCleanup(self.provider.close)
        self.stack.enter_context(mock.patch.object(meshy.request, "urlopen", side_effect=self.provider))
        self.sleeps = self.stack.enter_context(mock.patch.object(meshy.time, "sleep"))
        self.stack.enter_context(mock.patch.dict(os.environ, {"MESHY_API_KEY": "private-api-key"}))
        self.stack.enter_context(redirect_stdout(io.StringIO()))
        self.stack.enter_context(redirect_stderr(io.StringIO()))

    JOB_COMMANDS = {"text", "refine", "image", "multi-image", "retexture", "remesh", "rig",
                    "animate", "motion", "character-pipeline"}

    def run_job(self, *argv):
        cli = list(argv)
        if argv[0] in self.JOB_COMMANDS:
            cli.extend(["--out-dir", str(self.root / "outputs"), "--interval", "0"])
        args = meshy.build_parser().parse_args(cli)
        args.func(args)

    def saved(self, path=None):
        return json.loads((path or self.checkpoint).read_text())

    def text_job(self, *extra):
        self.run_job("text", "--prompt", "paladin", "--checkpoint", str(self.checkpoint), *extra)

    def pipeline(self, *extra):
        self.run_job("character-pipeline", "--prompt", "paladin", "--name", "character",
                     "--animations", "idle,walking", "--checkpoint", str(self.checkpoint), *extra)

    def resume(self, *extra):
        self.run_job("resume", str(self.checkpoint), *extra)

    def posts_of(self, kind):
        return [post for post in self.provider.posts if post["kind"] == kind]

    def test_accepted_task_interruption_resumes_without_generation(self):
        self.provider.status_events["task-1"] = [KeyboardInterrupt()]
        with self.assertRaises(KeyboardInterrupt):
            self.text_job("--wait", "--download")
        self.assertEqual(self.saved()["stages"]["preview"]["task_id"], "task-1")
        self.resume()
        stages = self.saved()["stages"]
        self.assertEqual(stages["preview"]["state"], "SUCCEEDED")
        self.assertEqual(stages["refine"]["state"], "SUCCEEDED")
        self.assertTrue(stages["refine"]["downloads_complete"])
        self.assertEqual(len(stages["refine"]["files"]), 2)
        self.assertEqual(len(self.provider.posts), 2)

    def test_accepted_id_is_saved_before_it_is_printed(self):
        def interrupted_print(*parts, **kwargs):
            if parts and str(parts[0]).endswith("task-1"):
                self.assertEqual(self.saved()["stages"]["preview"]["task_id"], "task-1")
                raise KeyboardInterrupt()
        with mock.patch("builtins.print", side_effect=interrupted_print), self.assertRaises(KeyboardInterrupt):
            self.text_job()
        self.resume()
        self.assertEqual(len(self.posts_of("text")), 2)

    def test_unknown_post_records_intent_and_never_blindly_reposts(self):
        def inspect_intent(_payload):
            self.provider.before_post = None
            stage = self.saved()["stages"]["preview"]
            self.assertEqual(stage["state"], "submitting")
            self.assertEqual(stage["request"]["kind"], "text")
            self.assertNotIn("task_id", stage)
        self.provider.before_post = inspect_intent
        self.provider.post_events = [error.URLError("connection closed after acceptance")]
        with self.assertRaises(meshy.MeshyError) as failed:
            self.text_job()
        self.assertEqual(failed.exception.category, "unknown_submission")
        with self.assertRaises(meshy.MeshyError) as blocked:
            self.resume()
        self.assertEqual(blocked.exception.category, "unknown_submission")
        self.assertEqual(len(self.provider.posts), 1)
        self.resume("--task-id", "task-1")
        self.assertEqual(self.saved()["stages"]["preview"]["task_id"], "task-1")
        self.assertEqual(len(self.posts_of("text")), 2)

    def test_interrupted_post_and_missing_response_id_are_uncertain(self):
        for index, event in enumerate((KeyboardInterrupt(), {"result": None}, {}, b"invalid JSON")):
            with self.subTest(event=index):
                path = self.root / f"uncertain-{index}.json"
                self.provider.post_events = [event]
                with self.assertRaises((KeyboardInterrupt, meshy.MeshyError)):
                    self.run_job("text", "--prompt", "paladin", "--checkpoint", str(path))
                self.assertEqual(self.saved(path)["stages"]["preview"]["state"], "unknown_submission")
                previous = len(self.provider.posts)
                with self.assertRaises(meshy.MeshyError):
                    self.run_job("resume", str(path))
                self.assertEqual(len(self.provider.posts), previous)

    def test_reconciliation_rejects_a_task_from_another_parent(self):
        self.provider.post_events = [{"result": "task-1"}, error.URLError("lost")]
        with self.assertRaises(meshy.MeshyError):
            self.text_job("--wait")
        self.assertEqual(self.saved()["stages"]["refine"]["state"], "unknown_submission")
        self.provider.tasks["other-task"] = {"id": "other-task", "status": "SUCCEEDED",
                                             "preview_task_id": "someone-elses-preview"}
        with self.assertRaises(meshy.MeshyError):
            self.resume("--task-id", "other-task")
        self.assertNotIn("task_id", self.saved()["stages"]["refine"])

    def test_existing_checkpoint_refuses_a_second_submission(self):
        self.text_job()
        with self.assertRaises(meshy.MeshyError) as refused:
            self.text_job()
        self.assertEqual(refused.exception.category, "checkpoint_error")
        self.assertEqual(len(self.provider.posts), 1)

    def test_concurrent_checkpoint_writer_is_rejected(self):
        self.text_job()
        with meshy.checkpoint_file(self.checkpoint):
            with self.assertRaises(meshy.MeshyError) as busy:
                self.resume()
        self.assertEqual(busy.exception.category, "checkpoint_error")

    def test_unusable_checkpoint_paths_are_classified(self):
        missing = self.root / "never-written.json"
        with self.assertRaises(meshy.MeshyError) as absent:
            self.run_job("resume", str(missing))
        self.assertEqual(absent.exception.category, "checkpoint_error")
        self.assertFalse(Path(f"{missing}.lock").exists())

        unwritable = self.root / "read-only"
        unwritable.mkdir()
        unwritable.chmod(0o500)
        self.addCleanup(unwritable.chmod, 0o700)
        with self.assertRaises(meshy.MeshyError) as denied:
            self.run_job("text", "--prompt", "paladin", "--checkpoint", str(unwritable / "job.json"))
        self.assertEqual(denied.exception.category, "checkpoint_error")
        self.assertEqual(self.provider.posts, [])

    def test_malformed_checkpoints_fail_before_any_provider_call(self):
        self.text_job()
        reads = len(self.provider.status_reads)
        damaged = [
            {"version": 2},
            {"command": "nonsense"},
            {"args": {"prompt": None}},
            {"args": {"interval": "soon"}},
            {"args": {"target_polycount": "20000"}},
            {"stages": {"unknown-stage": {"state": "submitted", "task_id": "task-1", "files": {}}}},
            {"stages": {"preview": {"state": "submitted", "files": {}}}},
            {"stages": {"preview": {"state": "submitted", "task_id": "task-1", "files": {},
                                    "task": {"id": "task-9", "status": "SUCCEEDED"}}}},
            {"stages": {"preview": {"state": "invented", "task_id": "task-1", "files": {}}}},
        ]
        for index, patch in enumerate(damaged):
            with self.subTest(case=index):
                data = self.saved()
                for key, value in patch.items():
                    if key in {"args", "stages"} and isinstance(value, dict):
                        data[key].update(value)
                    else:
                        data[key] = value
                path = self.root / f"damaged-{index}.json"
                path.write_text(json.dumps(data))
                with self.assertRaises(meshy.MeshyError) as invalid:
                    self.run_job("resume", str(path))
                self.assertEqual(invalid.exception.category, "checkpoint_error")
        self.assertEqual(len(self.provider.status_reads), reads)

    def test_checkpoint_keeps_local_paths_and_no_secrets(self):
        source = self.root / "concept.png"
        source.write_bytes(b"PNG concept")
        self.run_job("image", "--image", str(source), "--checkpoint", str(self.checkpoint), "--wait")
        body = self.checkpoint.read_text()
        self.assertEqual(self.saved()["args"]["image"], str(source.resolve()))
        self.assertNotIn("private-api-key", body)
        self.assertNotIn("data:image", body)
        self.assertNotIn("Signature=private-download-signature", body)

    def test_accepted_remote_image_task_resumes_without_the_source(self):
        remote = self.root / "accepted.json"
        self.provider.status_events["task-1"] = [KeyboardInterrupt()]
        with self.assertRaises(KeyboardInterrupt):
            self.run_job("image", "--image", "https://images.test/hero.png",
                         "--checkpoint", str(remote), "--wait", "--download")
        self.assertIsNone(self.saved(remote)["args"]["image"])
        self.run_job("resume", str(remote))
        stage = self.saved(remote)["stages"]["model"]
        self.assertEqual(stage["state"], "SUCCEEDED")
        self.assertTrue(stage["downloads_complete"])
        self.assertEqual(len(self.provider.posts), 1)

    def test_remote_image_source_must_be_resupplied_on_resume(self):
        remote = self.root / "remote.json"
        self.provider.post_events = [error.URLError("lost")]
        with self.assertRaises(meshy.MeshyError):
            self.run_job("image", "--image", "https://images.test/hero.png", "--checkpoint", str(remote))
        self.assertIsNone(self.saved(remote)["args"]["image"])
        local = self.root / "hero.png"
        local.write_bytes(b"PNG hero")
        self.run_job("resume", str(remote), "--task-id", "task-1", "--image", str(local))
        self.assertEqual(self.saved(remote)["stages"]["model"]["task_id"], "task-1")
        self.assertEqual(len(self.provider.posts), 1)

    def test_completed_downloads_are_reused_and_repaired(self):
        self.text_job("--wait", "--download")
        reads = len(self.provider.download_reads)
        self.resume()
        self.assertEqual(len(self.provider.download_reads), reads)
        files = [Path(record["path"]) for record in self.saved()["stages"]["refine"]["files"].values()]
        files[0].write_bytes(b"corrupted")
        self.resume()
        self.assertGreater(len(self.provider.download_reads), reads)
        self.assertTrue(all(meshy.file_matches(record)
                            for record in self.saved()["stages"]["refine"]["files"].values()))
        self.assertEqual(len(self.provider.posts), 2)

    def test_expired_download_link_is_refreshed_from_the_task(self):
        self.text_job("--wait")
        url = self.provider.tasks["task-2"]["model_urls"]["glb"]
        self.provider.download_events[url] = [http_error(403)]
        with self.assertRaises(meshy.MeshyError) as expired:
            self.resume()
        self.assertEqual(expired.exception.category, "expired_download")
        self.resume()
        self.assertTrue(self.saved()["stages"]["refine"]["downloads_complete"])
        self.assertEqual(len(self.provider.posts), 2)

    def test_status_reads_retry_transient_failures_but_posts_do_not(self):
        self.provider.status_events["task-1"] = [http_error(503, retry_after=5), http_error(429)]
        self.text_job("--wait")
        self.assertEqual(len(self.posts_of("text")), 2)
        self.sleeps.assert_any_call(5)

        self.provider.post_events = [http_error(500)]
        with self.assertRaises(meshy.MeshyError) as uncertain:
            self.run_job("text", "--prompt", "second", "--checkpoint", str(self.root / "second.json"))
        self.assertEqual(uncertain.exception.category, "unknown_submission")
        self.assertEqual(len(self.posts_of("text")), 3)

    def test_credentials_credits_and_invalid_input_are_distinct(self):
        cases = ((401, {}, "credentials"), (402, {}, "exhausted_credits"),
                 (400, {"message": "invalid pose_mode"}, "invalid_input"),
                 (403, {"message": "insufficient credits"}, "exhausted_credits"))
        for index, (status, body, category) in enumerate(cases):
            with self.subTest(status=status):
                self.provider.post_events = [http_error(status, body)]
                path = self.root / f"classified-{index}.json"
                with self.assertRaises(meshy.MeshyError) as failure:
                    self.run_job("text", "--prompt", "paladin", "--checkpoint", str(path))
                self.assertEqual(failure.exception.category, category)
                self.assertEqual(self.saved(path)["stages"]["preview"]["state"], "rejected")

    def test_failed_task_is_reported_and_not_resubmitted(self):
        self.provider.status_events["task-1"] = [
            {"id": "task-1", "status": "FAILED", "task_error": {"message": "generation failed"}}]
        with self.assertRaises(meshy.MeshyError) as failed:
            self.text_job("--wait")
        self.assertEqual(failed.exception.category, "task_failed")
        self.assertEqual(self.saved()["stages"]["preview"]["state"], "FAILED")
        with self.assertRaises(meshy.MeshyError):
            self.resume()
        self.assertEqual(len(self.provider.posts), 1)

    def test_missing_api_key_is_reported_before_any_request(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(meshy.MeshyError) as missing:
                self.text_job()
        self.assertEqual(missing.exception.category, "missing_credentials")
        self.assertEqual(self.provider.posts, [])

    def test_probe_prints_the_credential_contract_line(self):
        for environment, expected in (({"MESHY_API_KEY": "private-api-key"}, "SET"), ({}, "MISSING")):
            with self.subTest(expected=expected):
                stream = io.StringIO()
                with mock.patch.dict(os.environ, environment, clear=True), redirect_stdout(stream):
                    self.run_job("probe")
                self.assertEqual(f"MESHY_API_KEY={expected}", stream.getvalue().strip())

    def test_pipeline_stops_for_model_inspection_then_resumes_through_clips(self):
        self.pipeline("--stop-after", "model")
        self.assertEqual({"preview", "refine"}, set(self.saved()["stages"]))
        self.resume()
        stages = self.saved()["stages"]
        self.assertEqual({"preview", "refine", "rig", "animation-1", "animation-2"}, set(stages))
        self.assertEqual(len(self.posts_of("text")), 2)
        self.assertEqual(len(self.posts_of("rig")), 1)
        self.assertEqual([post["action_id"] for post in self.posts_of("animate")], [0, 1])
        self.assertTrue(all(stage["state"] == "SUCCEEDED" for stage in stages.values()))

    def test_pipeline_reuses_every_accepted_stage_after_an_interruption(self):
        self.provider.status_events["task-5"] = [KeyboardInterrupt()]
        with self.assertRaises(KeyboardInterrupt):
            self.pipeline()
        accepted = {name: stage["task_id"] for name, stage in self.saved()["stages"].items()}
        self.assertEqual(5, len(accepted))
        self.resume()
        self.assertEqual(accepted, {name: stage["task_id"] for name, stage in self.saved()["stages"].items()})
        self.assertEqual(len(self.provider.posts), 5)

    def test_pipeline_remeshes_a_too_dense_mesh_before_rigging(self):
        def reject_first_rig(payload):
            if payload.get("input_task_id") == "task-2" and "target_polycount" not in payload:
                raise http_error(400, {"message": "model exceeds the 300000 face limit"})
        self.provider.before_post = reject_first_rig
        self.pipeline("--animations", "idle")
        stages = self.saved()["stages"]
        self.assertEqual(stages["rig"]["state"], "rejected")
        self.assertEqual(stages["remesh"]["state"], "SUCCEEDED")
        self.assertEqual(stages["rig-remeshed"]["state"], "SUCCEEDED")
        self.assertEqual(self.posts_of("remesh")[0]["target_polycount"], 30000)

    def test_single_job_resume_never_grows_into_a_pipeline(self):
        self.text_job("--wait")
        with self.assertRaises(meshy.MeshyError):
            self.resume("--stop-after", "rig")
        self.assertEqual(self.posts_of("rig"), [])

    def test_job_without_checkpoint_still_runs_to_completion(self):
        self.run_job("text", "--prompt", "paladin", "--wait", "--download")
        self.assertEqual(len(self.posts_of("text")), 2)
        self.assertFalse(self.checkpoint.exists())


if __name__ == "__main__":
    unittest.main()
