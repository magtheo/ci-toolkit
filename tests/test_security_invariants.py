"""Source-level security invariants for review.sh.

The most important security boundary in this repo lives in shell, not
python: the rubric (trusted policy) must resolve from the PR BASE sha,
and its fetch must fail CLOSED — only a confirmed 404 may fall back to
the bundled rubric. These tests fail if someone reverts that boundary,
even though the logic itself runs in CI, not pytest.
"""

import pathlib
import re

REVIEW_SH = pathlib.Path(__file__).resolve().parents[1] / "review.sh"
SRC = REVIEW_SH.read_text()


def _section(marker):
    start = SRC.index(marker)
    end = SRC.index("\n# ----", start + 1)
    return SRC[start:end]


def test_rubric_resolves_from_base_not_head():
    sec = _section("# ---- rubric:")
    assert "?ref=$base_sha" in sec
    assert "?ref=$head_sha" not in sec


def test_head_sha_is_still_used_for_the_review_itself():
    # head sha must remain the reviewed commit (commit_id), just not the
    # policy source
    assert "head_sha=$(jq -r .head.sha" in SRC
    assert '"$head_sha" "$MODEL"' in SRC


def test_rubric_fails_closed_on_non_200_non_404():
    sec = _section("# ---- rubric:")
    # the probe result is handled by a case with exactly two accepting
    # branches (200, 404) and an exiting catch-all
    assert re.search(r"case \"\$code\" in", sec)
    assert re.search(r"200\)", sec)
    assert re.search(r"404\)", sec)
    catchall = sec[sec.index("*)"):]
    assert "exit 1" in catchall
    assert "FAIL CLOSED" in sec


def test_network_failures_retry_not_exit():
    sec = _section("# ---- model call:")
    # rc != 0 (transport failure) must be a retry path, distinct from the
    # http-status case statement
    assert '[ "$rc" -ne 0 ]' in sec
    retry_idx = sec.index("network failure")
    case_idx = sec.index("case \"$http_code\" in")
    assert retry_idx < case_idx or "elif" in sec[:case_idx]


def test_retry_reports_last_status_not_reset():
    sec = _section("# ---- model call:")
    # http_code=000 may appear exactly once, as the pre-loop init; a
    # reset inside/after the loop would clobber the final reported status
    assert sec.count("http_code=000") == 1
    assert sec.index("http_code=000") < sec.index("for attempt")
    assert "retries exhausted (last http $http_code" in sec


def test_gitignore_covers_python_artifacts():
    gi = (REVIEW_SH.parent / ".gitignore").read_text()
    assert "__pycache__/" in gi
    assert "*.py[cod]" in gi
    assert ".pytest_cache/" in gi
