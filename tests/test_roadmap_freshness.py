"""Contract tests for the roadmap freshness guard logic.

The guard's contract (from a real-world incident in a consumer repo): work that
landed after a stale 'Last reviewed:' date must turn the guard red —
no matter how old that work is. A rolling window (commits in the last
N days) silently passes exactly that case, which is why these tests
exist (external review caught the template shipping that bug).
"""

import datetime
import pathlib
import shutil
import subprocess
import tempfile

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / \
    "templates" / "roadmap-freshness.sh"


def _run_git(repo, *args, date=None):
    env = {}
    if date is not None:
        env = {"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    subprocess.run(["git", "-C", str(repo), *args],
                   check=True, env={**env, "PATH": "/usr/bin:/bin:/usr/local/bin",
                                    "HOME": str(repo),
                                    "GIT_CONFIG_GLOBAL": "/dev/null",
                                    "GIT_CONFIG_SYSTEM": "/dev/null"})


def _make_repo(reviewed_days_ago, commit_days_ago=None):
    repo = pathlib.Path(tempfile.mkdtemp())
    now = datetime.datetime.now(datetime.timezone.utc)
    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    _run_git(repo, "init", "-q", "-b", "main")
    _run_git(repo, "config", "user.email", "t@example.com")
    _run_git(repo, "config", "user.name", "t")

    reviewed_at = now - datetime.timedelta(days=reviewed_days_ago)
    roadmap = repo / "plans"
    roadmap.mkdir()
    (roadmap / "ROADMAP.md").write_text(
        "Last reviewed: " + reviewed_at.strftime("%Y-%m-%d") + "\n")
    _run_git(repo, "add", "-A")
    _run_git(repo, "commit", "-q", "-m", "roadmap",
             date=iso(reviewed_at))

    if commit_days_ago is not None:
        work = repo / "work.txt"
        work.write_text("work\n")
        _run_git(repo, "add", "-A")
        _run_git(repo, "commit", "-q", "-m", "work",
                 date=iso(now - datetime.timedelta(days=commit_days_ago)))
    return repo


def _guard(repo):
    return subprocess.run(["bash", str(SCRIPT)],
                          cwd=repo, capture_output=True, text=True)


def test_fresh_review_with_commits_is_green():
    r = _make_repo(reviewed_days_ago=10, commit_days_ago=5)
    assert _guard(r).returncode == 0


def test_stale_review_no_commits_since_review_is_green():
    r = _make_repo(reviewed_days_ago=60, commit_days_ago=None)
    assert _guard(r).returncode == 0


def test_stale_review_with_old_commit_since_review_is_red():
    # the rolling-window bug: 60d-old review, 40d-old commit — no
    # commits in the last 28 days, but work DID land after the review
    r = _make_repo(reviewed_days_ago=60, commit_days_ago=40)
    assert _guard(r).returncode == 1


def test_stale_review_with_recent_commit_is_red():
    r = _make_repo(reviewed_days_ago=60, commit_days_ago=1)
    assert _guard(r).returncode == 1


def test_missing_review_date_fails_loudly():
    import tempfile as tf
    repo = pathlib.Path(tf.mkdtemp())
    _run_git(repo, "init", "-q", "-b", "main")
    _run_git(repo, "config", "user.email", "t@example.com")
    _run_git(repo, "config", "user.name", "t")
    (repo / "plans").mkdir()
    (repo / "plans" / "ROADMAP.md").write_text("# Roadmap\n")
    _run_git(repo, "add", "-A")
    _run_git(repo, "commit", "-q", "-m", "x")
    result = _guard(repo)
    assert result.returncode != 0
    assert "Last reviewed" in result.stderr or "Last reviewed" in result.stdout


def test_installed_guard_runs_the_template_and_pins_checkout():
    # dogfood invariant: no second copy of the script may appear —
    # the workflow must execute the tested template in place, and CI
    # actions must be immutable full SHAs (as in ai-review.yml)
    import pathlib
    wf = pathlib.Path(__file__).resolve().parents[1] / \
        ".github" / "workflows" / "roadmap-freshness.yml"
    src = wf.read_text()
    assert "bash templates/roadmap-freshness.sh ROADMAP.md" in src
    assert "@v4" not in src.replace("# v4", "")
    import re
    uses = re.findall(r"actions/checkout@(\S+)", src)
    assert uses and all(re.fullmatch(r"[0-9a-f]{40}", u) for u in uses)
    assert not (pathlib.Path(__file__).resolve().parents[1]
                / ".github" / "scripts").exists()

