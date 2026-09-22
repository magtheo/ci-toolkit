"""Offline Phase-17 contract-relation study (protocol-pinned)."""
import pathlib
import sys
from collections import Counter

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.v21_contract_relations as relations  # noqa: E402


def _report():
    return relations.replay()


def test_population_and_pair_discipline_holds():
    report = _report()
    assert report["oracle_version"] == "117b4164e5446f50"
    assert len(report["phase09"]["rows"]) == 276
    gs = report["phase09"]["gate_summary"]
    assert gs["route_typed"] == {
        "control_blocker": {"admitted": 0, "total": 77},
        "true_positive_detection": {"admitted": 50, "total": 165},
        "positive_extra_blocker": {"admitted": 2, "total": 34},
    }
    assert gs["candidate"] == {
        "control_blocker": {"admitted": 0, "total": 77},
        "true_positive_detection": {"admitted": 74, "total": 165},
        "positive_extra_blocker": {"admitted": 2, "total": 34},
    }
    contract = report["phase09"]["contract_route_summary"]
    assert contract["route_typed"] == {
        "control_blocker": {"admitted": 0, "total": 35},
        "true_positive_detection": {"admitted": 29, "total": 68},
        "positive_extra_blocker": {"admitted": 1, "total": 22},
    }
    assert contract["candidate"] == {
        "control_blocker": {"admitted": 0, "total": 35},
        "true_positive_detection": {"admitted": 53, "total": 68},
        "positive_extra_blocker": {"admitted": 1, "total": 22},
    }


def test_per_relation_verdicts_are_pinned():
    info = _report()["phase09"]["relations"]
    failed = "doc_contract_prefix_unanchored_match"
    assert info[failed]["eligible"] is False
    assert info[failed]["control_fixtures"] == ["C10"]
    eligible = {
        "pinned_sha_demoted_to_branch": (["M2"], 0),
        "preserved_claim_vs_dropped_call_result": (["M7"], 1),
        "consume_before_validate_ordering": (["M8"], 0),
        "secret_logged_by_echo": (["M14"], 0),
        "doc_self_contradiction": (["M17", "M18"], 0),
        "jsonl_format_vs_unslurped_jq": (["M6"], 0),
    }
    for name, (fixtures, extras) in eligible.items():
        assert info[name]["eligible"] is True, name
        assert info[name]["tp_fixtures"] == fixtures, name
        assert info[name]["extra_rows"] == extras, name
    assert set(_report()["phase09"]["eligible"]) == set(eligible)


def test_newly_admitted_rows_are_exactly_pinned():
    rows = _report()["phase09"]["rows"]
    new = Counter((r["fixture"], r["role"]) for r in rows
                  if r["candidate"] and not r["route_typed"])
    assert new == Counter({
        ("M18", "true_positive_detection"): 7,
        ("M7", "true_positive_detection"): 7,
        ("M8", "true_positive_detection"): 5,
        ("M17", "true_positive_detection"): 2,
        ("M6", "true_positive_detection"): 2,
        ("M2", "true_positive_detection"): 1,
    })
    assert not any(r["candidate"] for r in rows
                   if r["role"] == "control_blocker")


def test_frozen_five_invariants_hold():
    cases = {c["case_id"]: c for c in _report()["frozen_cases"]}
    assert cases["M3-context-only-evidence-quote"]["candidate_admitted"]
    assert cases["M3-context-only-evidence-quote"]["reason"] == \
        "existing registry witness: parsed_date_vs_mtime"
    assert cases["C11-fabricated-contract-contradiction"]["reason"] == \
        "no eligible relation verifier"
    for key in ("C11-fabricated-contract-contradiction",
                "M13-external-fact-extrapolation",
                "C12-honest-uncertainty-downgrade",
                "M12-contiguous-quote-downgrade"):
        assert cases[key]["candidate_admitted"] is False


def _fixture(patch, path="core/rules.py"):
    return {"input": {"files": [{"path": path, "patch": patch}]}}


def test_failed_m10_relation_cannot_separate_c10():
    # The preregistered wording listed re.match among "unanchored"
    # functions; re.match is anchored by definition. The module
    # implements the preregistered behavior faithfully, so it fires on
    # BOTH the M10 defect and the C10 near-miss control -- which is
    # exactly why the pair test recorded the relation FAILED and the
    # candidate gate excluded it.
    claim = "bypass of the privileged lane"
    doc = '"""Only refs under feature/ may run the privileged lane."""'
    finding = {"file": "core/rules.py", "comment": claim}
    for code in ("re.search(r\"feature/\", ref)",
                 "re.match(r\"feature/\", ref)"):
        assert "doc_contract_prefix_unanchored_match" in \
            relations.relation_names(finding, _fixture("+" + doc +
                                                       "\n+return " + code))
    assert "doc_contract_prefix_unanchored_match" not in \
        _report()["phase09"]["eligible"]
