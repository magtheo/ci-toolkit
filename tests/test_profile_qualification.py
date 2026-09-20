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

# Byte-identity pins: sha256 of each subject file at the oracle
# checkout (4b116a7) and each transport file at the pinned #70 merge
# (b663bfd). Content hashes make these tests hermetic — they hold on
# any checkout (CI fetches shallow history) without needing the
# ancestor commits. A legitimate subject/transport bump is a
# reviewed change to these constants.
FILE_PINS = {
    # subject @ oracle checkout
    "engine.py":
        "ef69514cb4964e3df5c584486ba4578835c373fb7b7b97be5f7b5361ae3be346",
    "render.py":
        "31f32f07b77a55eb5aaad34e7481339bc15afca2b65793ec25f7674ad948b264",
    "rubric.md":
        "415d8a38cfed9d3a826c81d158d6b6883b1c0c4b598e1b81a51e98afae0b3eeb",
    "parse_review.py":
        "78333641c1b5c70bcc0745ed5993867ad35b4ea87ce2f5faba63c1664883d4e5",
    "review.sh":
        "834d950bde63b5710ef5ab12183045dc14c5b6b06bd2d27ea95106077af0089f",
    # transport @ pinned #70 merge
    "transport.py":
        "a8d53f24ee5bc6a3270ab128cf8ada72b614e45cae2a344f9a1808d241a2756c",
    "model_profiles.json":
        "821878ad3e795320017449e1af4afc87608cf9276d59cb855a44f1027aa8621a",
    "review_result_schema.json":
        "b1a3596b9ce0c52cfe4ed922c7302dde1cbf8cd01d4a2948adae814f3e83d9cc",
}


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

def _file_sha(rel):
    return pq._sha((REPO / rel).read_text())


def test_oracle_inputs_untouched_and_version_stable():
    # oracle_version is a content hash of run_corpus.py + every
    # fixture byte + states.json: equality with the pinned constant
    # IS byte-identity with the oracle checkout — no history needed.
    assert rc.oracle_version() == pq.ORACLE_VERSION == "5472d990f3b946c3"


def test_subject_and_transport_files_byte_identical_to_pins():
    for rel, expected in FILE_PINS.items():
        assert _file_sha(rel) == expected, rel


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

# ---- mode gate: genuinely double-gated live -------------------------------

def _ns(dry_run=False, live=False):
    import argparse
    return argparse.Namespace(dry_run=dry_run, live=live)


def test_mode_gate_four_cases(monkeypatch):
    # 1. --dry-run present, --live absent: allowed, no env needed.
    monkeypatch.delenv("PM_QUALIFY_LIVE_AUTHORIZED", raising=False)
    assert pq.resolve_mode(_ns(dry_run=True)) == "dry-run"
    # 2. --live present, env authorized: live.
    monkeypatch.setenv("PM_QUALIFY_LIVE_AUTHORIZED", "1")
    assert pq.resolve_mode(_ns(live=True)) == "live"
    # 3. --live present, env missing: refused.
    monkeypatch.delenv("PM_QUALIFY_LIVE_AUTHORIZED", raising=False)
    with pytest.raises(SystemExit, match="PM_QUALIFY_LIVE_AUTHORIZED"):
        pq.resolve_mode(_ns(live=True))
    # 4. env authorized WITHOUT --live: refused — the env var alone
    #    is never a live invocation.
    monkeypatch.setenv("PM_QUALIFY_LIVE_AUTHORIZED", "1")
    with pytest.raises(SystemExit, match="no mode selected"):
        pq.resolve_mode(_ns())
    # mutually exclusive flags: refused.
    with pytest.raises(SystemExit, match="mutually exclusive"):
        pq.resolve_mode(_ns(dry_run=True, live=True))


def test_authorized_env_without_live_flag_makes_no_live_run(
        tmp_path, monkeypatch):
    monkeypatch.setenv("PM_QUALIFY_LIVE_AUTHORIZED", "1")
    with pytest.raises(SystemExit, match="no mode selected"):
        pq.main(["--reasoning-effort", "low", "--out",
                 str(tmp_path / "live")])
    assert not (tmp_path / "live").exists()
    assert not (tmp_path / "live" / "records.jsonl").exists()


