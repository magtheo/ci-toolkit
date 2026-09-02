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


# ---- credential transport: never curl argv (main #22 hardening, ----
# ---- ported to the engine architecture) ------------------------------------

def test_credentials_never_in_curl_argv():
    # Credential transport invariant: Authorization headers reach
    # curl via private files (-H @file), never argv — /proc/<pid>/cmdline
    # is observable by co-located users on self-hosted runners.
    # TWO transports carry credentials: review.sh (GitHub API) and
    # engine.py (OpenRouter model call) — both are pinned here.
    assert '-H "Authorization: Bearer $' not in SRC, \
        "Authorization header passed as argv (observable via /proc)"
    assert SRC.count("-H @") >= 2, "expected header-file curl usage"
    assert '"-H", "Authorization' not in ESRC, \
        "engine passes Authorization as curl argv (observable via /proc)"
    assert "'-H', 'Authorization" not in ESRC
    assert '"-H", "@"' in ESRC, \
        "engine model call must use header-file transport (-H @file)"


def test_credential_cleanup_is_effective_single_trap():
    # cleanup must be EFFECTIVE, not merely present: bash EXIT traps
    # REPLACE, they do not append — a second `trap ... EXIT` anywhere
    # would silently drop credential-file removal. Exactly one EXIT
    # trap, installed on a cleanup() that removes the header dir.
    exit_traps = re.findall(r"^trap .*EXIT", SRC, re.M)
    assert exit_traps == ["trap cleanup EXIT"], exit_traps
    body = SRC[SRC.index("cleanup() {"):SRC.index("trap cleanup EXIT")]
    assert 'rm -rf "$HDR_DIR"' in body, \
        "cleanup() must remove the credential header dir"


# Model-call retry invariants live in the engine since the Phase 1
# boundary extraction (reviewer-eval-baseline); same semantics.

ENGINE_PY = REVIEW_SH.parent / "engine.py"
ESRC = ENGINE_PY.read_text()


def test_network_failures_retry_not_exit():
    # transport failures (_NetworkFailure) must be a retry path inside
    # the retry loop, distinct from the HTTP-status branches
    assert "except _NetworkFailure" in ESRC
    assert "retrying after backoff" in ESRC
    retry_idx = ESRC.index('"network failure (')
    loop_idx = ESRC.index("for attempt in")
    exhausted_idx = ESRC.index("retries exhausted")
    assert loop_idx < retry_idx < exhausted_idx


def test_retry_reports_last_status_not_reset():
    # status = 0 may appear exactly once, as the pre-loop init; a
    # reset inside/after the loop would clobber the final reported status
    assert ESRC.count("status = 0") == 1
    assert ESRC.index("status = 0") < ESRC.index("for attempt in")
    assert "retries exhausted (last http {0})\".format(status)" in ESRC


def test_gitignore_covers_python_artifacts():
    gi = (REVIEW_SH.parent / ".gitignore").read_text()
    assert "__pycache__/" in gi
    assert "*.py[cod]" in gi
    assert ".pytest_cache/" in gi


# ---- caller / reusable-workflow trust model (round 5) ---------------------

TOOLKIT_ROOT = REVIEW_SH.parent
REVIEW_YML = TOOLKIT_ROOT / ".github" / "workflows" / "review.yml"
AI_REVIEW_YML = TOOLKIT_ROOT / ".github" / "workflows" / "ai-review.yml"


def test_secret_bearing_caller_uses_trusted_base_trigger():
    src = REVIEW_YML.read_text()
    assert "pull_request_target:" in src
    assert not re.search(r"^\s*pull_request:\s*$", src, re.M)


def test_secret_bearing_caller_never_inherits_secrets():
    src = REVIEW_YML.read_text()
    assert "secrets: inherit" not in src
    assert "LLM_API_KEY: ${{ secrets.LLM_API_KEY }}" in src


def test_caller_pins_both_layers_to_full_sha():
    src = REVIEW_YML.read_text()
    # only the caller job carries pins; the verify-pin job's bash
    # extraction patterns mention the same keywords as data
    caller = src[:src.index("verify-pin:")]
    uses = re.findall(r"ai-review\.yml@(\S+)", caller)
    refs = re.findall(r"toolkit_ref:\s*(\S+)", caller)
    assert uses and refs
    for ref in uses + refs:
        assert re.fullmatch(r"[0-9a-f]{40}", ref), ref
    assert uses[0] == refs[0]


def test_toolkit_ref_is_required_without_floating_default():
    src = AI_REVIEW_YML.read_text()
    assert "required: true" in src.split("toolkit_ref:")[1].split("secrets:")[0]
    assert not re.search(r"toolkit_ref:.*\n\s*default:\s*main", src)
    assert "^[0-9a-f]{40}$" in src  # SHA validation present


def test_caller_fork_guard_present():
    src = REVIEW_YML.read_text()
    assert "head.repo.fork" in src


def test_checkout_pinned_to_full_sha():
    src = AI_REVIEW_YML.read_text()
    m = re.search(r"actions/checkout@([0-9a-f]{40})", src)
    assert m, "actions/checkout must be pinned to a full commit SHA"
    assert "actions/checkout@v4\n" not in src
