#!/usr/bin/env python3
"""The ONLY code path that merges a story branch. Refuses everything unproven.

usage: gate_merge.py --story <id> --branch story/<id> [--cwd <repo>]
                     [--target main] [--config harness.toml] [--cleanup] [--worktree <path>]
exit:  0 merged (+regression passed)
       11 verdict missing or not PASS
       12 pre-flight failed (dirty tree, wrong branch, unknown branch)
       13 merge conflict (aborted; tree restored)
       14 post-merge regression failed (recovery printed, NOT executed)
       40 environment error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import gitio  # noqa: E402
from gate_runner import load_config, resolve_test_command, run_tests  # noqa: E402
from story_done_check import normalize_story_id  # noqa: E402


def fail(code: int, **payload) -> int:
    print(json.dumps({"ok": False, **payload}, indent=2))
    return code


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--target", default=None, help="integration branch (default: config or main)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--cleanup", action="store_true")
    ap.add_argument("--worktree", default=None)
    args = ap.parse_args()

    cwd = Path(args.cwd).resolve()
    if not gitio.is_repo(cwd):
        return fail(40, reason=f"not a git repo: {cwd}")
    cfg = load_config(cwd, args.config)
    sid = normalize_story_id(args.story)
    target = args.target or (cfg.get("merge") or {}).get("target_branch", "main")
    artifacts = cwd / (cfg.get("gate", {}).get("artifacts_dir", "_bmad-output"))

    # 1. Verdict must exist and be PASS for this exact story+branch tip.
    verdict_path = artifacts / "test-artifacts" / f"verdict-story-{sid}.json"
    # The verdict lives on the story branch; read it from the branch, not the target tree.
    blob = gitio.git(cwd, "show", f"{args.branch}:{verdict_path.relative_to(cwd)}", check=False)
    if blob.returncode != 0:
        return fail(11, reason=f"no verdict for story {sid} on {args.branch} — run gate_runner first")
    try:
        verdict = json.loads(blob.stdout)
    except json.JSONDecodeError as exc:
        return fail(11, reason=f"verdict unreadable: {exc}")
    if verdict.get("verdict") != "PASS":
        return fail(11, reason=f"verdict is {verdict.get('verdict')!r}, not PASS",
                    verdict_reasons=verdict.get("reasons", []))
    branch_tip = gitio.git(cwd, "rev-parse", args.branch).stdout.strip()
    if verdict.get("head") != branch_tip:
        # The branch may legitimately advance past the gated SHA by commits that
        # only add gate artifacts (the verdict itself gets committed). Any commit
        # touching real code invalidates the verdict.
        artifacts_rel = str((artifacts / "test-artifacts").relative_to(cwd))
        diff = gitio.git(cwd, "diff", "--name-only",
                         f"{verdict.get('head')}..{branch_tip}", check=False)
        touched = [f for f in diff.stdout.splitlines() if f.strip()]
        non_artifact = [f for f in touched if not f.startswith(artifacts_rel)]
        if diff.returncode != 0 or non_artifact:
            return fail(11, reason=(
                f"verdict head {verdict.get('head', '')[:8]} != branch tip {branch_tip[:8]} — "
                "code changed after gating; re-run gate_runner"),
                changed_after_gate=non_artifact[:20])

    # 2. Pre-flight.
    if not gitio.branch_exists(cwd, args.branch):
        return fail(12, reason=f"branch {args.branch} does not exist")
    cur = gitio.current_branch(cwd)
    if cur.startswith("story/"):
        return fail(12, reason=f"refusing to merge while on a story branch ({cur})")
    if cur != target:
        checkout = gitio.git(cwd, "checkout", target, check=False)
        if checkout.returncode != 0:
            return fail(12, reason=f"cannot checkout {target}: {checkout.stderr.strip()}")
    if not gitio.is_clean(cwd):
        return fail(12, reason="working tree not clean — commit or stash before merging")

    before = gitio.head_sha(cwd)

    # 3. Merge --no-ff with structured message.
    tests = verdict["checks"].get("tests", {})
    trace = verdict["checks"].get("trace_gate", {})
    msg = (
        f"merge: story {sid}\n\n"
        f"Story: {sid}\n"
        f"Gate: PASS (tests exit={tests.get('exit_code')} in {tests.get('duration_s')}s; "
        f"trace {trace.get('gate_status', trace.get('status', 'n/a'))})\n"
        f"Verdict: {verdict_path.relative_to(cwd)}\n"
        f"Branch: {args.branch}\n"
    )
    merge = gitio.git(cwd, "merge", "--no-ff", "--no-edit", "-m", msg, args.branch, check=False)
    if merge.returncode != 0:
        files = gitio.conflicted_files(cwd)
        gitio.git(cwd, "merge", "--abort", check=False)
        return fail(13, reason="merge conflict — aborted, tree restored",
                    conflicts=files,
                    recovery=[f"resolve by rebasing {args.branch} onto {target}, re-run gate_runner, retry"])

    merged = gitio.head_sha(cwd)

    # 4. Post-merge regression on the integration branch.
    cmd = resolve_test_command(cfg, cwd)
    if cmd is None:
        return fail(40, reason="no test command for post-merge regression")
    regression = run_tests(cmd, cwd)
    if regression["status"] != "pass":
        print(json.dumps({
            "ok": False,
            "reason": "post-merge regression FAILED — semantic conflict likely",
            "merged_sha": merged,
            "regression": regression,
            "recovery": [
                f"inspect: git log --oneline {before}..{merged}",
                f"undo the merge (DESTRUCTIVE, run manually): git reset --hard {before}",
            ],
        }, indent=2))
        return 14

    # 5. Cleanup only after regression pass.
    cleaned = []
    if args.cleanup:
        if args.worktree and Path(args.worktree).exists():
            wt = gitio.git(cwd, "worktree", "remove", args.worktree, check=False)
            cleaned.append(f"worktree {args.worktree}: {'removed' if wt.returncode == 0 else wt.stderr.strip()}")
        br = gitio.git(cwd, "branch", "-d", args.branch, check=False)
        cleaned.append(f"branch {args.branch}: {'deleted' if br.returncode == 0 else br.stderr.strip()}")

    print(json.dumps({
        "ok": True, "story": sid, "merge_sha": merged, "target": target,
        "regression": {"status": "pass", "duration_s": regression["duration_s"]},
        "cleanup": cleaned,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