def test_dry_run_and_live_are_exclusive(tmp_path):
    with pytest.raises(SystemExit, match="mutually exclusive"):
        pq.main(["--dry-run", "--live", "--reasoning-effort", "low",
                 "--out", str(tmp_path / "x")])


def test_deployed_profile_file_not_mutated_by_measurement():
    pinned_sha = FILE_PINS["model_profiles.json"]
    assert _file_sha("model_profiles.json") == pinned_sha
    profile, _ = _low_profile(effort="max", budget=12000)
    assert profile["reasoning_effort"] == "max"
    assert profile["max_tokens"] == 12000
    assert _file_sha("model_profiles.json") == pinned_sha


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


# ---- raw HTTP retry accounting: local to every generation -------------------

def _install_retry_layer(monkeypatch, responses):
    """Queue of (status, body_bytes) per raw attempt; counts raw calls.

    engine._post_with_retries (the UNCHANGED legacy policy) sleeps
    between retries — the clock is stubbed, the policy is not."""
    calls = {"n": 0}
    queue = list(responses)

    def fake_post_chat(payload):
        calls["n"] += 1
        return queue.pop(0)

    monkeypatch.setattr(engine, "_post_chat", fake_post_chat)
    monkeypatch.setattr(engine.time, "sleep", lambda s: None)
    # engine_http wraps whatever is installed NOW; restoration means
    # coming back to exactly that function object.
    return calls, engine._post_chat


def test_retry_counted_on_initial_generation(monkeypatch):
    calls, sentinel = _install_retry_layer(
        monkeypatch, [(429, b"rate limited"), (200, _ok_body(_CLEAR).encode("utf-8"))])
    post = pq.engine_http(engine)
    raw, retries, _ = post({"model": MODEL})
    assert json.loads(raw)["choices"][0]["finish_reason"] == "stop"
    assert calls["n"] == 2
    assert retries == 1
    assert engine._post_chat is sentinel  # restored after success


def test_retry_counted_on_escalated_generation(monkeypatch):
    calls, sentinel = _install_retry_layer(
        monkeypatch,
        [(200, _ok_body(None, finish="length").encode("utf-8")),
         (429, b"rate limited"),
         (200, _ok_body(_CLEAR).encode("utf-8"))])
    profile, overrides = _low_profile()
    records = []
    rec = pq.logical_review(engine, _fixture("C1"), 0, MODEL, profile,
                            overrides, pq.engine_http(engine),
                            records.append)
    assert rec["escalated"] is True
    assert [a["kind"] for a in rec["attempts"]] == ["initial", "escalated"]
    assert rec["http_retries"] == 1  # the retry happened on the 16k gen
    assert rec["attempts"][0]["finish_reason"] == "length"
    assert rec["attempts"][1]["finish_reason"] == "stop"
    assert calls["n"] == 3
    assert engine._post_chat is sentinel


def test_retry_counting_is_local_to_each_generation(monkeypatch):
    calls, sentinel = _install_retry_layer(
        monkeypatch,
        [(429, b"x"), (200, _ok_body(_CLEAR).encode("utf-8")),
         (429, b"x"), (429, b"x"), (200, _ok_body(_CLEAR).encode("utf-8"))])
    post = pq.engine_http(engine)
    assert post({"m": 1})[1] == 1  # first generation: 1 retry
    assert post({"m": 2})[1] == 2  # later generation: fresh count, 2 retries
    assert calls["n"] == 5
    assert engine._post_chat is sentinel


def test_post_chat_restored_after_infra_failure(monkeypatch):
    calls, sentinel = _install_retry_layer(
        monkeypatch, [(429, b"x"), (429, b"x"), (429, b"x")])
    post = pq.engine_http(engine)
    with pytest.raises(SystemExit):
        post({"m": 1})
    assert calls["n"] == 3  # legacy policy: exactly 3 attempts
    assert engine._post_chat is sentinel  # restored after failure


# ---- resume: one reducer, records.jsonl as source of truth ------------------

