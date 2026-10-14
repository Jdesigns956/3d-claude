#!/usr/bin/env python3
"""Asset job queue for the studio.

Claude (any session, no GPU needed) writes jobs; a worker on a GPU machine runs the models and
pushes the results back through git. Every generated file lands in game/assets/generated/ and gets a
ledger entry saying which model made it and whether its license allows shipping.

  python3 pipeline/assets.py enqueue music level1_theme --prompt "..." --param duration=90
  python3 pipeline/assets.py enqueue mesh crate --image game/assets/concept/crate.png --prompt "..."
  python3 pipeline/assets.py enqueue pbr rusted_chrome --image game/assets/concept/rust.png
  python3 pipeline/assets.py enqueue foley intro_clip --capture-seconds 8
  python3 pipeline/assets.py status
  python3 pipeline/assets.py placeholders           # stand-ins at the final paths, jobs stay queued
  python3 pipeline/assets.py work --watch            # on the GPU machine
  python3 pipeline/assets.py work --once --mock      # placeholders, runs anywhere
  python3 pipeline/assets.py gate [--ship]           # license / placeholder check
"""

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

import mock_assets

ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "pipeline" / "jobs"
LEDGER = ROOT / "pipeline" / "ledger.json"
GENERATED = ROOT / "game" / "assets" / "generated"
CONFIG = ROOT / "pipeline" / "worker.toml"

# type -> output extension ("" = the output is a directory of files)
JOB_TYPES = {"music": ".wav", "foley": ".wav", "mesh": ".glb", "pbr": ""}
NEEDS_IMAGE = {"mesh", "pbr"}
SLUG = re.compile(r"^[a-z0-9][a-z0-9_]*$")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def read_json(path: Path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


# ---------------------------------------------------------------- enqueue

def output_for(kind: str, name: str) -> Path:
    return GENERATED / kind / (name + JOB_TYPES[kind])


def cmd_enqueue(args) -> int:
    if not SLUG.match(args.name):
        sys.exit(f"name must be lowercase snake_case, got '{args.name}'")
    job_id = f"{args.type}-{args.name}"
    for state in ("pending", "running"):
        if (JOBS / state / f"{job_id}.json").exists():
            sys.exit(f"{job_id} is already {state}")
    inputs = {}
    if args.image:
        image = (ROOT / args.image).resolve()
        if not image.exists():
            sys.exit(f"input image not found: {args.image}")
        inputs["image"] = rel(image)
    if args.type in NEEDS_IMAGE and "image" not in inputs:
        sys.exit(f"{args.type} jobs need --image (a reference picture in the repo)")
    if args.type == "foley":
        if args.video:
            inputs["video"] = args.video
        else:
            inputs["capture"] = {"scene": args.scene, "seconds": args.capture_seconds}

    params = {}
    for item in args.param or []:
        key, _, value = item.partition("=")
        params[key] = value
    job = {
        "id": job_id,
        "type": args.type,
        "prompt": args.prompt or "",
        "params": params,
        "inputs": inputs,
        "output": rel(output_for(args.type, args.name)),
        "requested_by": args.by,
        "created": now(),
    }
    write_json(JOBS / "pending" / f"{job_id}.json", job)
    print(f"queued {job_id} -> {job['output']}")
    return 0


# ---------------------------------------------------------------- status

def cmd_status(_args) -> int:
    for state in ("pending", "running", "failed", "done"):
        files = sorted((JOBS / state).glob("*.json"))
        if state == "done":
            files = files[-10:]
        print(f"{state} ({len(files)}{' most recent' if state == 'done' else ''})")
        for f in files:
            job = read_json(f)
            line = f"  {job['id']:<32} {job['output']}"
            if state == "failed":
                line += f"\n    error: {job.get('error', '?')}"
            print(line)
    return 0


# ---------------------------------------------------------------- ledger + gate

def ledger_load() -> dict:
    return read_json(LEDGER, {"assets": []})


def ledger_record(files: list[Path], job: dict, model: dict, placeholder: bool) -> None:
    """Replace every ledger entry under the job's output (a file, or a pbr folder) with `files`."""
    ledger = ledger_load()
    out = job["output"]
    paths = {rel(f) for f in files}
    entries = [e for e in ledger["assets"] if e["path"] != out and not e["path"].startswith(out + "/")]
    for p in sorted(paths):
        entries.append({
            "path": p,
            "job": job["id"],
            "model": model["name"],
            "license": model["license"],
            "commercial_ok": bool(model["commercial_ok"]),
            "placeholder": placeholder,
            "prompt": job.get("prompt", ""),
            "created": now(),
        })
    ledger["assets"] = sorted(entries, key=lambda e: e["path"])
    write_json(LEDGER, ledger)


def generated_files() -> list[str]:
    return sorted(rel(p) for p in GENERATED.rglob("*")
                  if p.is_file() and p.suffix not in {".import", ".uid"} and p.name != ".gitkeep")


def cmd_gate(args) -> int:
    ledger = {e["path"]: e for e in ledger_load()["assets"]}
    problems = []
    for path in generated_files():
        entry = ledger.get(path)
        if entry is None:
            problems.append(f"UNTRACKED     {path} (not made by the pipeline; no license record)")
        elif entry["placeholder"]:
            problems.append(f"PLACEHOLDER   {path} (job {entry['job']})")
        elif not entry["commercial_ok"]:
            problems.append(f"LICENSE       {path} ({entry['model']}: {entry['license']})")
    for path in sorted(set(ledger) - set(generated_files())):
        print(f"note: ledger lists {path} but the file is gone")

    if not problems:
        print("gate: every generated asset is final and cleared for commercial release")
        return 0
    print("\n".join(problems))
    if args.ship:
        print(f"gate: BLOCKED - {len(problems)} asset(s) can't ship. Replace them or regenerate with a cleared model.")
        return 1
    print(f"gate: {len(problems)} asset(s) would block a release (run with --ship to enforce)")
    return 0


# ---------------------------------------------------------------- worker

MOCK_MODEL = {"name": "mock", "license": "placeholder", "commercial_ok": True}


def load_config(mock: bool) -> dict:
    if CONFIG.exists():
        return tomllib.loads(CONFIG.read_text())
    if mock:
        return {"worker": {}, "models": {}}
    sys.exit(f"missing {rel(CONFIG)}: copy pipeline/worker.example.toml and fill in your model installs")


def git(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *cmd], check=check, capture_output=True, text=True)


