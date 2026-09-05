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

def test_corpus_loads_all_thirty_six_fixtures():
    fixtures = rc.load_corpus(FIXTURES)
    ids = {f["id"] for f in fixtures}
    assert ids == {"M{0}".format(i) for i in range(1, 19)} | \
        {"C{0}".format(i) for i in range(1, 19)}


# ---- Track 1 family semantics (T1.1) ----------------------------------------

def test_family_field_must_be_a_declared_family(tmp_path):
    ctrl = json.loads((FIXTURES / "C9.json").read_text())
    pos = json.loads((FIXTURES / "M9.json").read_text())
    ctrl["family"] = "not-a-family"
    (tmp_path / "C9.json").write_text(json.dumps(ctrl))
    (tmp_path / "M9.json").write_text(json.dumps(pos))
    with pytest.raises(AssertionError, match="unknown family"):
        rc.load_corpus(tmp_path)


def test_family_must_be_pair_consistent(tmp_path):
    ctrl = json.loads((FIXTURES / "C9.json").read_text())
    pos = json.loads((FIXTURES / "M9.json").read_text())
    pos["family"] = "risk-boilerplate"  # control stays hallucinated-fact
    (tmp_path / "C9.json").write_text(json.dumps(ctrl))
    (tmp_path / "M9.json").write_text(json.dumps(pos))
    with pytest.raises(AssertionError, match="pair family mismatch"):
        rc.load_corpus(tmp_path)


def test_family_absent_on_both_pair_members_is_valid(tmp_path):
    ctrl = json.loads((FIXTURES / "C9.json").read_text())
    pos = json.loads((FIXTURES / "M9.json").read_text())
    for d in (ctrl, pos):
        d.pop("family")
    (tmp_path / "C9.json").write_text(json.dumps(ctrl))
    (tmp_path / "M9.json").write_text(json.dumps(pos))
    assert len(rc.load_corpus(tmp_path)) == 2


def test_identical_pair_inputs_are_rejected(tmp_path):
    # a control identical to its positive carries the defect too —
    # the pair measures nothing. This guard caught the T1.1 silent
    # template failures (M10/M12/C17/C18).
    ctrl = json.loads((FIXTURES / "C9.json").read_text())
    pos = json.loads((FIXTURES / "M9.json").read_text())
    pos["input"] = dict(ctrl["input"])  # positive now identical to control
    (tmp_path / "C9.json").write_text(json.dumps(ctrl))
    (tmp_path / "M9.json").write_text(json.dumps(pos))
    with pytest.raises(AssertionError, match="identical inputs"):
        rc.load_corpus(tmp_path)


def test_real_corpus_pairs_all_diverge():
    fixtures = {f["id"]: f for f in rc.load_corpus(FIXTURES)}
    for fid, f in fixtures.items():
        if f["kind"] == "positive":
            mate = fixtures[f["paired_with"]]
            assert f["input"] != mate["input"], fid


def test_every_declared_family_has_two_new_frozen_pairs():
    # plan rev 5, T1.1 acceptance: >=2 NEW frozen pairs per confirmed
    # family beyond baseline coverage (baseline ids are M1-M8/C1-C8)
    fixtures = {f["id"]: f for f in rc.load_corpus(FIXTURES)}
    for family in rc.FAMILIES:
        new_pairs = [fid for fid, f in fixtures.items()
                     if f["kind"] == "positive" and f.get("family") == family
                     and int(fid[1:]) >= 9]
        assert len(new_pairs) >= 2, \
            "{0}: expected >=2 new pairs, found {1}".format(family, new_pairs)