def _canned_http(monkeypatch, latency=0.01):
    monkeypatch.setenv("PM_QUALIFY_LIVE_AUTHORIZED", "1")

    def fake_engine_http(engine_module):
        def post(body):
            return _ok_body(_CLEAR), 0, latency
        return post
    monkeypatch.setattr(pq, "engine_http", fake_engine_http)
    ticks = {"t": 0.0}

    def monotonic():
        ticks["t"] += 0.5
        return ticks["t"]

    monkeypatch.setattr(pq.time, "monotonic", monotonic)


def _ids(n):
    return sorted(f["id"] for f in rc.load_corpus(
        REPO / "eval" / "fixtures"))[:n]


def test_resume_summary_equals_uninterrupted_byte_for_byte(
        tmp_path, monkeypatch):
    _canned_http(monkeypatch)
    a, b = _ids(2)
    whole = tmp_path / "whole"
    split = tmp_path / "split"
    # one uninterrupted campaign: C1 then C2
    pq.live(whole, [_fixture(a), _fixture(b)], 1, MODEL,
            _low_profile()[0], _low_profile()[1])
    # same records across two process runs, in the OTHER order:
    # first run executes only C2; the resumed run skips C2 (persisted)
    # and executes C1. Reducer must make the summaries identical.
    pq.live(split, [_fixture(b)], 1, MODEL,
            _low_profile()[0], _low_profile()[1])
    pq.live(split, [_fixture(a), _fixture(b)], 1, MODEL,
            _low_profile()[0], _low_profile()[1])
    u = (whole / "summary.json").read_bytes()
    r = (split / "summary.json").read_bytes()
    assert u == r  # byte-for-byte; no nondeterministic summary fields
    summary = json.loads(u)
    assert summary["logical_reviews"] == 2
    assert summary["provider_generations"] == 2
    assert summary["transport_failures"] == 0
    # the record orders genuinely differ (order-insensitivity is real)
    order_whole = [json.loads(l)["fixture"] for l in
                   (whole / "records.jsonl").read_text().splitlines()]
    order_split = [json.loads(l)["fixture"] for l in
                   (split / "records.jsonl").read_text().splitlines()]
    assert order_whole == [a, b] and order_split == [b, a]


def test_reducer_is_the_single_aggregation():
    records = [
        {"fixture": "C1", "run_index": 0, "http_retries": 1,
         "escalated": True, "terminal_state": "OK_CONTENT",
         "wall_s": 1.5,
         "attempts": [
             {"kind": "initial", "max_tokens": 8000,
              "finish_reason": "length", "state": "NO_CONTENT",
              "prompt_tokens": 10, "completion_tokens": 3,
              "reasoning_tokens": 7000},
             {"kind": "escalated", "max_tokens": 16000,
              "finish_reason": "stop", "state": "OK_CONTENT",
              "prompt_tokens": 10, "completion_tokens": 5,
              "reasoning_tokens": 4}],
         "result": {"assessment": "CLEAR", "findings": []}},
        {"fixture": "C2", "run_index": 0, "http_retries": 0,
         "escalated": False, "terminal_state": "NO_CONTENT",
         "wall_s": 0.25, "reason_code": "OUTPUT_BUDGET_EXHAUSTED",
         "attempts": [
             {"kind": "initial", "max_tokens": 8000,
              "finish_reason": "length", "state": "NO_CONTENT",
              "prompt_tokens": 10, "completion_tokens": 0,
              "reasoning_tokens": 8000}],
         "result": {"assessment": "INCONCLUSIVE", "findings": []}},
    ]
    agg = pq.reduce_records(records)
    assert agg == {
        "logical_reviews": 2, "provider_generations": 3,
        "http_retries": 1, "prompt_tokens": 30,
        "completion_tokens": 8, "reasoning_tokens": 15004,
        "length_exhaustions": 2, "escalations": 1,
        "post_escalation_exhaustions": 0,
        "final_inconclusive": 1, "transport_failures": 0,
        "wall_s": 1.75, "campaign_halted": False}
    # transport failure: counted as a halt, never as a logical review
    halted = pq.reduce_records(records + [
        {"fixture": "C3", "run_index": 0,
         "terminal_state": "TRANSPORT_FAILURE", "attempts": [],
         "result": None}])
    assert halted["transport_failures"] == 1
    assert halted["campaign_halted"] is True
    assert halted["logical_reviews"] == 2


