"""Trace sidecar tests (retained measurement infrastructure).

The iteration-4 blocker-verification mechanism is REVERTED (frozen
interpretation of the 2026-09-15 campaign); the trace sidecar is
carved out by the freeze ("trace stays inert") and stays as the
evidence channel for future governed campaigns. These tests lock:

- production behavior is byte-identical with the trace environment
  variable unset, and the ReviewResult is unchanged even when tracing
  is on (the record is additive evidence only);
- the trace sink fails HARD (before the first provider call when
  predictably unwritable; on runtime write failure) — never silent;
- the frozen v2 record schema with pass-2 fields always empty/None
  and provider_call_count = 1 while the mechanism is reverted;
- the review_input_digest tracks the effective (budgeted) input.
"""

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import engine  # noqa: E402
from parse_review import normalize  # noqa: E402


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
    assert rec["model_id"] == "m"
    assert rec["verification_error"] is None
    assert rec["pass1_review_result"] == result
    assert rec["final_review_result"] == result
    assert rec["pass1_usage"] == usage
    assert rec["candidate_ids"] == []
    assert rec["verifier_raw_response"] is None
    assert rec["verifier_parsed"] is None
    assert rec["pass2_usage"] is None
    assert rec["provider_call_count"] == 1  # logical stages, not attempts
    assert set(rec) == {
        "trace_version", "model_id", "review_input_digest",
        "pass1_review_result", "pass1_usage", "candidate_ids",
        "verifier_raw_response", "verifier_parsed", "verification_error",
        "pass2_usage", "final_review_result", "provider_call_count"}


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
        engine._trace_emit(
            str(pathlib.Path("/nonexistent-dir/t.jsonl")), _input(),
            {"assessment": "CLEAR"}, {"assessment": "CLEAR"}, None, None,
            [], None, None, None, 1)
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