WORKFLOW = pathlib.Path(__file__).resolve().parents[1] / \
    ".github" / "workflows" / "roadmap-freshness.yml"


def _make_two_roadmap_repo(roadmap_days_ago, maturity_days_ago,
                           commit_days_ago=None):
    # mirrors the dogfood layout: both authoritative roadmaps at the
    # repo root, the real template script at templates/ — exactly what
    # the workflow's step block executes
    repo = pathlib.Path(tempfile.mkdtemp())
    now = datetime.datetime.now(datetime.timezone.utc)
    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    _run_git(repo, "init", "-q", "-b", "main")
    _run_git(repo, "config", "user.email", "t@example.com")
    _run_git(repo, "config", "user.name", "t")

    (repo / "templates").mkdir()
    shutil.copy(SCRIPT, repo / "templates" / "roadmap-freshness.sh")
    for name, days in (("ROADMAP.md", roadmap_days_ago),
                       ("MATURITY_ROADMAP.md", maturity_days_ago)):
        reviewed_at = now - datetime.timedelta(days=days)
        (repo / name).write_text(
            "Last reviewed: " + reviewed_at.strftime("%Y-%m-%d") + "\n")
    _run_git(repo, "add", "-A")
    _run_git(repo, "commit", "-q", "-m", "roadmaps",
             date=iso(now - datetime.timedelta(
                 days=max(roadmap_days_ago, maturity_days_ago))))

    if commit_days_ago is not None:
        (repo / "work.txt").write_text("work\n")
        _run_git(repo, "add", "-A")
        _run_git(repo, "commit", "-q", "-m", "work",
                 date=iso(now - datetime.timedelta(days=commit_days_ago)))
    return repo


def _freshness_run_block():
    lines = WORKFLOW.read_text().splitlines()
    inv = next(i for i, l in enumerate(lines)
               if l.strip().startswith("bash templates/roadmap-freshness.sh"))
    start = max(i for i in range(inv) if lines[i].strip().startswith("run:"))
    indent = len(lines[start + 1]) - len(lines[start + 1].lstrip())
    body = []
    for line in lines[start + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) < indent:
            break
        body.append(line[indent:])
    return "\n".join(body)


def _run_step(repo, block):
    # GitHub Actions runs `run:` steps under `bash -e` on Linux
    return subprocess.run(["bash", "-e", "-c", block],
                          cwd=repo, capture_output=True, text=True)


def test_workflow_invocation_set_is_exactly_both_roadmaps():
    # neither authoritative roadmap may silently fall out of dogfood
    # coverage, and no third target may creep in
    import re
    invocations = set(re.findall(
        r"bash templates/roadmap-freshness\.sh ([^;\s]+)",
        WORKFLOW.read_text()))
    assert invocations == {"ROADMAP.md", "MATURITY_ROADMAP.md"}


def test_workflow_step_fails_on_either_roadmap_independently():
    # the workflow's step block, executed verbatim with the real
    # template script: a failure of one check must not mask the other
    block = _freshness_run_block()
    reviewed = lambda days: (datetime.datetime.now(datetime.timezone.utc)
                             - datetime.timedelta(days=days)
                             ).strftime("%Y-%m-%d")

    # ROADMAP stale-with-work, MATURITY fresh
    r = _run_step(_make_two_roadmap_repo(60, 5, commit_days_ago=40), block)
    assert r.returncode != 0
    output = r.stdout + r.stderr
    assert reviewed(60) in output and reviewed(5) not in output
    assert "fresh" in r.stdout  # MATURITY was still checked

    # mirrored: MATURITY stale-with-work, ROADMAP fresh
    r = _run_step(_make_two_roadmap_repo(5, 60, commit_days_ago=40), block)
    assert r.returncode != 0
    output = r.stdout + r.stderr
    assert reviewed(60) in output and reviewed(5) not in output
    assert "fresh" in r.stdout  # ROADMAP was still checked