def test_duplicate_completed_keys_fail_closed(tmp_path, monkeypatch):
    _canned_http(monkeypatch)
    out = tmp_path / "dup"
    out.mkdir()
    rec = {"fixture": "C1", "run_index": 0, "model": MODEL,
           "reasoning_effort": "low", "initial_max_tokens": 8000,
           "terminal_state": "OK_CONTENT", "attempts": [],
           "escalated": False, "http_retries": 0, "wall_s": 0.0,
           "result": {"assessment": "CLEAR"}}
    (out / "records.jsonl").write_text(
        json.dumps(rec) + "\n" + json.dumps(rec) + "\n")
    # a consistent campaign.json so the rebind guard passes and the
    # duplicate check itself is what fires
    profile, overrides = _low_profile()
    pq._write_json(out / "campaign.json",
                   pq.campaign_identity(MODEL, profile, 1))
    with pytest.raises(SystemExit, match="duplicate completed review"):
        pq.live(out, [_fixture("C1")], 1, MODEL,
                _low_profile()[0], _low_profile()[1])


def test_transport_failure_halts_and_blocks_silent_resume(
        tmp_path, monkeypatch):
    monkeypatch.setenv("PM_QUALIFY_LIVE_AUTHORIZED", "1")
    out = tmp_path / "halt"

    def failing_engine_http(engine_module):
        def post(body):
            raise SystemExit(1)
        return post

    monkeypatch.setattr(pq, "engine_http", failing_engine_http)
    monkeypatch.setattr(pq.time, "monotonic", lambda: 0.0)
    with pytest.raises(SystemExit):
        pq.live(out, [_fixture("C1")], 1, MODEL,
                _low_profile()[0], _low_profile()[1])
    summary = json.loads((out / "summary.json").read_text())
    assert summary["transport_failures"] == 1
    assert summary["campaign_halted"] is True
    assert summary["logical_reviews"] == 0
    # resume attempt: refused — D1 halt stops pending human direction
    # (the refusal fires before any post_payload is ever installed)
    with pytest.raises(SystemExit, match="campaign halted"):
        pq.live(out, [_fixture("C1")], 1, MODEL,
                _low_profile()[0], _low_profile()[1])
    records = (out / "records.jsonl").read_text().splitlines()
    assert len(records) == 1  # nothing appended on the refused resume


# ---- campaign identity: fail-closed resume across profiles ------------------

def test_campaign_identity_persisted_before_first_record(
        tmp_path, monkeypatch):
    _canned_http(monkeypatch)
    out = tmp_path / "camp"
    pq.live(out, [_fixture("C1")], 1, MODEL, _low_profile()[0],
            _low_profile()[1])
    identity = json.loads((out / "campaign.json").read_text())
    assert identity == {
        "model": MODEL,
        "reasoning_effort": "low",
        "initial_max_tokens": 8000,
        "N": 1,
        "oracle_version": "5472d990f3b946c3",
        "oracle_checkout_sha": pq.ORACLE_CHECKOUT_SHA,
        "subject_content_ref": pq.subject_content_ref(),
        "transport_sha": pq.TRANSPORT_SHA,
        "transport_content_ref": pq.transport_content_ref(),
        "rubric_sha256": identity["rubric_sha256"],
        "corpus_sha256": identity["corpus_sha256"]}
    # deterministic content ref over subject files
    assert pq.subject_content_ref() == pq.subject_content_ref()


def test_resume_refuses_profile_change_in_same_dir(tmp_path, monkeypatch):
    _canned_http(monkeypatch)
    out = tmp_path / "mix"
    pq.live(out, [_fixture("C1")], 1, MODEL, _low_profile()[0],
            _low_profile()[1])
    before_records = (out / "records.jsonl").read_bytes()
    before_campaign = (out / "campaign.json").read_bytes()
    high, ovh = pq.measurement_profile(MODEL, reasoning_effort="high")
    with pytest.raises(SystemExit, match="campaign identity mismatch"):
        pq.live(out, [_fixture("C1")], 1, MODEL, high, ovh)
    assert (out / "records.jsonl").read_bytes() == before_records
    assert (out / "campaign.json").read_bytes() == before_campaign


