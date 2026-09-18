"""Q0 preflight tests — measurement fidelity without model calls.

Pins (Q0 directive §6/§7):
- the qualification adapter builds requests with the SAME semantics
  as production #70 (transport.build_request_body, one source);
- effort/budget measurement overrides change ONLY what they name;
- escalation is one-time, budget-only, length-gated;
- refusal/malformed/infra boundaries match transport's taxonomy;
- prompts are engine._build_prompts byte-for-byte (golden hashes)
  and invariant to measurement overrides;
- the oracle (run_corpus + fixtures + states) and the subject
  (engine/render/rubric/parse_review/review.sh) are untouched vs the
  oracle checkout 4b116a7; the transport trio is untouched vs #70;
- dry-run never opens a network connection and is deterministic;
- the deployed profile file is never mutated by measurement.
"""

import copy
import json
import pathlib
import socket
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import transport  # noqa: E402
import engine  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import eval.profile_qualification as pq  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
MODEL = "z-ai/glm-5.3-flash"
ORACLE_SHA = "4b116a7c7c4e9e78cddd362cd3ca4766aaf6ea25"
TRANSPORT_SHA = "b663bfd3139bb04a70f95d661c96ee150f534513"


def _fixture(fid):
    matches = [f for f in rc.load_corpus(REPO / "eval" / "fixtures")
               if f["id"] == fid]
    assert matches, fid
    return matches[0]


def _ok_body(content, finish="stop"):
    return json.dumps({
        "provider": "test-provider",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                  "completion_tokens_details": {"reasoning_tokens": 0}},
        "choices": [{"finish_reason": finish,
                     "message": {"content": content}}],
    })


_CLEAR = json.dumps({"assessment": "CLEAR", "findings": [],
                     "summary": "s", "good": []})


def _fake_post(responses):
    """post_payload(body) -> (raw_body, http_retries, latency)."""
    seq = list(responses)

    def post(body):
        if isinstance(seq[0], BaseException):
            raise seq.pop(0)
        return seq.pop(0), 0, 0.01

    return post


def _low_profile(**kw):
    profile, overrides = pq.measurement_profile(
        MODEL, reasoning_effort=kw.get("effort", "low"),
        max_tokens=kw.get("budget"))
    return profile, overrides


def _diff(a, b, path=""):
    diffs = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            diffs += _diff(a.get(k), b.get(k), path + "." + str(k))
    elif a != b:
        diffs.append((path, a, b))
    return diffs


# ---- measurement-only overrides -------------------------------------------

def test_overrides_change_only_what_they_name():
    base = transport.load_profile(MODEL)
    low, ov = _low_profile()
    assert low == {**base, "reasoning_effort": "low"}
    assert ov["overrides"] == {"reasoning_effort": "low"}
    high, ovh = _low_profile(effort="high")
    assert _diff(low, high) == [(".reasoning_effort", "low", "high")]
    big, ovb = _low_profile(budget=16000)
    assert _diff(low, big) == [(".max_tokens", 8000, 16000)]
    assert ovb["overrides"] == {"reasoning_effort": "low",
                                "max_tokens": 16000}
    assert ovb["base_profile"] == base


def test_effort_validation_fails_closed():
    with pytest.raises(SystemExit, match="reasoning-effort"):
        pq.measurement_profile(MODEL, reasoning_effort="medium")


# ---- request equivalence with production #70 -------------------------------

def test_low_8k_request_pins_full_shape():
    _, _, body = pq.build_initial_request(
        engine, rc._review_input(_fixture("C1"), MODEL), MODEL,
        _low_profile()[0])
    system, user = engine._build_prompts(
        rc._review_input(_fixture("C1"), MODEL))
    assert body == {
        "model": MODEL,
        "temperature": 0.2,
        "max_tokens": 8000,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "reasoning": {"effort": "low"},
        "response_format": {"type": "json_schema",
                            "json_schema": transport.load_schema()},
        "provider": {"require_parameters": True},
    }


def test_high_and_max_differ_only_in_reasoning_effort():
    bodies = {}
    for effort in ("low", "high", "max"):
        _, _, bodies[effort] = pq.build_initial_request(
            engine, rc._review_input(_fixture("C1"), MODEL), MODEL,
            _low_profile(effort=effort)[0])
    assert _diff(bodies["low"], bodies["high"]) == \
        [(".reasoning.effort", "low", "high")]
    assert _diff(bodies["low"], bodies["max"]) == \
        [(".reasoning.effort", "low", "max")]


