"""Iteration-4 plumbing tests (25b — built, tested, NOT activated).

Locks the deterministic surface of the blocker-verification plumbing
(design rev 3) WITHOUT activating pass 2:

- run_review production behavior is byte-identical with the trace
  environment variable unset, and the ReviewResult is unchanged even
  when tracing is on (the record is additive evidence only);
- the trace sink fails HARD (before the first provider call when
  predictably unwritable; on runtime write failure) — never silent;
- provider_call_count counts logical model stages (1 in 25b);
- keep/remove policy preserves confirmed findings byte-for-byte,
  removes refuted candidates, never edits findings, and requires a
  verdict for every blocking candidate;
- verifier-result parsing is strict and fail-closed: any malformed
  verdict object raises VerificationParseError (the 25c caller
  converts that to INCONCLUSIVE) — unusable verification never
  confirms a blocker;
- pass-2 prompt plumbing reuses the pass-1 effective input and
  refuses to build until the protocol is configured.
"""

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import engine  # noqa: E402
import parse_review  # noqa: E402
from parse_review import extract_verdicts, normalize  # noqa: E402
from parse_review import VerificationParseError  # noqa: E402


def _input(**over):
    base = {
        "schema_version": 1,
        "title": "t",
        "body": "b",
        "files": [{"path": "a.py", "status": "modified",
                   "patch": "@@ -0,0 +1,1 @@\n+x"}],
        "policy": "RUBRIC",
        "model": {"id": "m", "temperature": 0.2, "max_tokens": 2000},
    }
    base.update(over)
    return base


def _findings():
    return [
        {"file": "a.py", "line": 1, "severity": "blocking",
         "comment": "blocker one", "suggestion": None},
        {"file": "b.py", "line": 2, "severity": "non-blocking",
         "comment": "advisory one", "suggestion": "s"},
        {"file": "c.py", "line": 3, "severity": "blocking",
         "comment": "blocker two", "suggestion": None},
    ]


def _verdict(cid, verdict="confirmed", **over):
    v = {
        "evidence_establishes": "e " + cid,
        "applicable_requirement": "r " + cid,
        "contradiction": "c " + cid,
        "unstated_assumption": "none",
        "correct_implementation_possible": False,
        "verdict": verdict,
    }
    v.update(over)
    return v


def _verdicts(**by_id):
    return {cid: _verdict(cid, verdict) for cid, verdict in by_id.items()}


# ---- candidates -------------------------------------------------------------

def test_blocking_candidates_are_deterministic_and_blocking_only():
    cands = engine._blocking_candidates(_findings())
    assert [cid for cid, _ in cands] == ["v1", "v2"]
    assert all(f["severity"] == "blocking" for _, f in cands)
    assert engine._blocking_candidates([]) == []
    assert engine._blocking_candidates(
        [{"file": "x", "line": 1, "severity": "non-blocking",
          "comment": "c", "suggestion": None}]) == []


# ---- keep/remove policy ------------------------------------------------------

def test_policy_confirmed_preserved_byte_for_byte():
    findings = _findings()
    verdicts = _verdicts(v1="confirmed", v2="confirmed")
    final, removed = engine._apply_verification_policy(findings, verdicts)
    assert final == findings  # identical values, order, no edits
    assert removed == []


def test_policy_refuted_removed_not_demoted():
    findings = _findings()
    verdicts = _verdicts(v1="refuted", v2="confirmed")
    final, removed = engine._apply_verification_policy(findings, verdicts)
    assert [f["comment"] for f in final] == ["advisory one",
                                             "blocker two"]
    assert len(removed) == 1
    assert removed[0]["candidate_id"] == "v1"
    assert removed[0]["finding"] == findings[0]
    assert removed[0]["verdict"]["verdict"] == "refuted"
    # the refuted finding is gone outright — no advisory conversion
    assert all(f["severity"] != findings[0]["severity"]
               or f["comment"] != findings[0]["comment"] for f in final)


def test_policy_all_refuted_yields_empty_final():
    findings = [f for f in _findings() if f["severity"] == "blocking"]
    final, removed = engine._apply_verification_policy(
        findings, _verdicts(v1="refuted", v2="refuted"))
    assert final == []
    assert [r["candidate_id"] for r in removed] == ["v1", "v2"]


def test_policy_missing_verdict_is_contract_error():
    with pytest.raises(ValueError, match="v2"):
        engine._apply_verification_policy(
            _findings(), _verdicts(v1="confirmed"))


# ---- strict verifier-result parsing ------------------------------------------

def _verifier_body(by_id):
    return json.dumps({"verdicts": by_id})