def test_resume_refuses_records_from_other_profile(tmp_path, monkeypatch):
    _canned_http(monkeypatch)
    out = tmp_path / "blend"
    pq.live(out, [_fixture("C1")], 1, MODEL, _low_profile()[0],
            _low_profile()[1])
    lines = (out / "records.jsonl").read_text().splitlines()
    rec = json.loads(lines[0])
    rec["fixture"] = "C2"
    rec["reasoning_effort"] = "max"  # forged/blended record
    (out / "records.jsonl").write_text("\n".join(lines + [json.dumps(rec)])
                                       + "\n")
    with pytest.raises(SystemExit, match="different campaign profile"):
        pq.live(out, [_fixture("C1"), _fixture("C2")], 1, MODEL,
                _low_profile()[0], _low_profile()[1])


# ---- Stage-A semantic/selection reducer (through the REAL oracle) -----------

def _det_result(findings, assessment="ISSUES_FOUND"):
    return {"schema_version": 1, "assessment": assessment,
            "findings": findings, "summary": "s", "good": []}


def _m2_detect_result():
    m2 = _fixture("M2")
    a0 = m2["expected"]["groups"][0]["alternatives"][0]
    a1 = m2["expected"]["groups"][1]["alternatives"][0]
    return _det_result([
        {"file": "x.yml", "severity": a0["severity"],
         "comment": "pull_request_target trigger runs untrusted code"},
        {"file": "x.yml", "severity": a1["severity"],
         "comment": "action pins a floating toolkit_ref"}])


def _records_for(spec, runs=3):
    """spec: {fixture_id: [result, ...]} -> campaign-shaped records."""
    out = []
    for fid, results in spec.items():
        for i, res in enumerate(results[:runs]):
            out.append({
                "fixture": fid, "run_index": i, "model": MODEL,
                "reasoning_effort": "low", "initial_max_tokens": 8000,
                "terminal_state": "OK_CONTENT",
                "attempts": [{"kind": "initial", "max_tokens": 8000,
                              "finish_reason": "stop",
                              "state": "OK_CONTENT",
                              "provider": "p", "latency_s": 0.01,
                              "prompt_tokens": 10,
                              "completion_tokens": 5,
                              "reasoning_tokens": 0}],
                "http_retries": 0, "escalated": False, "wall_s": 0.01,
                "result": res})
    return out


def _auto_detect_result(fixture):
    """A result whose findings hit the FIRST alternative of every
    required group (needles embedded verbatim in the comment)."""
    findings = []
    for group in fixture["expected"]["groups"]:
        alt = group["alternatives"][0]
        parts = list(alt.get("comment_all", []))
        if alt.get("comment_any"):
            parts.append(alt["comment_any"][0])
        findings.append({"file": "x", "severity": alt["severity"],
                         "comment": " ".join(parts)})
    return _det_result(findings)


def test_stage_a_report_full_clean_campaign_through_real_oracle():
    spec = {}
    for f in rc.load_corpus(REPO / "eval" / "fixtures"):
        if f["kind"] == "positive":
            spec[f["id"]] = [_auto_detect_result(f)] * 3
        else:
            spec[f["id"]] = [_det_result([], assessment="CLEAR")] * 3
    report = pq.stage_a_report(_records_for(spec), runs=3)
    assert report["complete"] is True
    assert report["missing_runs"] == [] and report["fixtures_absent"] == []
    agg = report["aggregate_positive_detection"]
    assert agg["detected"] == 54 and agg["denominator"] == 54
    assert set(agg["per_positive"].values()) == {3}
    assert len(agg["per_positive"]) == 18
    assert report["per_group_hits"]["M2"] == [3, 3]
    assert report["gating_violations"] == []
    assert report["control_false_blocks"] == []
    assert report["pair_integrity_violations"] == []
    assert len(report["promotion_eligible"]) == 18
    assert report["false_blockers_on_positives"] == 0
    assert report["assessment_stability"]["CLEAR"] == 54
    assert report["assessment_stability"]["ISSUES_FOUND"] == 54
    assert report["inconclusive_runs"] == 0
    fired = [k for k, v in report["hard_disqualifiers"].items()
             if v["fired"]]
    assert fired == []
    assert report["selection_tuple"][0] == -54  # full detection
    assert report["selection_tuple"][2] == -18