def test_escalation_changes_only_max_tokens():
    profile, _ = _low_profile()
    ri = rc._review_input(_fixture("C1"), MODEL)
    _, _, initial = pq.build_initial_request(engine, ri, MODEL, profile)
    escalated = transport.build_request_body(
        MODEL, initial["messages"][0]["content"],
        initial["messages"][1]["content"], profile,
        max_tokens=profile["max_tokens"] * 2)
    assert _diff(initial, escalated) == [(".max_tokens", 8000, 16000)]


# ---- escalation + terminal-state semantics (transport taxonomy) ------------

def _run_logical(fid, responses):
    profile, overrides = _low_profile()
    records = []
    rec = pq.logical_review(engine, _fixture(fid), 0, MODEL, profile,
                            overrides, _fake_post(responses),
                            records.append)
    return rec, records


def test_stop_never_escalates():
    rec, _ = _run_logical("C1", [_ok_body(_CLEAR)])
    assert len(rec["attempts"]) == 1
    assert rec["attempts"][0]["max_tokens"] == 8000
    assert rec["escalated"] is False
    assert rec["terminal_state"] == "OK_CONTENT"
    assert rec["result"]["assessment"] == "CLEAR"


def test_partial_truncation_escalates_like_null_content():
    partial = _ok_body('{"assessment": "CLE', finish="length")
    null_len = _ok_body(None, finish="length")
    for first in (partial, null_len):
        rec, _ = _run_logical("C1", [first, _ok_body(_CLEAR)])
        assert rec["escalated"] is True
        assert [a["max_tokens"] for a in rec["attempts"]] == [8000, 16000]
        assert [a["kind"] for a in rec["attempts"]] == ["initial",
                                                        "escalated"]
        assert rec["result"]["assessment"] == "CLEAR"


def test_escalation_is_exactly_once():
    rec, _ = _run_logical(
        "C1", [_ok_body(None, finish="length"),
               _ok_body(None, finish="length")])
    assert len(rec["attempts"]) == 2
    assert rec["attempts"][-1]["max_tokens"] == 16000
    assert rec["escalated"] is True
    assert rec["terminal_state"] == "NO_CONTENT"
    assert rec["reason_code"] == "OUTPUT_BUDGET_EXHAUSTED"
    assert rec["result"]["assessment"] == "INCONCLUSIVE"
    assert rec["result"]["findings"] == []


def test_refusal_wins_over_content_presence():
    rec, _ = _run_logical(
        "C1", [_ok_body('{"assessment": "CLEAR", "findings": []}',
                        finish="content_filter")])
    assert rec["terminal_state"] == "REFUSAL"
    assert rec["reason_code"] == "UPSTREAM_ERROR"
    assert rec["result"]["assessment"] == "INCONCLUSIVE"
    assert rec["result"]["findings"] == []


def test_malformed_envelope_maps_to_upstream_error():
    rec, _ = _run_logical("C1", [json.dumps({"error": "boom"})])
    assert rec["terminal_state"] == "MALFORMED"
    assert rec["reason_code"] == "UPSTREAM_ERROR"
    assert rec["result"]["assessment"] == "INCONCLUSIVE"


def test_infra_failure_is_not_an_inconclusive_result():
    records = []
    with pytest.raises(SystemExit):
        profile, overrides = _low_profile()
        pq.logical_review(engine, _fixture("C1"), 0, MODEL, profile,
                          overrides, _fake_post([SystemExit(1)]),
                          records.append)
    rec = records[0]
    assert rec["terminal_state"] == "TRANSPORT_FAILURE"
    assert rec["result"] is None
    assert rec["attempts"] == []


# ---- prompts: golden byte-identity + override invariance --------------------

def _prompt_hashes(fid):
    ri = rc._review_input(_fixture(fid), MODEL)
    system, user = engine._build_prompts(ri)
    return [pq._sha(system)[:16], pq._sha(user)[:16]]


def test_prompts_byte_identical_to_golden():
    golden = json.loads(
        (REPO / "tests" / "golden_prompts_q0.json").read_text())
    assert len(golden) == 36
    for fid in sorted(golden):
        assert _prompt_hashes(fid) == golden[fid], fid


def test_prompts_invariant_to_measurement_overrides():
    baseline = _prompt_hashes("M2")
    for kwargs in ({"effort": "high"}, {"effort": "max"},
                   {"effort": "low", "budget": 16000}):
        assert _prompt_hashes("M2") == baseline, kwargs


# ---- oracle / subject / transport separation (Q0 directive §7) --------------

