"""Installed resources work without repository-root helpers or configuration."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
NAMES = {
    "threejs-game-director", "threejs-gameplay-systems", "threejs-aaa-graphics-builder",
    "threejs-game-ui-designer", "threejs-debug-profiler", "threejs-qa-release",
    "threejs-3d-generator", "threejs-image-generator", "threejs-audio-generator",
}
NOISE = {".DS_Store", "__pycache__", "node_modules", "dist", "artifacts", "test-results"}


class PackagingTests(unittest.TestCase):
    def test_nine_skill_package_and_required_resources(self):
        self.assertEqual(NAMES, {entry.parent.name for entry in SKILLS.glob("*/SKILL.md")})
        for relative in (
            "threejs-gameplay-systems/assets/threejs-vite-game/package.json",
            "threejs-gameplay-systems/scripts/create_threejs_game.py",
            "threejs-qa-release/scripts/inspect-threejs-canvas.mjs",
            "threejs-game-director/references/asset-recovery.md",
            "threejs-game-director/references/evidence-manifest.md",
            "threejs-game-director/references/workflow-evaluations.md",
        ):
            with self.subTest(path=relative):
                self.assertTrue((SKILLS / relative).is_file())

    def test_no_generated_noise_in_package(self):
        self.assertEqual([], [str(path.relative_to(SKILLS)) for path in SKILLS.rglob("*") if path.name in NOISE])

    def test_installed_scaffold_creator_is_self_contained(self):
        with tempfile.TemporaryDirectory(prefix="threejs-package-") as directory:
            temp = Path(directory)
            installed = temp / "installed/threejs-gameplay-systems"
            shutil.copytree(SKILLS / installed.name, installed)
            game = temp / "My Game"
            process = subprocess.run([
                sys.executable, "-B", str(installed / "scripts/create_threejs_game.py"), str(game),
            ], cwd=temp, text=True, capture_output=True)
            self.assertEqual(0, process.returncode, process.stdout + process.stderr)
            self.assertEqual("my-game", json.loads((game / "package.json").read_text())["name"])
            self.assertEqual(
                (SKILLS / "threejs-qa-release/scripts/inspect-threejs-canvas.mjs").read_bytes(),
                (game / "scripts/inspect-threejs-canvas.mjs").read_bytes(),
            )
            self.assertTrue((game / "tests/visual-regression.template.ts").is_file())
            self.assertTrue((game / "src/vite-env.d.ts").is_file())

    def test_installed_helper_clis_do_not_need_repo_root(self):
        with tempfile.TemporaryDirectory(prefix="threejs-cli-") as directory:
            temp = Path(directory)
            for name, executable, relative in (
                ("threejs-game-director", sys.executable, "scripts/check_evidence.py"),
                ("threejs-3d-generator", sys.executable, "scripts/threejs_3d_asset.py"),
                ("threejs-qa-release", "node", "scripts/inspect-threejs-canvas.mjs"),
            ):
                with self.subTest(skill=name):
                    installed = temp / name
                    shutil.copytree(SKILLS / name, installed)
                    process = subprocess.run([executable, str(installed / relative), "--help"],
                                             cwd=temp, text=True, capture_output=True)
                    self.assertEqual(0, process.returncode, process.stdout + process.stderr)
                    self.assertIn("usage", process.stdout.lower())


if __name__ == "__main__":
    unittest.main()