def test_stage_a_report_d3_zero_tolerance_control_false_block():
    clear = _det_result([], assessment="CLEAR")
    poisoned = _det_result(
        [{"file": "y.py", "severity": "blocking",
          "comment": "totally unrelated blocking claim"}])
    records = _records_for({"C1": [clear, poisoned, clear]})
    report = pq.stage_a_report(records, runs=3)
    d3 = report["hard_disqualifiers"]["D3_control_false_block"]
    assert d3["fired"] is True
    assert report["control_false_blocks"][0]["id"] == "C1"
    assert report["control_false_blocks"][0]["false_blockers"] == 1


def test_stage_a_report_d2_gating_regression_without_d3():
    # C4 is a recorded GATING control: INCONCLUSIVE on every run
    # fails the control (cannot review clean code) with ZERO false
    # blockers — D2 fires, D3 stays clean. Two separate concepts.
    inc = _det_result([], assessment="INCONCLUSIVE")
    records = _records_for({"C4": [inc] * 3})
    report = pq.stage_a_report(records, runs=3)
    assert report["hard_disqualifiers"]["D2_gating_regression"][
        "fired"] is True
    assert report["gating_violations"] == ["C4"]
    assert report["hard_disqualifiers"]["D3_control_false_block"][
        "fired"] is False


def test_stage_a_report_d1_and_d4_transport_disqualifiers():
    clear = _det_result([], assessment="CLEAR")
    inc = _det_result([], assessment="INCONCLUSIVE")
    records = _records_for({"C1": [inc, inc, clear]})
    # forged transport counters: 2/3 INCONCLUSIVE finals (66% > 10%)
    # and 1 escalated review that exhausted again at 16k (100% > 5%)
    for r in records:
        r["escalated"] = True
    records[0]["attempts"] = [
        {"kind": "initial", "max_tokens": 8000, "finish_reason": "length",
         "state": "NO_CONTENT", "provider": "p", "latency_s": 1.0,
         "prompt_tokens": 10, "completion_tokens": 0,
         "reasoning_tokens": 8000},
        {"kind": "escalated", "max_tokens": 16000,
         "finish_reason": "length", "state": "NO_CONTENT",
         "provider": "p", "latency_s": 2.0, "prompt_tokens": 10,
         "completion_tokens": 0, "reasoning_tokens": 16000}]
    report = pq.stage_a_report(records, runs=3)
    dq = report["hard_disqualifiers"]
    assert dq["D1_transport_viability"]["fired"] is True
    assert dq["D1_transport_viability"]["final_inconclusive"] == 2
    assert dq["D4_post_escalation_exhaustion"]["fired"] is True
    assert report["selection_tuple"][0] == 0  # no positives in spec


def test_report_cli_reads_records_and_campaign(tmp_path, monkeypatch):
    _canned_http(monkeypatch)
    out = tmp_path / "cli"
    pq.live(out, [_fixture("C1")], 1, MODEL, _low_profile()[0],
            _low_profile()[1])
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_code = pq.main(["--report", str(out / "records.jsonl")])
    assert rc_code == 0
    report = json.loads(buf.getvalue())
    assert report["campaign"]["reasoning_effort"] == "low"
    assert report["complete"] is False  # 1 of 36 fixtures only
    assert "selection_tuple" in report and "hard_disqualifiers" in report
    assert "run_detects_all_groups" in report[
        "aggregate_positive_detection"]["definition"]


# ---- rev 4: evidence-set rebind + balanced schedule realizability -----------