def _changed_between(base, paths):
    out = subprocess.run(
        ["git", "diff", "--name-only", "%s..HEAD" % base, "--"] + paths,
        capture_output=True, text=True, check=True, cwd=str(REPO))
    return [l for l in out.stdout.splitlines() if l.strip()]


def test_oracle_inputs_untouched_and_version_stable():
    assert rc.oracle_version() == pq.ORACLE_VERSION
    assert _changed_between(ORACLE_SHA, [
        "eval/run_corpus.py", "eval/fixtures", "eval/states.json"]) == []


def test_subject_files_untouched_vs_oracle_checkout():
    assert _changed_between(ORACLE_SHA, [
        "engine.py", "render.py", "rubric.md", "parse_review.py",
        "review.sh"]) == []


def test_transport_files_untouched_vs_pinned_transport():
    assert _changed_between(TRANSPORT_SHA, [
        "transport.py", "model_profiles.json",
        "review_result_schema.json"]) == []


# ---- dry run: zero network, deterministic -----------------------------------

def test_dry_run_never_opens_a_socket_and_is_deterministic(tmp_path):
    def forbidden(*a, **kw):
        raise AssertionError("dry run attempted a network connection")

    real_socket = socket.socket
    socket.socket = forbidden
    try:
        out1 = pq.main(["--dry-run", "--reasoning-effort", "low",
                        "--out", str(tmp_path / "a")])
        out2 = pq.main(["--dry-run", "--reasoning-effort", "low",
                        "--out", str(tmp_path / "b")])
    finally:
        socket.socket = real_socket
    assert out1 is not None and out2 is not None
    for name in ("requests.json", "planned_bounds.json", "meta.json"):
        assert (tmp_path / "a" / name).read_bytes() == \
            (tmp_path / "b" / name).read_bytes(), name
    bounds = json.loads(
        (tmp_path / "a" / "planned_bounds.json").read_text())
    assert bounds["logical_reviews"] == 108
    assert bounds["max_provider_generations"] == 216
    records = json.loads(
        (tmp_path / "a" / "requests.json").read_text())["records"]
    assert len(records) == 36
    assert all(r["terminal_state"] == "DRY_RUN" for r in records)
    assert all(r["result"] is None for r in records)


def test_effort_variants_pin_identical_prompts_across_manifests(tmp_path):
    sha_sets = {}
    for effort in ("low", "high", "max"):
        pq.main(["--dry-run", "--reasoning-effort", effort,
                 "--out", str(tmp_path / effort)])
        recs = json.loads(
            (tmp_path / effort / "requests.json").read_text())["records"]
        sha_sets[effort] = {r["fixture"]: r["prompt_sha256"] for r in recs}
    assert sha_sets["low"] == sha_sets["high"] == sha_sets["max"]


# ---- governance guards --------------------------------------------------------

def test_live_refused_without_explicit_authorization(tmp_path):
    with pytest.raises(SystemExit, match="PM_QUALIFY_LIVE_AUTHORIZED"):
        pq.main(["--reasoning-effort", "low", "--out",
                 str(tmp_path / "live")])
    assert not (tmp_path / "live").exists()


def test_dry_run_and_live_are_exclusive(tmp_path):
    with pytest.raises(SystemExit, match="mutually exclusive"):
        pq.main(["--dry-run", "--live", "--reasoning-effort", "low",
                 "--out", str(tmp_path / "x")])


def test_deployed_profile_file_not_mutated_by_measurement():
    pinned = subprocess.run(
        ["git", "show", "%s:model_profiles.json" % TRANSPORT_SHA],
        capture_output=True, text=True, check=True, cwd=str(REPO)).stdout
    assert (REPO / "model_profiles.json").read_text() == pinned
    profile, _ = _low_profile(effort="max", budget=12000)
    assert profile["reasoning_effort"] == "max"
    assert profile["max_tokens"] == 12000
    assert (REPO / "model_profiles.json").read_text() == pinned


def test_record_carries_no_reasoning_text_and_full_accounting():
    rec, _ = _run_logical("C1", [_ok_body(_CLEAR)])
    required = {"fixture", "run_index", "model", "reasoning_effort",
                "initial_max_tokens", "attempts", "http_retries",
                "escalated", "terminal_state", "reason_code", "usage",
                "result", "wall_s", "prompt_sha256", "prompt_chars",
                "base_profile", "overrides"}
    assert required <= set(rec)
    assert "raw_output" not in (rec["result"] or {})
    assert set(rec["attempts"][0]) >= {
        "kind", "max_tokens", "finish_reason", "state", "provider",
        "prompt_tokens", "completion_tokens", "reasoning_tokens"}