def sync_pull(branch: str) -> None:
    git("pull", "--rebase", "--autostash", "origin", branch)


def sync_push(branch: str, job_ids: list[str]) -> None:
    git("add", "-A", "pipeline/jobs", "pipeline/ledger.json", "game/assets/generated")
    if not git("diff", "--cached", "--quiet", check=False).returncode:
        return
    git("commit", "-m", f"assets: {', '.join(job_ids)}\n\nGenerated by pipeline/assets.py work")
    for attempt in range(4):
        if git("push", "origin", f"HEAD:{branch}", check=False).returncode == 0:
            return
        time.sleep(2 ** (attempt + 1))
        sync_pull(branch)
    raise RuntimeError("could not push generated assets")


def fill(template: list[str], values: dict) -> list[str]:
    out = []
    for part in template:
        try:
            out.append(part.format(**values))
        except KeyError as missing:
            raise RuntimeError(f"command uses {missing} but the job has no such value") from None
    return out


def capture_gameplay(job: dict, cfg: dict, dest: Path) -> Path:
    """Record a clip with Godot's Movie Maker so foley models have footage to score."""
    cap = job["inputs"]["capture"]
    fps = 30
    cmd = [cfg.get("godot", "godot"), "--path", str(ROOT / "game"), "--write-movie", str(dest),
           "--fixed-fps", str(fps), "--quit-after", str(int(float(cap["seconds"]) * fps)), cap["scene"]]
    subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    return dest


def output_path(job: dict) -> Path:
    output = ROOT / job["output"]
    if GENERATED.resolve() not in output.resolve().parents:
        raise RuntimeError(f"output must be inside {rel(GENERATED)}")
    return output