def test_resume_refuses_records_without_campaign_json(
        tmp_path, monkeypatch):
    """An existing evidence set must never be rebound to a freshly
    generated campaign identity (old subject/oracle records would
    acquire today's identity retroactively)."""
    _canned_http(monkeypatch)
    out = tmp_path / "orphan"
    out.mkdir()
    rec = {"fixture": "C1", "run_index": 0, "model": MODEL,
           "reasoning_effort": "low", "initial_max_tokens": 8000,
           "terminal_state": "OK_CONTENT", "attempts": [],
           "escalated": False, "http_retries": 0, "wall_s": 0.0,
           "result": {"assessment": "CLEAR"}}
    (out / "records.jsonl").write_text(json.dumps(rec) + "\n")
    with pytest.raises(SystemExit, match="without campaign.json"):
        pq.live(out, [_fixture("C1")], 1, MODEL, _low_profile()[0],
                _low_profile()[1])
    assert not (out / "campaign.json").exists()  # nothing was created
    assert len((out / "records.jsonl").read_text().splitlines()) == 1


def test_run_index_executes_the_preregistered_balanced_schedule(
        tmp_path, monkeypatch):
    """The preregistered cyclic schedule must be operationally
    realizable: single-run-index invocations populate three per-effort
    campaign directories (N=3 pinned in each campaign.json) in the
    documented interleaving."""
    _canned_http(monkeypatch)
    dirs = {e: tmp_path / e for e in ("low", "high", "max")}
    profiles = {}
    for e in dirs:
        profiles[e] = pq.measurement_profile(MODEL, reasoning_effort=e)
    schedule = [["low", "high", "max"],
                ["high", "max", "low"],
                ["max", "low", "high"]]
    fixtures = [_fixture("C1"), _fixture("C2")]
    for run_index, order in enumerate(schedule):
        for effort in order:
            profile, overrides = profiles[effort]
            pq.live(dirs[effort], fixtures, 3, MODEL, profile,
                    overrides, run_index=run_index)
    for effort, out in dirs.items():
        records = [json.loads(l) for l in
                   (out / "records.jsonl").read_text().splitlines()]
        assert sorted(r["run_index"] for r in records) == [0, 0, 1, 1, 2, 2]
        assert {r["fixture"] for r in records} == {"C1", "C2"}
        assert {r["reasoning_effort"] for r in records} == {effort}
        campaign = json.loads((out / "campaign.json").read_text())
        assert campaign["N"] == 3
        assert campaign["reasoning_effort"] == effort
    # finishing: one more full pass per effort completes all runs
    # (the resume path dedupes against persisted records)


def test_run_index_validation(tmp_path, monkeypatch):
    _canned_http(monkeypatch)
    monkeypatch.setenv("PM_QUALIFY_LIVE_AUTHORIZED", "1")
    profile, overrides = _low_profile()
    with pytest.raises(SystemExit, match="run-index must satisfy"):
        pq.live(tmp_path / "x", [_fixture("C1")], 3, MODEL, profile,
                overrides, run_index=3)
    with pytest.raises(SystemExit, match="applies to --live only"):
        pq.main(["--dry-run", "--run-index", "0", "--reasoning-effort",
                 "low", "--out", str(tmp_path / "y")])


# ---- rev 4b: hard spend ceiling, enforced before every request --------------

PRICES = (0.075, 0.25, "openrouter.ai z-ai/glm-5.3-flash 2026-09-18 "
          "discounted")


def _guard(ceiling, fixtures):
    chars = {}
    for f in fixtures:
        ri = rc._review_input(f, MODEL)
        sy, us = engine._build_prompts(ri)
        chars[f["id"]] = len(sy) + len(us)
    return pq.SpendGuard(ceiling, PRICES[0], PRICES[1], chars)


