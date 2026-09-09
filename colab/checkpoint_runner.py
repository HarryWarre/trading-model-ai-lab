"""Restartable Colab runner for long Quant Lab jobs.

Run from the repository root. Each stage is idempotent and writes its marker
under QUANT_DRIVE_ROOT so a disconnected runtime can resume safely.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = ["cfd_intraday_5m_15_2024.csv"]
STAGES = ("validate", "prepare", "model", "robustness", "publish")

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def state_dir():
    root = Path(os.environ.get("QUANT_DRIVE_ROOT", "/content/drive/MyDrive/trading-model-ai-lab"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "checkpoints"

def marker(stage):
    return state_dir() / f"{stage}.json"

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def write_manifest():
    entries = []
    for raw in os.environ.get("QUANT_RAW_FILES", "").split(","):
        raw = raw.strip()
        if raw:
            p = Path(raw)
            if not p.exists():
                raise FileNotFoundError(f"missing raw file: {p}")
            entries.append({"path": str(p), "sha256": sha256(p), "bytes": p.stat().st_size})
    out = state_dir() / "runtime_manifest.json"
    out.write_text(json.dumps({"created_utc": utc_now(), "files": entries}, indent=2))
    return out

def run_stage(stage):
    if stage not in STAGES:
        raise ValueError(stage)
    done = marker(stage)
    if done.exists():
        print(f"SKIP {stage}: {done}")
        return
    if stage == "validate":
        manifest = write_manifest()
        payload = {"stage": stage, "completed_utc": utc_now(), "manifest": str(manifest)}
    elif stage == "prepare":
        cmd = os.environ.get("QUANT_PREPARE_CMD", "")
        if not cmd:
            raise RuntimeError("QUANT_PREPARE_CMD is not configured")
        subprocess.run(cmd, shell=True, check=True)
        payload = {"stage": stage, "completed_utc": utc_now(), "command": cmd}
    elif stage == "model":
        cmd = os.environ.get("QUANT_MODEL_CMD", "")
        if not cmd:
            raise RuntimeError("QUANT_MODEL_CMD is not configured")
        subprocess.run(cmd, shell=True, check=True)
        payload = {"stage": stage, "completed_utc": utc_now(), "command": cmd}
    elif stage == "robustness":
        cmd = os.environ.get("QUANT_ROBUSTNESS_CMD", "")
        if not cmd:
            raise RuntimeError("QUANT_ROBUSTNESS_CMD is not configured")
        subprocess.run(cmd, shell=True, check=True)
        payload = {"stage": stage, "completed_utc": utc_now(), "command": cmd}
    else:
        payload = {"stage": stage, "completed_utc": utc_now(), "status": "manual publish required"}
    done.write_text(json.dumps(payload, indent=2))
    print(f"DONE {stage}")

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "validate"
    run_stage(stage)