def test_extract_verdicts_valid_full_record():
    body = _verifier_body({"v1": _verdict("v1", "refuted"),
                           "v2": _verdict("v2", "confirmed")})
    out = extract_verdicts(body, ["v1", "v2"])
    assert out["v1"]["verdict"] == "refuted"
    assert out["v2"]["verdict"] == "confirmed"
    assert out["v1"]["evidence_establishes"] == "e v1"
    assert out["v2"]["correct_implementation_possible"] is False


def test_extract_verdicts_wrapped_in_surrounding_text():
    body = ("Verification follows.\n"
            + _verifier_body({"v1": _verdict("v1")})
            + "\nEnd.")
    assert extract_verdicts(body, ["v1"])["v1"]["verdict"] == "confirmed"


@pytest.mark.parametrize("body", [
    "",
    "no json at all",
    "[]",
    '{"assessment": "CLEAR"}',
    '{"verdicts": []}',
])
def test_extract_verdicts_non_json_or_missing_object(body):
    with pytest.raises(VerificationParseError):
        extract_verdicts(body, ["v1"])


def test_extract_verdicts_missing_id():
    with pytest.raises(VerificationParseError, match="missing=.*v2"):
        extract_verdicts(_verifier_body({"v1": _verdict("v1")}),
                         ["v1", "v2"])


def test_extract_verdicts_extra_id():
    with pytest.raises(VerificationParseError, match="extra=.*v9"):
        extract_verdicts(_verifier_body({"v1": _verdict("v1"),
                                         "v9": _verdict("v9")}),
                         ["v1"])


def test_extract_verdicts_invalid_verdict_value():
    with pytest.raises(VerificationParseError, match="invalid verdict"):
        extract_verdicts(_verifier_body(
            {"v1": _verdict("v1", verdict="REFUTED")}), ["v1"])


def test_extract_verdicts_missing_field():
    v = _verdict("v1")
    del v["contradiction"]
    with pytest.raises(VerificationParseError, match="contradiction"):
        extract_verdicts(_verifier_body({"v1": v}), ["v1"])


def test_extract_verdicts_extra_field():
    v = _verdict("v1")
    v["confidence"] = 0.9
    with pytest.raises(VerificationParseError, match="confidence"):
        extract_verdicts(_verifier_body({"v1": v}), ["v1"])


def test_extract_verdicts_empty_string_field():
    v = _verdict("v1", evidence_establishes="   ")
    with pytest.raises(VerificationParseError, match="evidence_establishes"):
        extract_verdicts(_verifier_body({"v1": v}), ["v1"])


def test_extract_verdicts_non_bool_possibility():
    v = _verdict("v1", correct_implementation_possible="no")
    with pytest.raises(VerificationParseError,
                       match="correct_implementation_possible"):
        extract_verdicts(_verifier_body({"v1": v}), ["v1"])


def test_extract_verdicts_non_object_verdict():
    with pytest.raises(VerificationParseError, match="not an object"):
        extract_verdicts(_verifier_body({"v1": "confirmed"}), ["v1"])


# ---- pass-2 prompt plumbing ---------------------------------------------------

def test_verification_context_matches_pass1_effective_input(monkeypatch):
    ri = _input(body="b" * 3000,
                files=[{"path": "a.py", "status": "modified",
                        "patch": "@@ -0,0 +1,1 @@\n+x"}])
    ctx = engine._verification_context(ri)
    changed_list, diff_text, files_note, trunc_note = engine._budget(ri)
    assert ctx == {"title": "t", "body": "b" * 2000,
                   "changed_list": changed_list, "diff_text": diff_text,
                   "files_note": files_note, "trunc_note": trunc_note}


def test_verification_prompts_refuse_without_protocol():
    assert engine.VERIFICATION_PROTOCOL is None
    with pytest.raises(RuntimeError, match="25c"):
        engine._build_verification_prompts(
            _input(), engine._blocking_candidates(_findings()))


def test_verification_prompts_embed_protocol_and_allegations(monkeypatch):
    monkeypatch.setattr(engine, "VERIFICATION_PROTOCOL", "PROTO-TEXT")
    cands = engine._blocking_candidates(_findings())
    system, user = engine._build_verification_prompts(_input(), cands)
    assert "PROTO-TEXT" in system
    assert "[v1] file=a.py line=1 severity=blocking" in user
    assert "blocker one" in user and "blocker two" in user
    assert "advisory one" not in user  # only candidates are verified
    assert "<<<DIFF_BEGIN>>>" in user and "<<<DIFF_END>>>" in user
    assert "STRICT JSON" in user


# ---- trace sidecar -------------------------------------------------------------

@pytest.fixture
def no_trace_env(monkeypatch):
    monkeypatch.delenv(engine.TRACE_ENV, raising=False)