def files_at(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else []


def clear(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def run_job(job: dict, cfg: dict, mock: bool, work_dir: Path) -> tuple[list[Path], dict]:
    output = output_path(job)
    if mock:
        clear(output)
        return mock_assets.generate(job, output), MOCK_MODEL

    model = cfg.get("models", {}).get(job["type"])
    if not model:
        raise RuntimeError(f"no [models.{job['type']}] section in worker.toml")
    if any("REPLACE_ME" in part for part in model["command"]):
        raise RuntimeError(f"[models.{job['type']}].command still has REPLACE_ME; set it from the model's README")

    # The model writes into a staging folder; the old file (often a placeholder) is only replaced on success.
    stage = work_dir / "stage" / job["id"]
    clear(stage)
    staged = stage / output.name
    values = {"prompt": job.get("prompt", ""), "seed": job.get("params", {}).get("seed", "0"),
              "work_dir": str(work_dir), **job.get("params", {})}
    if JOB_TYPES[job["type"]]:
        values["output"] = str(staged)
        stage.mkdir(parents=True)
    else:
        values["output_dir"] = str(staged)
        staged.mkdir(parents=True)
    if "image" in job["inputs"]:
        values["image"] = str(ROOT / job["inputs"]["image"])
    if job["type"] == "foley":
        video = job["inputs"].get("video")
        values["video"] = str(ROOT / video) if video else str(capture_gameplay(
            job, cfg.get("worker", {}), work_dir / f"{job['id']}.avi"))

    cmd = fill(model["command"], values)
    log = work_dir / f"{job['id']}.log"
    with log.open("w") as fh:
        proc = subprocess.run(cmd, cwd=model.get("cwd"), stdout=fh, stderr=subprocess.STDOUT,
                              timeout=int(model.get("timeout_minutes", 30)) * 60)
    if proc.returncode != 0:
        tail = "".join(log.read_text(errors="replace").splitlines(keepends=True)[-15:])
        raise RuntimeError(f"{model['name']} exited {proc.returncode}:\n{tail}")

    produced = files_at(staged)
    if not produced or any(f.stat().st_size == 0 for f in produced):
        raise RuntimeError(f"{model['name']} finished but wrote nothing to {staged}")
    clear(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(staged, output)
    clear(stage)
    return files_at(output), model


def process_pending(cfg: dict, mock: bool) -> list[str]:
    work_dir = JOBS / "running"
    work_dir.mkdir(parents=True, exist_ok=True)
    handled = []
    for pending in sorted((JOBS / "pending").glob("*.json"), key=lambda p: read_json(p).get("created", "")):
        job = read_json(pending)
        running = work_dir / pending.name
        pending.rename(running)
        print(f"[{now()}] {job['id']} ...", flush=True)
        try:
            if job.get("type") not in JOB_TYPES:
                raise RuntimeError(f"unknown job type '{job.get('type')}'")
            files, model = run_job(job, cfg, mock, work_dir)
            ledger_record(files, job, model, placeholder=mock)
            job.update(status="done", finished=now(), model=model["name"], files=[rel(f) for f in files])
            write_json(JOBS / "done" / pending.name, job)
            print(f"  done: {', '.join(job['files'])}")
        except Exception as exc:  # a bad job must not stop the queue
            job.update(status="failed", finished=now(), error=str(exc))
            write_json(JOBS / "failed" / pending.name, job)
            print(f"  FAILED: {exc}")
        running.unlink(missing_ok=True)
        handled.append(job["id"])
    return handled


def cmd_placeholders(_args) -> int:
    """Mock files at the final paths of queued jobs, so scenes can reference them before the GPU worker runs.
    Jobs stay pending; the real asset later overwrites the placeholder with no scene changes."""
    made = 0
    for pending in sorted((JOBS / "pending").glob("*.json")):
        job = read_json(pending)
        output = output_path(job)
        if output.exists():
            continue
        files = mock_assets.generate(job, output)
        ledger_record(files, job, MOCK_MODEL, placeholder=True)
        print(f"placeholder {job['output']}")
        made += 1
    print(f"{made} placeholder(s) written; jobs remain queued for the worker")
    return 0


def cmd_work(args) -> int:
    cfg = load_config(args.mock)
    wcfg = cfg.get("worker", {})
    use_git = wcfg.get("git_sync", True) and not args.no_git
    if use_git:
        branch = wcfg.get("branch") or git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    while True:
        if use_git:
            sync_pull(branch)
        handled = process_pending(cfg, args.mock)
        if handled and use_git:
            sync_push(branch, handled)
        if not args.watch:
            return 0
        time.sleep(int(wcfg.get("poll_seconds", 30)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    enq = sub.add_parser("enqueue", help="queue an asset job")
    enq.add_argument("type", choices=sorted(JOB_TYPES))
    enq.add_argument("name", help="snake_case asset name; becomes the file name")
    enq.add_argument("--prompt", help="text prompt for the model")
    enq.add_argument("--image", help="reference image in the repo (mesh, pbr)")
    enq.add_argument("--video", help="foley: existing clip in the repo instead of a capture")
    enq.add_argument("--scene", default="res://scenes/main.tscn", help="foley: scene to capture")
    enq.add_argument("--capture-seconds", type=float, default=8.0)
    enq.add_argument("--param", action="append", metavar="KEY=VALUE", help="extra model parameter (repeatable)")
    enq.add_argument("--by", default="claude", help="who asked for it (agent name)")
    enq.set_defaults(func=cmd_enqueue)

    sub.add_parser("status", help="show the queue").set_defaults(func=cmd_status)
    sub.add_parser("placeholders", help="mock files for queued jobs; jobs stay queued").set_defaults(
        func=cmd_placeholders)

    work = sub.add_parser("work", help="run queued jobs (GPU machine)")
    mode = work.add_mutually_exclusive_group()
    mode.add_argument("--watch", action="store_true", help="keep polling")
    mode.add_argument("--once", action="store_true", help="process the queue once and exit (default)")
    work.add_argument("--mock", action="store_true", help="make placeholders instead of calling models")
    work.add_argument("--no-git", action="store_true", help="don't pull/commit/push")
    work.set_defaults(func=cmd_work)

    gate = sub.add_parser("gate", help="check generated assets against the ledger")
    gate.add_argument("--ship", action="store_true", help="fail on placeholders and non-commercial licenses")
    gate.set_defaults(func=cmd_gate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
