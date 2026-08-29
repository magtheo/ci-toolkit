"""Contract tests for the roadmap freshness guard logic.

The guard's contract (from real student-platform history): work that
landed after a stale 'Last reviewed:' date must turn the guard red —
no matter how old that work is. A rolling window (commits in the last
N days) silently passes exactly that case, which is why these tests
exist (external review caught the template shipping that bug).
"""

import datetime
import pathlib
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