def _mock_model(monkeypatch, content='{"assessment": "CLEAR", "findings": []}'):
    calls = []
    usage = {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10}

    def fake_call(review_input):
        calls.append(review_input)
        return content, usage

    monkeypatch.setattr(engine, "_call_model", fake_call)
    return calls, usage


def test_trace_unset_production_unchanged(no_trace_env, tmp_path,
                                          monkeypatch):
    calls, usage = _mock_model(monkeypatch)
    result = engine.run_review(_input())
    assert result == dict(normalize(
        '{"assessment": "CLEAR", "findings": []}'),
        usage=usage, raw_output='{"assessment": "CLEAR", "findings": []}')
    assert list(tmp_path.iterdir()) == []  # no sink, no file
    assert len(calls) == 1


def test_trace_set_result_unchanged_record_complete(tmp_path, monkeypatch):
    monkeypatch.delenv(engine.TRACE_ENV, raising=False)
    sink = tmp_path / "trace.jsonl"
    monkeypatch.setenv(engine.TRACE_ENV, str(sink))
    _, usage = _mock_model(monkeypatch)
    result = engine.run_review(_input())
    # additive evidence only — the returned ReviewResult is identical
    assert result["usage"] == usage
    assert result["assessment"] == "CLEAR"
    lines = sink.read_text().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["trace_version"] == engine.TRACE_VERSION
    assert rec["pass1_review_result"] == result
    assert rec["final_review_result"] == result
    assert rec["pass1_usage"] == usage
    assert rec["candidate_ids"] == []
    assert rec["verifier_raw_response"] is None
    assert rec["verifier_parsed"] is None
    assert rec["pass2_usage"] is None
    assert rec["provider_call_count"] == 1  # logical stages, not attempts
    assert set(rec) == {
        "trace_version", "review_input_digest", "pass1_review_result",
        "pass1_usage", "candidate_ids", "verifier_raw_response",
        "verifier_parsed", "pass2_usage", "final_review_result",
        "provider_call_count"}


def test_trace_digest_stable_and_effective_input_scoped(tmp_path,
                                                        monkeypatch):
    monkeypatch.delenv(engine.TRACE_ENV, raising=False)
    d1 = engine._review_input_digest(_input())
    d2 = engine._review_input_digest(_input())
    assert d1 == d2 and len(d1) == 16
    assert d1 != engine._review_input_digest(_input(title="other"))
    # the digest tracks the EFFECTIVE (budgeted) input, not the raw
    # input: the same 3-file input under a different cap produces a
    # different effective input (cap note + file list) -> a different
    # digest. This is intentional: the join key is what the model saw.
    many = _input(files=[{"path": "f{0}.py".format(i), "status": "added",
                          "patch": "@@ -0,0 +1,1 @@\n+x"}
                         for i in range(3)])
    monkeypatch.setenv("AI_REVIEW_MAX_FILES", "1")
    capped1 = engine._review_input_digest(many)
    monkeypatch.setenv("AI_REVIEW_MAX_FILES", "2")
    assert engine._review_input_digest(many) != capped1


def test_trace_preflight_fails_before_provider_call(tmp_path, monkeypatch):
    sink = tmp_path  # a directory: open(, "a") fails -> hard exit
    calls, _ = _mock_model(monkeypatch)
    monkeypatch.setattr(engine, "_call_model", engine._call_model)
    called = []

    def must_not_run(review_input):
        called.append(review_input)
        raise AssertionError("provider call must not happen")

    monkeypatch.setattr(engine, "_call_model", must_not_run)
    monkeypatch.setenv(engine.TRACE_ENV, str(sink))
    with pytest.raises(SystemExit) as ei:
        engine.run_review(_input())
    assert ei.value.code == 1
    assert called == []


def test_trace_emit_runtime_failure_is_hard(no_trace_env):
    with pytest.raises(SystemExit) as ei:
        engine._trace_emit(str(pathlib.Path("/nonexistent-dir/t.jsonl")),
                           _input(), {"assessment": "CLEAR"}, None)
    assert ei.value.code == 1


def test_trace_appends_one_record_per_review(tmp_path, monkeypatch):
    monkeypatch.delenv(engine.TRACE_ENV, raising=False)
    sink = tmp_path / "trace.jsonl"
    monkeypatch.setenv(engine.TRACE_ENV, str(sink))
    _mock_model(monkeypatch)
    engine.run_review(_input())
    engine.run_review(_input(title="second"))
    lines = sink.read_text().splitlines()
    assert len(lines) == 2
    recs = [json.loads(l) for l in lines]
    assert recs[0]["review_input_digest"] != recs[1]["review_input_digest"]
