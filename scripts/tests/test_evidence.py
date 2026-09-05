"""Filesystem and CLI checks for the packaged evidence verifier."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "skills/threejs-game-director/scripts/check_evidence.py"
SPEC = importlib.util.spec_from_file_location("check_evidence", SCRIPT)
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="threejs-evidence-")
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.manifest_path = self.project / "artifacts/evidence.json"

    def write_json(self, path, data):
        target = self.project / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data), encoding="utf-8")
        return target

    def capture(self, mode="desktop", state="active-play", run_id="run-123", **overrides):
        stem = f"{mode}-{state or 'default'}"
        screenshot = self.project / f"artifacts/{stem}.png"
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        # Content is immaterial to this file-existence check; pixels are tested by the inspector.
        screenshot.write_bytes(b"screenshot fixture" * 100)
        data = {"runId": run_id, "mode": mode, "state": state,
                "requestedState": state, "appliedState": state,
                "screenshotPath": str(screenshot), "result": {"ok": True},
                "consoleErrors": [], "pageErrors": []}
        data.update(overrides)
        path = f"artifacts/{stem}.json"
        self.write_json(path, data)
        return {"mode": mode, "state": state, "report": path}

    def verify(self, captures, **overrides):
        manifest = {"version": 1, "runId": "run-123", "captures": captures}
        manifest.update(overrides)
        self.write_json("artifacts/evidence.json", manifest)
        return evidence.check_manifest(self.project, self.manifest_path)

    def test_current_run_desktop_and_mobile(self):
        ok, bad = self.verify([self.capture(), self.capture("mobile", "boss")])
        self.assertEqual([], bad)
        self.assertEqual(2, len(ok))

    def test_missing_declared_capture_fails(self):
        captures = [self.capture(), {"mode": "mobile", "state": "boss", "report": "artifacts/missing.json"}]
        self.assertTrue(self.verify(captures)[1])

    def test_unrelated_old_failed_and_malformed_reports_are_ignored(self):
        self.write_json("artifacts/old.json", {"screenshotPath": "gone.png", "result": {"ok": False}})
        (self.project / "artifacts/broken.json").write_text("not json")
        self.assertEqual([], self.verify([self.capture()])[1])

    def test_stale_declared_report_fails(self):
        self.assertTrue(self.verify([self.capture(run_id="yesterday")])[1])

    def test_legacy_report_cannot_establish_acknowledged_capture(self):
        capture = self.capture()
        path = self.project / capture["report"]
        data = json.loads(path.read_text())
        del data["appliedState"]
        path.write_text(json.dumps(data))
        self.assertTrue(self.verify([capture])[1])

    def test_wrong_applied_state_fails(self):
        self.assertTrue(self.verify([self.capture(state="boss", appliedState="active-play")])[1])

    def test_wrong_requested_state_fails(self):
        self.assertTrue(self.verify([self.capture(requestedState="unknown")])[1])

    def test_wrong_mode_fails(self):
        capture = self.capture()
        capture["mode"] = "mobile"
        self.assertTrue(self.verify([capture])[1])

    def test_null_state_is_explicit_and_supported(self):
        self.assertEqual([], self.verify([self.capture(state=None)])[1])

    def test_duplicate_capture_fails(self):
        capture = self.capture()
        self.assertTrue(self.verify([capture, capture])[1])

    def test_reused_report_cannot_fill_two_slots(self):
        capture = self.capture()
        second = {**capture, "mode": "mobile"}
        self.assertTrue(self.verify([capture, second])[1])

    def test_missing_screenshot_and_stub_screenshot_fail(self):
        capture = self.capture()
        shot = self.project / "artifacts/desktop-active-play.png"
        shot.unlink()
        self.assertTrue(self.verify([capture])[1])
        shot.write_bytes(b"")
        self.assertTrue(self.verify([capture])[1])

    def test_missing_screenshot_field_fails(self):
        self.assertTrue(self.verify([self.capture(screenshotPath=None)])[1])

    def test_errors_and_blank_pixels_fail(self):
        for overrides in ({"consoleErrors": ["asset failed"]}, {"pageErrors": ["boom"]},
                          {"result": {"ok": False}}, {"result": {"ok": "true"}}, {"result": []}):
            with self.subTest(overrides=overrides):
                self.assertTrue(self.verify([self.capture(**overrides)])[1])

    def test_malformed_report_fails_cleanly(self):
        capture = self.capture()
        (self.project / capture["report"]).write_text("[]")
        self.assertTrue(self.verify([capture])[1])

    def test_invalid_manifests_fail(self):
        for patch in ({"version": True}, {"version": 2}, {"runId": ""}, {"captures": []},
                      {"captures": [{}]}, {"captures": [None]}, {"artifacts": "file.png"}):
            with self.subTest(patch=patch):
                manifest = {"version": 1, "runId": "run-123", "captures": [self.capture()], **patch}
                self.write_json("artifacts/evidence.json", manifest)
                self.assertTrue(evidence.check_manifest(self.project, self.manifest_path)[1])

    def test_absolute_report_path_and_artifact_with_spaces(self):
        capture = self.capture()
        capture["report"] = str(self.project / capture["report"])
        path = self.project / "assets/hero model.glb"
        path.parent.mkdir()
        path.write_bytes(b"model fixture" * 100)
        ok, bad = self.verify([capture], artifacts=[str(path)])
        self.assertEqual([], bad)
        self.assertEqual(2, len(ok))

    def test_artifact_directory_is_not_a_file(self):
        path = self.project / "fake.png"
        path.mkdir()
        self.assertTrue(evidence.check_artifacts([str(path)], [self.project])[1])

    def test_manifest_does_not_resolve_files_from_unrelated_working_directory(self):
        with tempfile.TemporaryDirectory(prefix="unrelated-evidence-") as directory:
            outside = Path(directory)
            (outside / "outside.png").write_bytes(b"image fixture" * 100)
            (outside / "motion.webm").write_bytes(b"motion fixture" * 100)
            previous = Path.cwd()
            try:
                os.chdir(outside)
                capture = self.capture(screenshotPath="outside.png")
                self.assertTrue(self.verify([capture])[1])
                self.assertTrue(self.verify([self.capture()], artifacts=["motion.webm"])[1])
                self.assertEqual([], self.verify([self.capture()], artifacts=[str(outside / "motion.webm")])[1])
            finally:
                os.chdir(previous)

    def test_manifest_does_not_resolve_screenshots_relative_to_report_folder(self):
        capture = self.capture(screenshotPath="desktop-active-play.png")
        self.assertTrue(self.verify([capture])[1])

    def test_inline_commands_and_remote_urls_are_not_filenames(self):
        text = "Run `python3 check_evidence.py . --manifest artifacts/evidence.json`. "
        text += "Then `node scripts/inspect.mjs --out artifacts/capture.json`. "
        text += "`https://example.com/model.glb` is remote. Evidence: `assets/hero model.glb`."
        self.assertEqual(["assets/hero model.glb"], evidence.find_paths(text))

    def test_markdown_and_code_paths_preserve_spaces_and_absolute_roots(self):
        text = "[Shot](/tmp/My Game/artifacts/active play.png) "
        text += "![Other](<artifacts/pause (mobile).png>) `assets/hero model.glb` "
        text += "[Encoded](artifacts/shot%20two.png) [Remote](https://example.com/remote.png) "
        text += "`src/config.json` artifacts/regular.json"
        self.assertEqual([
            "/tmp/My Game/artifacts/active play.png", "artifacts/pause (mobile).png",
            "assets/hero model.glb", "artifacts/shot two.png", "artifacts/regular.json",
        ], evidence.find_paths(text))

    def test_basic_report_mode_is_backward_compatible(self):
        self.capture()
        self.write_json("data/metrics.json", {"frames": 120})
        report = self.project / "artifacts/report.md"
        report.write_text("[Shot](artifacts/desktop-active-play.png) `data/metrics.json`")
        process = subprocess.run([sys.executable, "-B", str(SCRIPT), str(self.project),
                                  "--report", str(report)], capture_output=True, text=True)
        self.assertEqual(0, process.returncode, process.stdout + process.stderr)
        self.assertIn("Legacy mode", process.stdout)

    def test_manifest_cli_does_not_scan_history(self):
        self.verify([self.capture()])
        self.write_json("old.json", {"screenshotPath": "gone.png", "result": {"ok": False}})
        process = subprocess.run([sys.executable, "-B", str(SCRIPT), str(self.project),
                                  "--manifest", "artifacts/evidence.json"], capture_output=True, text=True)
        self.assertEqual(0, process.returncode, process.stdout + process.stderr)

    def test_manifest_cannot_skip_inspector(self):
        process = subprocess.run([sys.executable, "-B", str(SCRIPT), str(self.project),
                                  "--manifest", "missing.json", "--skip-inspector"], capture_output=True, text=True)
        self.assertNotEqual(0, process.returncode)


if __name__ == "__main__":
    unittest.main()