def test_spend_ceiling_halts_before_any_request(tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake_engine_http(engine_module):
        def post(body):
            calls["n"] += 1
            return _ok_body(_CLEAR), 0, 0.01
        return post

    monkeypatch.setattr(pq, "engine_http", fake_engine_http)
    monkeypatch.setenv("PM_QUALIFY_LIVE_AUTHORIZED", "1")
    out = tmp_path / "ceiling"
    profile, overrides = _low_profile()
    with pytest.raises(SystemExit, match="spend ceiling"):
        pq.live(out, [_fixture("C1")], 1, MODEL, profile, overrides,
                spend=_guard(1e-9, [_fixture("C1")]))
    assert calls["n"] == 0  # enforced BEFORE the request
    assert not (out / "records.jsonl").exists()  # nothing billed
    summary = json.loads((out / "summary.json").read_text())
    assert summary["spend"]["actual_cost_usd"] == 0.0


def test_spend_ceiling_halts_mid_campaign_and_stays_resumable(
        tmp_path, monkeypatch):
    _canned_http(monkeypatch)
    out = tmp_path / "mid"
    profile, overrides = _low_profile()
    # first invocation bills C1 only (2 runs x 1 generation)
    pq.live(out, [_fixture("C1")], 2, MODEL, profile, overrides,
            spend=_guard(1000.0, [_fixture("C1")]))
    records_before = (out / "records.jsonl").read_text()
    summary = json.loads((out / "summary.json").read_text())
    assert summary["spend"]["provider_generations_billed"] == 2
    expected_cost = (2 * 10 * PRICES[0] + 2 * (5 + 0) * PRICES[1]) / 1e6
    assert summary["spend"]["actual_cost_usd"] == round(expected_cost, 6)
    # effectively-zero ceiling: the NEXT unbilled review (C2) is
    # refused before its request; evidence intact
    with pytest.raises(SystemExit, match="spend ceiling"):
        pq.live(out, [_fixture("C1"), _fixture("C2")], 2, MODEL,
                profile, overrides, spend=_guard(0.0, fixtures_all()))
    assert (out / "records.jsonl").read_text() == records_before
    # and the ceiling breach did NOT poison the campaign: a normal
    # resume still works (fixture subsets do not touch identity)
    pq.live(out, [_fixture("C1"), _fixture("C2")], 2, MODEL,
            profile, overrides,
            spend=_guard(1000.0, fixtures_all()))


def fixtures_all():
    return [f for f in rc.load_corpus(REPO / "eval" / "fixtures")
            if f["id"] in ("C1", "C2")]


def test_spend_guard_worst_case_is_conservative():
    g = _guard(10.0, [_fixture("C1")])
    g.add({"prompt_tokens": 1000, "completion_tokens": 8000,
           "reasoning_tokens": 8000})
    # actual (over-counting) cost model
    assert g.cost_usd == (1000 * PRICES[0]
                          + 16000 * PRICES[1]) / 1e6
    # pre-request bound: ceil(chars/4)x2 input + FULL budget output
    est_in = g._est_input("C1")
    assert est_in >= (g.chars["C1"] + 3) // 4 * 2
    worst = (est_in * PRICES[0] + 16000 * PRICES[1]) / 1e6
    assert g.cost_usd + worst <= 10.0  # sanity: campaign fits the $10 class
    g.check("C1", 16000)  # must not raise


def test_spend_guard_seeds_from_persisted_records(
        tmp_path, monkeypatch):
    """The ceiling is campaign-wide: a new invocation inherits the
    billed tokens of every persisted record under the same identity."""
    _canned_http(monkeypatch)
    out = tmp_path / "seed"
    profile, overrides = _low_profile()
    pq.live(out, [_fixture("C1")], 2, MODEL, profile, overrides,
            spend=_guard(1000.0, [_fixture("C1")]))
    records = [json.loads(l) for l in
               (out / "records.jsonl").read_text().splitlines()]
    g = _guard(1000.0, [_fixture("C1")])
    for r in records:
        for a in r["attempts"]:
            g.add(a)
    assert g.in_tokens == 2 * 10 and g.out_tokens == 2 * 5
    assert g.cost_usd == (20 * PRICES[0] + 10 * PRICES[1]) / 1e6
    # a zero ceiling + seeded cost refuses any further generation
    g0 = _guard(0.0, [_fixture("C1")])
    for r in records:
        for a in r["attempts"]:
            g0.add(a)
    with pytest.raises(pq.SpendCeilingReached):
        g0.check("C1", 8000)


def test_price_argument_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("PM_QUALIFY_LIVE_AUTHORIZED", "1")
    with pytest.raises(SystemExit, match="requires --price-input-per-m"):
        pq.main(["--live", "--spend-ceiling-usd", "10", "--out", "x"])
    with pytest.raises(SystemExit, match="price-source is required"):
        pq.main(["--live", "--spend-ceiling-usd", "10",
                 "--price-input-per-m", "0.075",
                 "--price-output-per-m", "0.25", "--out", "x"])
