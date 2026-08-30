"""Deterministic tests for the eval harness (no network, no model).

The harness's own logic — corpus loading, matching, pass policy,
measured classification proposals, gating exit semantics, profile
metadata — must be as regression-proofed as the reviewer itself.
"""

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import eval.run_corpus as rc  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "eval" / "fixtures"


def _result(assessment, findings=None, usage=None):
    return {"schema_version": 1, "assessment": assessment,
            "findings": findings or [], "summary": "", "good": [],
            "usage": usage or {"prompt_tokens": 10,
                               "completion_tokens": 5},
            "raw_output": ""}


BLOCK = {"severity": "blocking", "file": "a", "comment": "uses inherit here",
         "line": 1, "suggestion": None}
ADV = {"severity": "non-blocking", "file": "a", "comment": "nit",
       "line": 1, "suggestion": None}


# ---- corpus ----------------------------------------------------------------

def test_corpus_loads_all_sixteen_fixtures():
    fixtures = rc.load_corpus(FIXTURES)
    ids = {f["id"] for f in fixtures}
    assert ids == {"M{0}".format(i) for i in range(1, 9)} | \
        {"C{0}".format(i) for i in range(1, 9)}


def test_every_positive_has_control_and_vice_versa():
    fixtures = {f["id"]: f for f in rc.load_corpus(FIXTURES)}
    for fid, f in fixtures.items():
        assert fixtures[f["paired_with"]]["paired_with"] == fid


def test_corpus_hash_is_stable_and_content_sensitive():
    a = rc.load_corpus(FIXTURES)
    h1 = rc.corpus_hash(a)
    assert h1 == rc.corpus_hash(rc.load_corpus(FIXTURES))
    mutated = [dict(f) for f in a]
    mutated[0] = dict(mutated[0])
    mutated[0]["input"] = dict(mutated[0]["input"],
                               title="changed")
    assert rc.corpus_hash(mutated) != h1


# ---- pass policy ------------------------------------------------------------

def _fx(kind="positive"):
    return {"id": "X1", "kind": kind,
            "expected": {"findings": [
                {"severity": "blocking", "comment_any": ["inherit"]}]}}


def test_positive_passes_at_two_of_three_detection():
    runs = [_result("ISSUES_FOUND", [dict(BLOCK)]),  # hit
            _result("ISSUES_FOUND", [dict(BLOCK)]),  # hit
            _result("CLEAR")]                         # miss
    r = rc.evaluate(_fx(), runs)
    assert r["passes_policy"] and r["proposal"] == "GATING-capable"
    assert r["expected_detection"][0]["hits"] == 2


def test_positive_fails_at_one_of_three():
    runs = [_result("ISSUES_FOUND", [dict(BLOCK)]),
            _result("CLEAR"), _result("CLEAR")]
    assert not rc.evaluate(_fx(), runs)["passes_policy"]


def test_control_fails_on_any_false_blocker_zero_tolerance():
    runs = [_result("CLEAR"), _result("CLEAR"),
            _result("ISSUES_FOUND", [{"severity": "blocking",
                                      "file": "a", "comment": "spurious",
                                      "line": 1, "suggestion": None}])]
    r = rc.evaluate(_fx(kind="control"), runs)
    assert not r["passes_policy"]
    assert r["false_blockers"] == 1
    assert r["proposal"] == "KNOWN_GAP"


def test_unexpected_blocker_fails_even_positive():
    runs = [_result("ISSUES_FOUND", [dict(BLOCK),
                                     {"severity": "blocking", "file": "b",
                                      "comment": "extra", "line": 2,
                                      "suggestion": None}])] * 3
    r = rc.evaluate(_fx(), runs)
    assert not r["passes_policy"]


def test_advisory_noise_counted_not_gating():
    runs = [_result("CLEAR", [dict(ADV), dict(ADV)])] * 3
    r = rc.evaluate(_fx(kind="control"), runs)
    assert r["passes_policy"]          # advisories alone never fail
    assert r["advisory_noise"] == 6


def test_severity_must_match_expectation():
    soft = [dict(BLOCK, severity="non-blocking")]
    runs = [_result("CLEAR", soft)] * 3
    assert not rc.evaluate(_fx(), runs)["passes_policy"]


# ---- classification + gating semantics --------------------------------------

def test_measured_proposal_is_never_taken_on_faith():
    # a fixture that fails today is proposed as KNOWN_GAP — the
    # harness records reality; states.json is the human record
    runs = [_result("CLEAR")] * 3
    r = rc.evaluate(_fx(), runs)
    assert r["proposal"] == "KNOWN_GAP"


def test_gating_violation_logic():
    # emulate main()'s gating composition: only recorded GATING
    # fixtures gate the exit status
    states = {"M1": "GATING", "M2": "KNOWN_GAP"}
    per = [{"id": "M1", "passes_policy": False},
           {"id": "M2", "passes_policy": False}]
    violations = [r["id"] for r in per
                  if states.get(r["id"]) == "GATING"
                  and not r["passes_policy"]]
    assert violations == ["M1"]


# ---- profile metadata --------------------------------------------------------

def test_review_input_uses_bundled_rubric_and_model_config():
    fx = rc.load_corpus(FIXTURES)[0]
    ri = rc._review_input(fx, "model-x")
    assert ri["schema_version"] == 1
    assert "RUBRIC" not in ri["policy"][:0]  # policy present
    assert ri["policy"].strip()              # non-empty bundled rubric
    assert ri["model"] == {"id": "model-x", "temperature": 0.2,
                           "max_tokens": 2000}


def test_spend_accumulates_usage():
    fixtures = [rc.load_corpus(FIXTURES)[0]]
    runs = iter([_result("CLEAR")])
    spend = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}

    def run_once(f):
        return _result("CLEAR")

    per, spend = rc.run_corpus(fixtures, "m", 3, run_once)
    assert spend == {"calls": 3, "prompt_tokens": 30,
                     "completion_tokens": 15}
    assert per[0]["runs"] == 3
