#!/usr/bin/env python3
"""The merge gate. The LLM reads an exit code, not vibes.

usage: gate_runner.py --story <id> [--cwd <worktree>] [--config harness.toml]
                      [--skip-trace] [--waive <check>:<reason>] [--out <path>]
exit:  0  PASS — merge permitted
       10 tests failed
       20 STORY-DONE missing/invalid
       30 trace gate FAIL / blocking CONCERNS / stale / target mismatch
       40 environment error (no test command, not a repo, bad config)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import gitio  # noqa: E402
from story_done_check import normalize_story_id, validate as validate_story_done  # noqa: E402

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover — py<3.11
    tomllib = None

TEST_TIMEOUT_S = 600

AUTODETECT = [
    ("bin/ci",        lambda cwd: (cwd / "bin/ci").exists(),          ["bin/ci"]),
    ("npm test",      lambda cwd: (cwd / "package.json").exists(),    ["npm", "test"]),
    ("pytest",        lambda cwd: (cwd / "pyproject.toml").exists() or (cwd / "pytest.ini").exists(), ["pytest"]),
    ("cargo test",    lambda cwd: (cwd / "Cargo.toml").exists(),      ["cargo", "test"]),
    ("bin/rails test",lambda cwd: (cwd / "Gemfile").exists() and (cwd / "bin/rails").exists(), ["bin/rails", "test"]),
    ("go test",       lambda cwd: (cwd / "go.mod").exists(),          ["go", "test", "./..."]),
]


def load_config(cwd: Path, explicit: str | None) -> dict:
    path = Path(explicit) if explicit else cwd / "harness.toml"
    if path.exists() and tomllib:
        return tomllib.loads(path.read_text())
    return {}


def resolve_test_command(cfg: dict, cwd: Path) -> list[str] | None:
    configured = (cfg.get("gate") or {}).get("test_command")
    if configured:
        return ["sh", "-c", configured] if isinstance(configured, str) else list(configured)
    for _name, probe, cmd in AUTODETECT:
        if probe(cwd):
            return cmd
    return None


def run_tests(cmd: list[str], cwd: Path) -> dict:
    start = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=TEST_TIMEOUT_S)
        code = proc.returncode
        tail = "\n".join((proc.stdout + "\n" + proc.stderr).splitlines()[-80:])
    except subprocess.TimeoutExpired:
        code, tail = 124, f"TIMEOUT after {TEST_TIMEOUT_S}s"
    return {
        "status": "pass" if code == 0 else "fail",
        "command": " ".join(cmd),
        "exit_code": code,
        "duration_s": round(time.monotonic() - start, 1),
        "output_tail": tail if code != 0 else "",
    }


def check_trace_gate(story_id: str, cfg: dict, cwd: Path, artifacts: Path) -> dict:
    sid = normalize_story_id(story_id)
    policy = (cfg.get("gate") or {}).get("trace_gate", "prefer")  # require|prefer|off
    concerns_policy = (cfg.get("gate") or {}).get("concerns_policy", "halt")
    if policy == "off":
        return {"status": "skipped", "policy": policy}

    candidates = [
        artifacts / "test-artifacts" / f"gate-decision-{sid}.json",
        artifacts / "test-artifacts" / "gate-decision.json",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        status = "fail" if policy == "require" else "skipped"
        return {"status": status, "policy": policy, "reason": "gate-decision file not found"}

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return {"status": "fail", "path": str(path), "reason": f"invalid JSON: {exc}"}

    gate_status = str(data.get("gate_status", data.get("decision", ""))).upper()
    target = normalize_story_id(
        (data.get("target") or {}).get("id", data.get("story_id", ""))
    )
    target_match = target == sid or not target

    # Freshness by git, never by evaluated_at (live files show fabricated timestamps).
    rel = path.relative_to(cwd) if path.is_relative_to(cwd) else path
    gate_time = gitio.last_commit_time(cwd, "HEAD", str(rel))
    code_time = gitio.last_commit_time(cwd, "HEAD")
    fresh = gate_time == 0 or code_time == 0 or gate_time >= code_time
    # gate_time==0 → file uncommitted yet (just produced this run) = fresh.

    ok = gate_status in ("PASS", "WAIVED") or (
        gate_status == "CONCERNS" and concerns_policy == "waive"
    )
    reasons = []
    if not target_match:
        reasons.append(f"gate-decision targets {target!r}, gating {sid!r}")
    if not fresh:
        reasons.append("gate-decision predates the branch's last code commit (stale)")
    if not ok:
        reasons.append(f"gate_status={gate_status} (concerns_policy={concerns_policy})")

    return {
        "status": "pass" if (ok and target_match and fresh) else "fail",
        "path": str(path),
        "gate_status": gate_status,
        "target_match": target_match,
        "fresh": fresh,
        "reasons": reasons,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", required=True)
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--config", default=None)
    ap.add_argument("--skip-trace", action="store_true")
    ap.add_argument("--waive", action="append", default=[], metavar="check:reason")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cwd = Path(args.cwd).resolve()
    if not gitio.is_repo(cwd):
        print(json.dumps({"verdict": "ERROR", "reasons": [f"not a git repo: {cwd}"]}))
        return 40
    cfg = load_config(cwd, args.config)
    artifacts = cwd / (cfg.get("gate", {}).get("artifacts_dir", "_bmad-output"))
    sid = normalize_story_id(args.story)
    waivers = dict(w.split(":", 1) for w in args.waive if ":" in w)

    cmd = resolve_test_command(cfg, cwd)
    if cmd is None:
        print(json.dumps({"verdict": "ERROR", "reasons": ["no test command configured or detected"]}))
        return 40

    checks: dict = {}
    checks["tests"] = {"status": "waived", "reason": waivers["tests"]} if "tests" in waivers \
        else run_tests(cmd, cwd)

    if "story_done" in waivers:
        checks["story_done"] = {"status": "waived", "reason": waivers["story_done"]}
    else:
        info, errors = validate_story_done(sid, artifacts, cwd)
        checks["story_done"] = {
            "status": "pass" if not errors else "fail",
            "path": info.get("path"),
            "errors": errors,
        }

    if args.skip_trace or "trace_gate" in waivers:
        checks["trace_gate"] = {"status": "waived",
                                "reason": waivers.get("trace_gate", "--skip-trace")}
    else:
        checks["trace_gate"] = check_trace_gate(sid, cfg, cwd, artifacts)

    failed = [k for k, v in checks.items() if v["status"] == "fail"]
    verdict = "PASS" if not failed else "FAIL"
    reasons = []
    for k in failed:
        reasons += [f"{k}: {r}" for r in checks[k].get("reasons", checks[k].get("errors", []))] \
            or [f"{k} failed"]

    out = {
        "schema_version": "1.0",
        "story_id": sid,
        "evaluated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "branch": gitio.current_branch(cwd),
        "head": gitio.head_sha(cwd),
        "checks": checks,
        "waivers": [{"check": k, "reason": v} for k, v in waivers.items()],
        "verdict": verdict,
        "reasons": reasons,
    }
    verdict_path = Path(args.out) if args.out else artifacts / "test-artifacts" / f"verdict-story-{sid}.json"
    verdict_path.parent.mkdir(parents=True, exist_ok=True)
    verdict_path.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))

    if verdict == "PASS":
        return 0
    if checks["tests"]["status"] == "fail":
        return 10
    if checks["story_done"]["status"] == "fail":
        return 20
    return 30


if __name__ == "__main__":
    sys.exit(main())
