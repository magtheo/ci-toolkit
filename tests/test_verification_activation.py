"""Iteration-4 activation tests (25c — pass 2 is live).

Locks the activated blocker-verification pipeline (design rev 3):

- pass 1 is byte-identical: the zero-candidate path (CLEAR or
  INCONCLUSIVE pass-1) performs exactly ONE model call and returns the
  legacy result; no verifier call may happen;
- pass 2 runs ONLY when pass-1 normalization yields blocking
  candidates (ISSUES_FOUND);
- verdict application: confirmed findings preserved byte-for-byte;
  refuted candidates removed outright (never advisory);
- CASE B assessment recomputation: all candidates refuted -> CLEAR;
  any surviving blocker -> ISSUES_FOUND;
- semantic verifier failure (unusable verdict object) -> final review
  INCONCLUSIVE, no keep/remove applied, and the trace preserves pass-1
  state + candidates + raw verifier response + the parse error;
- pass-2 transport exhaustion -> hard run failure (SystemExit), never
  INCONCLUSIVE — infrastructure is not semantic evidence;
- trace: provider_call_count 1|2 (logical stages), pass-2 usage,
  model_id profile attribution, verifier raw+parsed telemetry.
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
        "model": {"id": "profile-x", "temperature": 0.2,
                  "max_tokens": 2000},
    }
    base.update(over)
    return base


def _verdict(verdict="confirmed", **over):
    v = {"evidence_establishes": "e", "applicable_requirement": "r",
         "contradiction": "c", "unstated_assumption": "none",
         "correct_implementation_possible": False, "verdict": verdict}
    v.update(over)
    return v


def _pass1(findings, assessment=None):
    if assessment is None:
        assessment = ("ISSUES_FOUND"
                      if any(f["severity"] == "blocking" for f in findings)
                      else "CLEAR")
    return json.dumps({"assessment": assessment, "findings": findings,
                       "summary": "s", "good": ["g"]})


def _blocker(comment="c", file="a.py"):
    return {"file": file, "line": 1, "severity": "blocking",
            "comment": comment, "suggestion": None}


def _verdicts_body(**by_id):
    return json.dumps(
        {"verdicts": {cid: _verdict(v) for cid, v in by_id.items()}})


class _DoubleCall:
    """Records pass-1/pass-2 calls; serves queued (content, usage)."""

    usage = {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10}

    def __init__(self, monkeypatch, pass1_content, pass2_content):
        self.calls = []  # ("p1"|"p2", payload_messages)
        self.pass1_content = pass1_content
        self.pass2_content = pass2_content
        monkeypatch.setattr(engine, "_call_model", self._p1)
        monkeypatch.setattr(engine, "_call_verifier", self._p2)

    def _p1(self, review_input):
        self.calls.append(("p1", review_input))
        return self.pass1_content, self.usage

    def _p2(self, review_input, candidates):
        self.calls.append(("p2", [cid for cid, _ in candidates]))
        return self.pass2_content, self.usage


@pytest.fixture
def no_trace(monkeypatch):
    monkeypatch.delenv(engine.TRACE_ENV, raising=False)


# ---- pass-1 byte identity / no candidates ------------------------------------

def test_clear_pass1_single_call_no_verification(no_trace, monkeypatch):
    dc = _DoubleCall(monkeypatch, _pass1([]), None)

    def must_not_verify(*a):
        raise AssertionError("pass 2 must not run without candidates")

    monkeypatch.setattr(engine, "_call_verifier", must_not_verify)
    result = engine.run_review(_input())
    assert [c[0] for c in dc.calls] == ["p1"]
    assert result == dict(normalize(_pass1([])),
                          usage=dc.usage, raw_output=_pass1([]))


def test_inconclusive_pass1_single_call_no_verification(no_trace,
                                                        monkeypatch):
    dc = _DoubleCall(monkeypatch, "not json at all", None)

    def must_not_verify(*a):
        raise AssertionError("pass 2 must not run on INCONCLUSIVE pass 1")

    monkeypatch.setattr(engine, "_call_verifier", must_not_verify)
    result = engine.run_review(_input())
    assert [c[0] for c in dc.calls] == ["p1"]
    assert result["assessment"] == "INCONCLUSIVE"
    assert result["raw_output"] == "not json at all"


# ---- verdict application + CASE B ---------------------------------------------

def test_all_confirmed_preserves_findings_and_label(no_trace, monkeypatch):
    findings = [_blocker("b1"), _blocker("b2", "b.py")]
    _DoubleCall(monkeypatch, _pass1(findings),
                _verdicts_body(v1="confirmed", v2="confirmed"))
    result = engine.run_review(_input())
    assert result["assessment"] == "ISSUES_FOUND"
    assert result["findings"] == findings  # byte-for-byte, order intact


def test_all_refuted_clears_case_b(no_trace, monkeypatch):
    findings = [_blocker("b1")]
    _DoubleCall(monkeypatch, _pass1(findings), _verdicts_body(v1="refuted"))
    result = engine.run_review(_input())
    assert result["assessment"] == "CLEAR"  # CASE B recomputation
    assert result["findings"] == []
    assert result["summary"] == "s" and result["good"] == ["g"]


def test_mixed_verdicts_remove_only_refuted(no_trace, monkeypatch):
    findings = [_blocker("keep me"), _blocker("drop me", "b.py")]
    _DoubleCall(monkeypatch, _pass1(findings),
                _verdicts_body(v1="confirmed", v2="refuted"))
    result = engine.run_review(_input())
    assert result["assessment"] == "ISSUES_FOUND"
    assert [f["comment"] for f in result["findings"]] == ["keep me"]
    assert all(f["severity"] == "blocking" for f in result["findings"])


def test_candidates_sent_to_verifier_are_blocking_only(no_trace,
                                                       monkeypatch):
    findings = [_blocker("b1"),
                {"file": "x.py", "line": 2, "severity": "non-blocking",
                 "comment": "adv", "suggestion": None}]
    dc = _DoubleCall(monkeypatch, _pass1(findings),
                     _verdicts_body(v1="confirmed"))
    engine.run_review(_input())
    assert dc.calls[1] == ("p2", ["v1"])


# ---- semantic failure -> INCONCLUSIVE ------------------------------------------

@pytest.mark.parametrize("bad_verifier_output", [
    "", "I cannot verify this.", "```json\n{\"verdicts\": {}}\n```",
    json.dumps({"verdicts": {}}),
    json.dumps({"verdicts": {"v1": _verdict()},
                "extra": "field"}),
])
def test_semantic_verifier_failure_is_inconclusive(no_trace, monkeypatch,
                                                   bad_verifier_output):
    findings = [_blocker("b1")]
    dc = _DoubleCall(monkeypatch, _pass1(findings), bad_verifier_output)
    result = engine.run_review(_input())
    assert result["assessment"] == "INCONCLUSIVE"
    assert result["findings"] == [] and result["summary"] == ""
    assert result["usage"] == dc.usage      # pass-1 usage preserved
    assert result["raw_output"] == _pass1(findings)
    assert [c[0] for c in dc.calls] == ["p1", "p2"]  # both stages ran


def test_semantic_failure_applies_no_keep_remove(no_trace, monkeypatch):
    findings = [_blocker("b1")]
    dc = _DoubleCall(monkeypatch, _pass1(findings),
                     _verdicts_body(v1="refuted")
                     .replace("refuted", "REFUTED"))  # invalid enum value
    result = engine.run_review(_input())
    assert result["assessment"] == "INCONCLUSIVE"
    assert result["findings"] == []  # no demotion, no preservation:
    # the failure path emits the INCONCLUSIVE shape, never a mix


# ---- transport exhaustion -> hard failure ---------------------------------------

def test_pass2_transport_exhaustion_is_hard_failure(no_trace, monkeypatch):
    class Fail:
        def __init__(self):
            self.n = 0

        def p1(self, review_input):
            return _pass1([_blocker()]), {"total_tokens": 1}

        def p2(self, review_input, candidates):
            raise AssertionError("must be reached via _post_with_retries")

    monkeypatch.setattr(engine, "_call_model", Fail().p1)
    attempts = []

    def failing_post(payload):
        attempts.append(payload)
        raise engine._NetworkFailure("curl rc 7: connection refused")

    monkeypatch.setattr(engine, "_post_chat", failing_post)
    monkeypatch.setattr(engine.time, "sleep", lambda s: None)
    with pytest.raises(SystemExit) as ei:
        engine.run_review(_input())
    assert ei.value.code == 1
    assert len(attempts) == 3  # legacy retry policy, then exhaustion


# ---- trace on activated paths ----------------------------------------------------

def test_trace_records_full_verification_evidence(tmp_path, monkeypatch):
    monkeypatch.delenv(engine.TRACE_ENV, raising=False)
    sink = tmp_path / "trace.jsonl"
    monkeypatch.setenv(engine.TRACE_ENV, str(sink))
    findings = [_blocker("b1")]
    _DoubleCall(monkeypatch, _pass1(findings), _verdicts_body(v1="refuted"))
    result = engine.run_review(_input())
    rec = json.loads(sink.read_text().splitlines()[0])
    assert rec["provider_call_count"] == 2
    assert rec["model_id"] == "profile-x"
    assert rec["candidate_ids"] == ["v1"]
    assert rec["pass1_review_result"]["assessment"] == "ISSUES_FOUND"
    assert rec["final_review_result"]["assessment"] == "CLEAR"
    assert rec["verifier_parsed"]["v1"]["verdict"] == "refuted"
    assert rec["verification_error"] is None
    assert rec["pass2_usage"]["total_tokens"] == 10
    assert result["assessment"] == "CLEAR"


def test_trace_on_semantic_failure_preserves_the_story(tmp_path,
                                                       monkeypatch):
    monkeypatch.delenv(engine.TRACE_ENV, raising=False)
    sink = tmp_path / "trace.jsonl"
    monkeypatch.setenv(engine.TRACE_ENV, str(sink))
    findings = [_blocker("b1")]
    bad = "I cannot answer that."
    _DoubleCall(monkeypatch, _pass1(findings), bad)
    result = engine.run_review(_input())
    rec = json.loads(sink.read_text().splitlines()[0])
    # pass 1 succeeded and found a blocker; pass 2 responded; parsing
    # failed; NO keep/remove decision was applied
    assert rec["pass1_review_result"]["assessment"] == "ISSUES_FOUND"
    assert rec["pass1_review_result"]["findings"] == findings
    assert rec["candidate_ids"] == ["v1"]
    assert rec["verifier_raw_response"] == bad
    assert rec["verifier_parsed"] is None
    assert "not a bare JSON object" in rec["verification_error"]
    assert rec["final_review_result"]["assessment"] == "INCONCLUSIVE"
    assert rec["final_review_result"]["findings"] == []
    assert rec["provider_call_count"] == 2
    assert result["assessment"] == "INCONCLUSIVE"


def test_trace_on_zero_candidate_path_is_single_stage(tmp_path,
                                                      monkeypatch):
    monkeypatch.delenv(engine.TRACE_ENV, raising=False)
    sink = tmp_path / "trace.jsonl"
    monkeypatch.setenv(engine.TRACE_ENV, str(sink))
    _DoubleCall(monkeypatch, _pass1([]), None)
    engine.run_review(_input())
    rec = json.loads(sink.read_text().splitlines()[0])
    assert rec["provider_call_count"] == 1
    assert rec["candidate_ids"] == []
    assert rec["verifier_raw_response"] is None
    assert rec["pass2_usage"] is None
    assert rec["verification_error"] is None


def test_trace_distinguishes_profiles(tmp_path, monkeypatch):
    monkeypatch.delenv(engine.TRACE_ENV, raising=False)
    _DoubleCall(monkeypatch, _pass1([]), None)
    for model_id in ("haiku", "sonnet"):
        sink = tmp_path / "{0}.jsonl".format(model_id)
        monkeypatch.setenv(engine.TRACE_ENV, str(sink))
        engine.run_review(_input(model={"id": model_id, "temperature": 0.2,
                                        "max_tokens": 2000}))
        rec = json.loads(sink.read_text().splitlines()[0])
        assert rec["model_id"] == model_id
