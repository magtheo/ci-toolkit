"""Behavioral tests for the review.sh head-staleness guard.

Harness: tests/stub (scenario-driven fake curl on PATH). Race windows
are simulated by per-route response sequences — the Nth GET of the PR
route returns the Nth response — and asserted from OBSERVED behavior:
exit codes, the stub's calls log, saved POST bodies, and the step
summary. No network, no API key, no model calls.

Windows (fix/review-head-staleness-guard):
  A — head moves during file acquisition      -> abort before the model
      call (exit 4, no OpenRouter call, no POST);
  B — head moves between the model call and the POST -> abort before
      posting (exit 4, OpenRouter called exactly once, no POST);
  re-check failure (HTTP 500 on the guard GET) -> fail CLOSED (exit 5);
  stable head -> review posted, commit_id == the snapshot head.
Skip paths (fork, and via fixture shape the docs-only path) remain
exit 0 and unchanged.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
STUB = Path(__file__).resolve().parent / "stub"

H1 = "a" * 40
H2 = "b" * 40
BASE = "c" * 40

FILES = [{
    "filename": "app.py",
    "status": "modified",
    "patch": "--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,3 @@\n"
             " import os\n+print('hi')\n import sys\n",
}]

REVIEW_CONTENT = json.dumps({
    "assessment": "CLEAR",
    "summary": "stub review",
    "findings": [],
    "good": [],
}, separators=(",", ":"))

OPENROUTER_OK = {
    "choices": [{"message": {"content": REVIEW_CONTENT},
                 "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 10},
    "provider": "stub",
}


def pr_json(head_sha, fork=False):
    return {
        "title": "t", "body": "b",
        "head": {"sha": head_sha, "repo": {"fork": fork}},
        "base": {"sha": BASE},
    }


def build_scenario(tmp_path, pr_responses):
    scn = tmp_path / "stub"
    scn.mkdir()
    (scn / "pr1.json").write_text(json.dumps(pr_json(H1)))
    (scn / "pr2.json").write_text(json.dumps(pr_json(H2)))
    (scn / "prfork.json").write_text(json.dumps(pr_json(H1, fork=True)))
    (scn / "files.json").write_text(json.dumps(FILES))
    (scn / "openrouter.json").write_text(json.dumps(OPENROUTER_OK))
    # Ordered routes: more specific substrings first, so e.g.
    # /pulls/7/files and /pulls/7/reviews never fall through to /pulls/7.
    routes = [
        {"match": "/pulls/7/files",
         "responses": ["files.json"]},
        {"match": "/pulls/7/reviews",
         "responses": [{"body": "## AI review · Clear (stub)",
                        "comments": []}]},
        {"match": "/contents/.ai-review-rubric.md",
         "responses": [{"__status__": 404, "body": {}}]},
        {"match": "/pulls/7",
         "responses": pr_responses},
        {"match": "openrouter.ai",
         "responses": ["openrouter.json"]},
    ]
    (scn / "routes.json").write_text(json.dumps(routes))
    (scn / "calls.log").write_text("")
    return scn


def run_review(tmp_path, scn):
    env = dict(os.environ)
    env["PATH"] = "{0}{1}{2}".format(STUB, os.pathsep, env["PATH"])
    env.update({
        "STUB_DIR": str(scn),
        "PR_NUMBER": "7",
        "TOKEN": "stub-token",
        "OPENROUTER_API_KEY": "stub-key",
        "GITHUB_REPOSITORY": "org/repo",
        "GITHUB_API_URL": "https://api.github.com",
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
    })
    summary = tmp_path / "summary.md"
    proc = subprocess.run(
        ["bash", str(REPO / "review.sh")],
        cwd=str(tmp_path), env=env, timeout=180,
        capture_output=True, text=True)
    calls = (scn / "calls.log").read_text().splitlines()
    posts = list((scn / "posts").glob("*.json")) if \
        (scn / "posts").exists() else []
    # Only the review POST body carries commit_id; the OpenRouter
    # request body (the prompt) is saved here too and must not count.
    posted = [p for p in posts if "commit_id" in p.read_text()]
    summary_text = summary.read_text() if summary.exists() else ""
    return proc, calls, posted, summary_text


def call_count(calls, needle):
    return sum(1 for c in calls if needle in c)


def test_stable_head_posts_review_bound_to_snapshot_head(tmp_path):
    scn = build_scenario(tmp_path, ["pr1.json"])
    proc, calls, posted, summary = run_review(tmp_path, scn)
    assert proc.returncode == 0, proc.stderr
    assert call_count(calls, "pulls/7/files") >= 1
    assert call_count(calls, "openrouter.ai") == 1
    assert len(posted) == 1
    payload = json.loads(posted[0].read_text())
    assert payload["commit_id"] == H1
    assert payload["event"] == "COMMENT"
    assert "AI review" in payload["body"]
    assert "AI review posted" in summary


def test_head_moved_during_acquisition_aborts_before_model_call(tmp_path):
    # PR route sequence: initial GET -> guard-1 re-GET sees the NEW head.
    scn = build_scenario(tmp_path, ["pr1.json", "pr2.json"])
    proc, calls, posted, summary = run_review(tmp_path, scn)
    assert proc.returncode == 4, proc.stderr
    assert call_count(calls, "openrouter.ai") == 0
    assert posted == []
    assert "HEAD MOVED" in summary
    assert "after file acquisition" in summary
    assert H1[:12] in summary and H2[:12] in summary


def test_head_moved_before_post_aborts_without_posting(tmp_path):
    # Guard-1 re-GET still sees H1; guard-2 (pre-POST) sees H2.
    scn = build_scenario(tmp_path, ["pr1.json", "pr1.json", "pr2.json"])
    proc, calls, posted, summary = run_review(tmp_path, scn)
    assert proc.returncode == 4, proc.stderr
    assert call_count(calls, "openrouter.ai") == 1
    assert posted == []
    assert "HEAD MOVED" in summary
    assert "before posting" in summary


def test_failed_staleness_recheck_fails_closed(tmp_path):
    # Guard-1 re-GET returns HTTP 500: an unverifiable snapshot must
    # not be reviewed as if fresh.
    scn = build_scenario(tmp_path, ["pr1.json", 500])
    proc, calls, posted, summary = run_review(tmp_path, scn)
    assert proc.returncode == 5, proc.stderr
    assert call_count(calls, "openrouter.ai") == 0
    assert posted == []
    assert "FAIL CLOSED" in summary


def test_fork_skip_unchanged(tmp_path):
    scn = build_scenario(tmp_path, ["prfork.json"])
    proc, calls, posted, summary = run_review(tmp_path, scn)
    assert proc.returncode == 0, proc.stderr
    assert call_count(calls, "openrouter.ai") == 0
    assert posted == []
    assert "fork PR" in summary
