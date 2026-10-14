"""End-to-end check of the asset queue in a throwaway copy of the repo layout (no git, no GPU).

Run: python3 -m unittest discover -s pipeline/tests
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(REPO / "pipeline", self.tmp / "pipeline",
                        ignore=shutil.ignore_patterns("tests", "__pycache__", "worker.toml"))
        for state in ("pending", "running", "done", "failed"):
            for f in (self.tmp / "pipeline" / "jobs" / state).glob("*.json"):
                f.unlink()
        (self.tmp / "pipeline" / "ledger.json").write_text('{"assets": []}\n')
        (self.tmp / "game" / "assets" / "concept").mkdir(parents=True)
        (self.tmp / "game" / "assets" / "generated").mkdir()
        (self.tmp / "game" / "assets" / "generated" / ".gitkeep").touch()
        (self.tmp / "game" / "assets" / "concept" / "ref.png").write_bytes(b"fake")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_cli(self, *args, ok=True):
        proc = subprocess.run([sys.executable, str(self.tmp / "pipeline" / "assets.py"), *args],
                              capture_output=True, text=True)
        if ok:
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc

    def test_mock_round_trip_and_ship_gate(self):
        self.run_cli("enqueue", "music", "theme", "--prompt", "chrome lullaby", "--param", "duration=90")
        self.run_cli("enqueue", "mesh", "crate", "--image", "game/assets/concept/ref.png")
        self.run_cli("enqueue", "pbr", "rust", "--image", "game/assets/concept/ref.png")
        self.run_cli("enqueue", "foley", "intro")
        self.run_cli("work", "--once", "--mock", "--no-git")

        gen = self.tmp / "game" / "assets" / "generated"
        self.assertTrue((gen / "music" / "theme.wav").stat().st_size > 1000)
        self.assertEqual((gen / "mesh" / "crate.glb").read_bytes()[:4], b"glTF")
        self.assertEqual(len(list((gen / "pbr" / "rust").glob("*.png"))), 5)
        self.assertEqual(len(list((self.tmp / "pipeline" / "jobs" / "done").glob("*.json"))), 4)
        self.assertEqual(list((self.tmp / "pipeline" / "jobs" / "pending").glob("*.json")), [])

        ledger = json.loads((self.tmp / "pipeline" / "ledger.json").read_text())
        self.assertEqual(len(ledger["assets"]), 8)
        self.assertTrue(all(e["placeholder"] for e in ledger["assets"]))

        self.assertEqual(self.run_cli("gate").returncode, 0)
        blocked = self.run_cli("gate", "--ship", ok=False)
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("PLACEHOLDER", blocked.stdout)

    def test_untracked_asset_blocks_ship(self):
        stray = self.tmp / "game" / "assets" / "generated" / "music" / "stray.wav"
        stray.parent.mkdir(parents=True)
        stray.write_bytes(b"RIFF")
        proc = self.run_cli("gate", "--ship", ok=False)
        self.assertIn("UNTRACKED", proc.stdout)

    def test_unconfigured_model_fails_job_not_worker(self):
        (self.tmp / "pipeline" / "worker.toml").write_text(
            (REPO / "pipeline" / "worker.example.toml").read_text())
        self.run_cli("enqueue", "music", "theme", "--prompt", "x", "--param", "duration=30")
        self.run_cli("work", "--once", "--no-git")
        failed = json.loads((self.tmp / "pipeline" / "jobs" / "failed" / "music-theme.json").read_text())
        self.assertIn("REPLACE_ME", failed["error"])

    def test_real_model_command_is_templated_without_shell(self):
        script = self.tmp / "fake_model.py"
        script.write_text("import sys, pathlib; pathlib.Path(sys.argv[2]).write_text(sys.argv[1])\n")
        (self.tmp / "pipeline" / "worker.toml").write_text(
            '[worker]\n[models.music]\nname = "fake"\nlicense = "MIT"\ncommercial_ok = true\n'
            f'command = ["{sys.executable}", "{script.as_posix()}", "{{prompt}}", "{{output}}"]\n')
        self.run_cli("enqueue", "music", "theme", "--prompt", "$(rm -rf /); `echo hi`")
        self.run_cli("work", "--once", "--no-git")
        out = self.tmp / "game" / "assets" / "generated" / "music" / "theme.wav"
        self.assertEqual(out.read_text(), "$(rm -rf /); `echo hi`")
        self.assertEqual(self.run_cli("gate", "--ship").returncode, 0)

    def test_placeholder_then_real_asset_swaps_in_place(self):
        script = self.tmp / "fake_chord.py"
        script.write_text(
            "import sys, pathlib\n"
            "out = pathlib.Path(sys.argv[2])\n"
            "if sys.argv[1] == 'fail': sys.exit(3)\n"
            "for m in ('albedo', 'normal'): (out / f'chord_{m}.png').write_bytes(b'real')\n")
        (self.tmp / "pipeline" / "worker.toml").write_text(
            '[worker]\n[models.pbr]\nname = "CHORD"\nlicense = "research-only"\ncommercial_ok = false\n'
            f'command = ["{sys.executable}", "{script.as_posix()}", "{{prompt}}", "{{output_dir}}"]\n')
        rust = self.tmp / "game" / "assets" / "generated" / "pbr" / "rust"

        self.run_cli("enqueue", "pbr", "rust", "--image", "game/assets/concept/ref.png", "--prompt", "fail")
        self.run_cli("placeholders")
        self.assertEqual(len(list(rust.glob("*.png"))), 5)
        self.assertTrue((self.tmp / "pipeline" / "jobs" / "pending" / "pbr-rust.json").exists())

        self.run_cli("work", "--once", "--no-git")  # model fails: placeholder must survive
        self.assertEqual(len(list(rust.glob("*.png"))), 5)
        self.assertTrue((self.tmp / "pipeline" / "jobs" / "failed" / "pbr-rust.json").exists())

        (self.tmp / "pipeline" / "jobs" / "failed" / "pbr-rust.json").unlink()
        self.run_cli("enqueue", "pbr", "rust", "--image", "game/assets/concept/ref.png", "--prompt", "ok")
        self.run_cli("work", "--once", "--no-git")
        self.assertEqual(sorted(p.name for p in rust.iterdir()), ["chord_albedo.png", "chord_normal.png"])
        ledger = json.loads((self.tmp / "pipeline" / "ledger.json").read_text())["assets"]
        self.assertEqual([e["model"] for e in ledger], ["CHORD", "CHORD"])
        blocked = self.run_cli("gate", "--ship", ok=False)
        self.assertIn("LICENSE", blocked.stdout)  # research-only output can't ship

    def test_rejects_bad_names_and_missing_inputs(self):
        self.assertNotEqual(self.run_cli("enqueue", "music", "../escape", ok=False).returncode, 0)
        self.assertNotEqual(self.run_cli("enqueue", "mesh", "crate", ok=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
