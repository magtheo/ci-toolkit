"""Offline Phase-15 v2.1 candidate-mechanism replay."""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.v21_replay as replay  # noqa: E402


def test_replay_is_frozen_and_complete():
    report = replay.replay()
    assert report["oracle_version"] == "117b4164e5446f50"
    assert len(report["phase09"]["rows"]) == 276
    assert report["phase09"]["summary"] == {
        "quote_only": {
            "control_blocker": {"admitted": 27, "total": 77},
            "true_positive_detection": {"admitted": 111, "total": 165},
            "positive_extra_blocker": {"admitted": 7, "total": 34},
        },
        "closed_world_predicates": {
            "control_blocker": {"admitted": 0, "total": 77},
            "true_positive_detection": {"admitted": 50, "total": 165},
            "positive_extra_blocker": {"admitted": 2, "total": 34},
        },
    }


def test_frozen_five_case_projection_is_pinned():
    cases = {r["case_id"]: r for r in replay.replay()["frozen_cases"]}
    assert cases["C11-fabricated-contract-contradiction"] == {
        "case_id": "C11-fabricated-contract-contradiction",
        "fixture": "C11", "class": "declaration_failure",
        "quote_only": True, "closed_world_predicates": False,
        "predicates": [],
    }
    assert cases["M3-context-only-evidence-quote"]["closed_world_predicates"]
    assert cases["M3-context-only-evidence-quote"]["predicates"] == [
        "parsed_date_vs_mtime"]
    assert cases["M13-external-fact-extrapolation"] == {
        "case_id": "M13-external-fact-extrapolation",
        "fixture": "M13", "class": "declaration_failure",
        "quote_only": True, "closed_world_predicates": False,
        "predicates": [],
    }
    for key in ("C12-honest-uncertainty-downgrade",
                "M12-contiguous-quote-downgrade"):
        assert cases[key]["quote_only"] is False
        assert cases[key]["closed_world_predicates"] is False


def test_predicate_registry_does_not_confuse_c11_with_m11():
    fixtures = {f["id"]: f for f in replay.rc.load_corpus(
        REPO / "eval" / "fixtures")}
    c11 = {"comment": "the wrapper loses check failures and reports success"}
    m11 = {"comment": "the status is hardcoded success and discards outcome"}
    assert "hardcoded_success_status" not in replay.predicate_names(
        c11, fixtures["C11"])
    assert "hardcoded_success_status" in replay.predicate_names(
        m11, fixtures["M11"])
