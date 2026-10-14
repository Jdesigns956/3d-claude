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
        (self.tmp / "assets" / "concept").mkdir(parents=True)
        (self.tmp / "assets" / "generated").mkdir()
        (self.tmp / "assets" / "generated" / ".gitkeep").touch()
        (self.tmp / "assets" / "concept" / "ref.png").write_bytes(b"fake")

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
        self.run_cli("enqueue", "mesh", "crate", "--image", "assets/concept/ref.png")
        self.run_cli("enqueue", "pbr", "rust", "--image", "assets/concept/ref.png")
        self.run_cli("enqueue", "foley", "intro", "--video", "deliverables/clip/clip.mp4")
        self.run_cli("work", "--once", "--mock", "--no-git")

        gen = self.tmp / "assets" / "generated"
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
        stray = self.tmp / "assets" / "generated" / "music" / "stray.wav"
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
        out = self.tmp / "assets" / "generated" / "music" / "theme.wav"
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
        rust = self.tmp / "assets" / "generated" / "pbr" / "rust"

        self.run_cli("enqueue", "pbr", "rust", "--image", "assets/concept/ref.png", "--prompt", "fail")
        self.run_cli("placeholders")
        self.assertEqual(len(list(rust.glob("*.png"))), 5)
        self.assertTrue((self.tmp / "pipeline" / "jobs" / "pending" / "pbr-rust.json").exists())

        self.run_cli("work", "--once", "--no-git")  # model fails: placeholder must survive
        self.assertEqual(len(list(rust.glob("*.png"))), 5)
        self.assertTrue((self.tmp / "pipeline" / "jobs" / "failed" / "pbr-rust.json").exists())

        (self.tmp / "pipeline" / "jobs" / "failed" / "pbr-rust.json").unlink()
        self.run_cli("enqueue", "pbr", "rust", "--image", "assets/concept/ref.png", "--prompt", "ok")
        self.run_cli("work", "--once", "--no-git")
        self.assertEqual(sorted(p.name for p in rust.iterdir()), ["chord_albedo.png", "chord_normal.png"])
        ledger = json.loads((self.tmp / "pipeline" / "ledger.json").read_text())["assets"]
        self.assertEqual([e["model"] for e in ledger], ["CHORD", "CHORD"])
        blocked = self.run_cli("gate", "--ship", ok=False)
        self.assertIn("LICENSE", blocked.stdout)  # research-only output can't ship

    def test_render_job_runs_studio_and_lands_in_deliverables(self):
        (self.tmp / "pieces").mkdir()
        (self.tmp / "pieces" / "loop.py").write_text("")
        (self.tmp / "studio").mkdir()
        (self.tmp / "studio" / "run.py").write_text(
            "import sys, pathlib\n"
            "a = sys.argv; out = pathlib.Path(a[a.index('--out') + 1])\n"
            "(out / 'frames').mkdir(parents=True)\n"
            "(out / 'loop.mp4').write_text(' '.join(a[2:]))\n")
        (self.tmp / "pipeline" / "worker.toml").write_text(f'[worker]\n[render]\npython = "{sys.executable}"\ndevice = "gpu"\n')
        self.run_cli("enqueue", "render", "loop", "--param", "samples=64", "--param", "size=540x540")
        self.run_cli("work", "--once", "--no-git")
        out = self.tmp / "deliverables" / "loop"
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["loop.mp4"])   # staging frames are dropped
        args = (out / "loop.mp4").read_text()
        self.assertIn("--mode final", args)
        self.assertIn("--device gpu", args)
        self.assertIn("--samples 64", args)
        self.assertIn("--size 540x540", args)
        ledger = json.loads((self.tmp / "pipeline" / "ledger.json").read_text())["assets"]
        self.assertEqual(ledger, [])    # renders are deliverables, not licensed assets

    def test_mock_render_is_a_cpu_preview(self):
        (self.tmp / "pieces").mkdir()
        (self.tmp / "pieces" / "loop.py").write_text("")
        (self.tmp / "studio").mkdir()
        (self.tmp / "studio" / "run.py").write_text(
            "import sys, pathlib\n"
            "a = sys.argv; out = pathlib.Path(a[a.index('--out') + 1]); out.mkdir(parents=True, exist_ok=True)\n"
            "(out / 'sheet.txt').write_text(' '.join(a[2:]))\n")
        self.run_cli("enqueue", "render", "loop")
        self.run_cli("placeholders")     # renders are never faked
        self.assertFalse((self.tmp / "deliverables").exists())
        self.run_cli("work", "--once", "--mock", "--no-git")
        text = (self.tmp / "deliverables" / "loop" / "sheet.txt").read_text()
        self.assertIn("--mode preview", text)
        self.assertIn("--device cpu", text)

    def test_foley_needs_a_video_and_fails_cleanly_without_one(self):
        self.assertNotEqual(self.run_cli("enqueue", "foley", "x", ok=False).returncode, 0)
        (self.tmp / "pipeline" / "worker.toml").write_text(
            '[worker]\n[models.foley]\nname = "f"\nlicense = "x"\ncommercial_ok = false\ncommand = ["true", "{video}"]\n')
        self.run_cli("enqueue", "foley", "x", "--video", "deliverables/none/none.mp4")
        self.run_cli("work", "--once", "--no-git")
        failed = json.loads((self.tmp / "pipeline" / "jobs" / "failed" / "foley-x.json").read_text())
        self.assertIn("not found", failed["error"])

    def test_render_variants_get_their_own_folder(self):
        (self.tmp / "pieces").mkdir()
        (self.tmp / "pieces" / "loop.py").write_text("")
        (self.tmp / "studio").mkdir()
        (self.tmp / "studio" / "run.py").write_text(
            "import sys, pathlib\n"
            "a = sys.argv; out = pathlib.Path(a[a.index('--out') + 1]); out.mkdir(parents=True, exist_ok=True)\n"
            "(out / (a[1] + '.mp4')).write_text(' '.join(a[2:]))\n")
        (self.tmp / "pipeline" / "worker.toml").write_text(f'[worker]\n[render]\npython = "{sys.executable}"\n')
        self.run_cli("enqueue", "render", "loop_story", "--piece", "loop", "--param", "size=1080x1920")
        self.run_cli("enqueue", "render", "loop")
        self.run_cli("work", "--once", "--no-git")
        self.assertIn("--size 1080x1920", (self.tmp / "deliverables" / "loop_story" / "loop.mp4").read_text())
        self.assertNotIn("--size", (self.tmp / "deliverables" / "loop" / "loop.mp4").read_text())

    def test_render_needs_an_existing_piece(self):
        self.assertNotEqual(self.run_cli("enqueue", "render", "ghost", ok=False).returncode, 0)

    def test_rejects_bad_names_and_missing_inputs(self):
        self.assertNotEqual(self.run_cli("enqueue", "music", "../escape", ok=False).returncode, 0)
        self.assertNotEqual(self.run_cli("enqueue", "mesh", "crate", ok=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