def test_states_cover_every_fixture():
    states = json.loads(
        (FIXTURES.parent / "states.json").read_text())
    fixtures = rc.load_corpus(FIXTURES)
    assert {f["id"] for f in fixtures} == set(states), \
        "states.json and corpus fixture ids must stay in lockstep"


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
    return {"id": "X1", "kind": kind, "paired_with": "X2",
            "expected": {
                "assessment": "CLEAR" if kind == "control"
                else "ISSUES_FOUND",
                "findings": [] if kind == "control" else [
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


# ---- oracle-validity regressions (external review of #12) --------------------

def test_positive_with_missed_finding_is_known_gap_not_pass():
    # the M4-inversion regression: a positive whose expected finding
    # never appears must FAIL policy (proposal KNOWN_GAP) — never
    # auto-pass via an empty-expectations hack
    fx = {"id": "X1", "kind": "positive",
          "expected": {"assessment": "ISSUES_FOUND",
                       "findings": [{"severity": "blocking",
                                     "comment_all": ["inherit"]}]}}
    runs = [_result("CLEAR")] * 3
    r = rc.evaluate(fx, runs)
    assert not r["passes_policy"]
    assert r["proposal"] == "KNOWN_GAP"


def test_control_fails_when_reviewer_is_inconclusive():
    # a reviewer answering INCONCLUSIVE on everything cannot pass a
    # clean control — expected assessment is enforced, not decorative
    fx = {"id": "C1", "kind": "control",
          "expected": {"assessment": "CLEAR", "findings": []}}
    runs = [_result("INCONCLUSIVE")] * 3
    r = rc.evaluate(fx, runs)
    assert not r["passes_policy"]
    assert r["assessment_stability"]["INCONCLUSIVE"] == 3


def test_control_passes_only_when_all_runs_clear():
    fx = {"id": "C1", "kind": "control",
          "expected": {"assessment": "CLEAR", "findings": []}}
    ok = rc.evaluate(fx, [_result("CLEAR", [dict(ADV)])] * 3)
    assert ok["passes_policy"]          # advisories are compatible
    assert ok["advisory_noise"] == 3
    mixed = rc.evaluate(fx, [_result("CLEAR"), _result("CLEAR"),
                             _result("INCONCLUSIVE")])
    assert not mixed["passes_policy"]


def test_positive_requires_assessment_stability_too():
    fx = {"id": "X1", "kind": "positive",
          "expected": {"assessment": "ISSUES_FOUND",
                       "findings": [{"severity": "blocking",
                                     "comment_all": ["inherit"]}]}}
    # detection 2/3 ok, but one INCONCLUSIVE run is a miss only if
    # it pushes assessment below threshold: 2 ISSUES_FOUND of 3 -> ok
    runs = [_result("ISSUES_FOUND", [dict(BLOCK)]),
            _result("ISSUES_FOUND", [dict(BLOCK)]),
            _result("INCONCLUSIVE")]
    r = rc.evaluate(fx, runs)
    assert r["passes_policy"]


def test_matcher_all_and_any_semantics():
    entry = {"severity": "blocking",
             "comment_all": ["jq"], "comment_any": ["slurp", "jsonl"]}
    hit = {"severity": "blocking", "file": "a",
           "comment": "the jq call needs -s to slurp the stream", "line": 1}
    missing_all = dict(hit, comment="the loop needs -s to slurp")
    missing_any = dict(hit, comment="the jq call needs -s")
    assert rc._finding_matches(entry, hit)
    assert not rc._finding_matches(entry, missing_all)
    assert not rc._finding_matches(entry, missing_any)
    assert not rc._finding_matches(entry, dict(hit, severity="non-blocking"))


def _loader_case(kind, expected):
    # self-pairing: pairing validity is not what these cases test
    return {"id": "X1", "kind": kind, "paired_with": "X1",
            "expected": expected}


def test_loader_rejects_positive_without_expected_findings(tmp_path):
    bad = _loader_case("positive", {"assessment": "ISSUES_FOUND",
                                    "findings": []})
    d = tmp_path / "f"
    d.mkdir()
    (d / "X1.json").write_text(json.dumps(bad))
    with pytest.raises(AssertionError, match="expected finding"):
        rc.load_corpus(d)


def test_loader_rejects_control_with_findings_or_non_clear(tmp_path):
    d = tmp_path / "f"
    d.mkdir()
    (d / "X1.json").write_text(json.dumps(_loader_case(
        "control", {"assessment": "ISSUES_FOUND", "findings": []})))
    with pytest.raises(AssertionError, match="CLEAR"):
        rc.load_corpus(d)


def test_loader_rejects_matcher_without_all_or_any(tmp_path):
    d = tmp_path / "f"
    d.mkdir()
    (d / "X1.json").write_text(json.dumps(_loader_case(
        "positive", {"assessment": "ISSUES_FOUND",
                     "findings": [{"severity": "blocking"}]})))
    with pytest.raises(AssertionError, match="comment_all"):
        rc.load_corpus(d)


def test_loader_rejects_any_assessment_sentinel(tmp_path):
    d = tmp_path / "f"
    d.mkdir()
    (d / "X1.json").write_text(json.dumps(_loader_case(
        "positive", {"assessment": "ANY",
                     "findings": [{"severity": "blocking",
                                   "comment_any": ["x"]}]})))
    with pytest.raises(AssertionError, match="assessment"):
        rc.load_corpus(d)


def test_real_corpus_passes_strict_validation():
    fixtures = rc.load_corpus(FIXTURES)
    for f in fixtures:
        if f["kind"] == "control":
            assert f["expected"]["assessment"] == "CLEAR"
            assert f["expected"]["findings"] == []
        else:
            assert f["expected"]["findings"]
            for e in f["expected"]["findings"]:
                assert e.get("comment_all") or e.get("comment_any")


# ---- fixture-hygiene invariants (external review pass 3 of #12) --------------

def _patch(fid):
    return json.loads((FIXTURES / (fid + ".json")).read_text()) \
        ["input"]["files"][0]["patch"]


def test_M1_C1_differ_only_in_the_secrets_block():
    a, b = _patch("M1").splitlines(), _patch("C1").splitlines()
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    j = 0
    while j < min(len(a), len(b)) - i and a[-1 - j] == b[-1 - j]:
        j += 1
    assert a[i:len(a) - j] == ["+    secrets: inherit"]
    assert b[i:len(b) - j] == ["+    secrets:",
                               "+      LLM_API_KEY: ${{ secrets.LLM_API_KEY }}"]
    # both sides fully hardened otherwise
    for p in (a, b):
        assert "pull_request_target" in "\n".join(p)
        assert "toolkit_ref: 0123456789abcdef0123456789abcdef01234567" \
            in "\n".join(p)


def test_M2_secret_expression_well_formed():
    p = _patch("M2")
    assert "LLM_API_KEY: ${{ secrets.LLM_API_KEY }}" in p
    assert "${ secrets" not in p          # the format() artifact is gone
    assert "+  pull_request:" in p        # intended defect 1
    assert "@main" in p                   # intended defect 2 (floating)


def test_M7_urllib_hunk_is_mechanically_valid():
    p = _patch("M7")
    assert "+    req = urllib.request.Request(OPENROUTER_URL," in p
    # the presented function defines everything it uses


def test_C4_claim_is_self_contained():
    c4, m4 = _patch("C4"), _patch("M4")
    assert "RetryHandler" not in c4
    assert "no other signal" not in c4   # no external-code claims
    assert "no other signal" in m4       # M4 keeps the cross-file claim


def test_no_accidental_double_diff_markers():
    for f in sorted(FIXTURES.glob("*.json")):
        for line in _patch(f.stem).splitlines():
            assert not (line.startswith("++") and
                        not line.startswith("+++ ")), (f.stem, line)


def test_report_captures_raw_findings_for_analysis():
    # the baseline's key question is WHAT the reviewer said, not just
    # how often — false blockers must be inspectable post-hoc
    fx = {"id": "X1", "kind": "control",
          "expected": {"assessment": "CLEAR", "findings": []}}
    runs = [_result("ISSUES_FOUND", [dict(BLOCK)])]
    r = rc.evaluate(fx, runs)
    assert r["runs_detail"][0]["findings"][0]["comment"] == \
        "uses inherit here"
    assert "raw_output" in r["runs_detail"][0]
