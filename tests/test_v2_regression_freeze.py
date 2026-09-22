"""v2 declaration regression freeze (post-trial, Phase 14).

Pins the exact parser/gate behavior on the five adjudicated trial
outcomes BEFORE any v2.1 design work. Zero provider calls; the oracle
is asserted untouched. See eval/evidence/
v2-declaration-regression-freeze-2026-09-22/PREREGISTRATION.md for
the freeze rule: any behavior change on these inputs fails this suite;
intentional flips require a reviewed amendment naming the cases.
"""
import hashlib
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import eval.run_corpus as rc  # noqa: E402
import parse_review as pr  # noqa: E402

TRIAL = REPO / "eval" / "evidence" / "v2-trial-glm-2026-09-22"
FREEZE = REPO / "eval" / "evidence" \
    / "v2-declaration-regression-freeze-2026-09-22"
CORPUS = {f["id"]: f for f in rc.load_corpus(REPO / "eval" / "fixtures")}
CASES = sorted((FREEZE / "cases").glob("*.json"))
TRIAL_LINES = (TRIAL / "records.jsonl").read_text().splitlines()
TRIAL_BY_SHA = {hashlib.sha256(l.encode()).hexdigest(): json.loads(l)
                for l in TRIAL_LINES}


def _diff(fid):
    return {f["path"]: f["patch"] for f in CORPUS[fid]["input"]["files"]}


@pytest.fixture(params=CASES, ids=lambda p: p.stem)
def case(request):
    return json.loads(request.param.read_text())


def test_freeze_contains_exactly_the_five_adjudicated_cases():
    ids = {c["case_id"] for c in (json.loads(p.read_text()) for p in CASES)}
    assert ids == {
        "C11-fabricated-contract-contradiction",
        "M3-context-only-evidence-quote",
        "M13-external-fact-extrapolation",
        "C12-honest-uncertainty-downgrade",
        "M12-contiguous-quote-downgrade",
    }
    failures = {c["case_id"] for c in map(_load, CASES)
                if c["class"] == "declaration_failure"}
    controls = {c["case_id"] for c in map(_load, CASES)
                if c["class"] == "good_boundary_control"}
    assert len(failures) == 3 and len(controls) == 2


def _load(path):
    return json.loads(path.read_text())


def test_case_links_to_published_record_verbatim(case):
    rec = TRIAL_BY_SHA.get(case["source"]["record_line_sha256"])
    assert rec is not None, "case must derive from a published record"
    assert rec["fixture"] == case["fixture"]
    assert rec["raw_model_output"] == case["raw_model_output"]


def test_normalized_result_is_frozen_exactly(case):
    result, audit = pr.normalize_v2(
        case["raw_model_output"], _diff(case["fixture"]), gate=True)
    assert result == case["expected_result"]
    assert audit == case["expected_gate_audit"]


def test_oracle_group_match_fact_is_pinned(case):
    """M3/M12 true; M13 false — the @v4 defect was missed even though
    a blocker survived. Controls are unpinned (empty oracle groups)."""
    fid = case["fixture"]
    if case["oracle_group_matched"] is None:
        assert fid in ("C11", "C12")
        assert CORPUS[fid]["expected"]["assessment"] == "CLEAR"
        return
    matched = False
    for g in CORPUS[fid]["expected"]["groups"]:
        for alt in g["alternatives"]:
            for f in case["expected_result"]["findings"]:
                if f["severity"] == "blocking" \
                        and rc._finding_matches(alt, f):
                    matched = True
    assert matched is case["oracle_group_matched"], fid


def test_declaration_failures_survive_and_controls_downgrade(case):
    """The load-bearing pattern, independent of exact dicts: the three
    adjudicated declaration failures mechanically SURVIVE the gate
    (the honest limit the honesty audit exists for), and the two good
    controls are correctly downgraded."""
    result = case["expected_result"]
    survivors = [f for f in result["findings"]
                 if f["severity"] == "blocking"]
    downgraded = [f for f in result["findings"]
                  if f.get("machine_reason")
                  == "BLOCKING_EVIDENCE_INSUFFICIENT"]
    if case["class"] == "declaration_failure":
        assert len(survivors) == 1 and not downgraded
    else:
        assert len(downgraded) == 1
        if case["fixture"] == "C12":
            assert result["assessment"] == "CLEAR"
            assert result["assessment_recomputed"] is True
        else:  # M12 keeps its HONEST survivor
            assert result["assessment"] == "ISSUES_FOUND"
            assert len(survivors) == 1


def test_freeze_does_not_move_oracle_identity():
    """The freeze is subject-side; the corpus, states, and GATING
    ratchet are untouched."""
    assert rc.oracle_version() == "117b4164e5446f50"
