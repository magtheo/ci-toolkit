"""Phase-19B evaluation checks.

The published 19B report is bound EXACTLY to live `evaluate()` output
(the only module that may execute the frozen promotion rule), and the
frozen predictions, zero-collateral gate, and guard results are
pinned. Complements the 19A preregistration tests.
"""
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.v21_psd_promotion as pp  # noqa: E402

EVALDIR = REPO / "eval" / "evidence" / "v21-psd-promotion-eval-2026-09-23"
FROZEN_19B_REPORT_SHA = ("9f0c15ec4ec8935e16ed6e2b1503b39c62e69f4ea0926"
                         "dcb698941f067134906")


def test_published_19b_report_matches_evaluator_exactly():
    raw = (EVALDIR / "psd-promotion-report.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FROZEN_19B_REPORT_SHA
    published = json.loads(raw)
    live = pp.evaluate()
    assert published == live


def test_19b_outcome_matches_frozen_predictions():
    report = json.loads((EVALDIR / "psd-promotion-report.json")
                        .read_text())
    assert report["phase"] == "19B"
    assert report["population"] == 276
    assert report["baseline_aggregate"] == {"BLOCK_SURVIVES": 145,
                                            "DOWNGRADE": 131}
    assert report["integrated_aggregate"] == {
        "BLOCK_EVIDENCE_BACKED": 1,
        "BLOCK_SURVIVES": 145,
        "DOWNGRADE": 130,
    }
    assert report["unchanged_rows"] == 275
    assert report["collateral_changes"] == []
    assert report["control_or_extra_promotions"] == []
    assert report["success"] is True
    promotion = report["promotion_set"]
    assert len(promotion) == 1
    row = promotion[0]
    assert row["source"] == "stage-a-max"
    assert row["record_index"] == 28
    assert row["finding_index"] == 0
    assert row["fixture"] == "M2"
    assert row["route"] == "contract_contradiction"
    assert row["role"] == "true_positive_detection"
    assert row["g1_strict_quote"] == "DOWNGRADE"
    assert row["baseline"] == "DOWNGRADE"
    assert row["integrated"] == "BLOCK_EVIDENCE_BACKED"
    assert row["fired_relations"] == ["pinned_sha_demoted_to_branch"]
    landscape = report["landscape_observed"]
    assert landscape["psd_fires_on"] == 24
    assert landscape["downgraded_psd_fired_by_route"] == {
        "contract_contradiction": 1,
        "external_fact": 12,
        "unwitnessed_behavior": 6,
    }


def test_19b_prereg_binding_and_artifact_integrity():
    report = json.loads((EVALDIR / "psd-promotion-report.json")
                        .read_text())
    prereg = report["prereg"]
    contract_raw = (REPO / prereg["contract"]).read_bytes()
    assert prereg["contract_sha256"] == hashlib.sha256(
        contract_raw).hexdigest()
    contract = json.loads(contract_raw)
    assert contract["phase"] == "19A"
    assert report["rule"] == contract["promotion_rule"]["condition"]
    assert report["frozen_verifier"] == {
        "merge_sha": contract["subject"]["verifier_merge_sha"],
        "module_sha256": contract["subject"]["verifier_module_sha256"],
    }
    historical = report["historical_artifacts_unchanged"]
    assert historical["generalization-report.json"] == (
        "a56235b59bd104f9a6d868fad67d6ea1fe65f01a4987df02e257031e0558"
        "7eec")
    assert historical["generalization-report-18d.json"] == (
        "0a2bb7fa64be61a4c6b1f4b00b63c53a758fe1fed5d21fd169d067011af8"
        "dc26")


def test_19b_guards_and_meaning():
    report = json.loads((EVALDIR / "psd-promotion-report.json")
                        .read_text())
    guards = report["standing_regression_guards"]
    assert guards["oracle"] == "117b4164e5446f50"
    for key in ("C11_refused", "M3_admitted_via_existing_witness",
                "M13_refused", "C12_refused", "M12_refused",
                "M10_relation_still_FAILED", "C10_standing_near_miss"):
        assert guards[key] is True
    meaning = report["meaning"]
    assert "does NOT authorize GATING activation" in meaning
    assert "27 surviving control blockers" in meaning
    assert "remain downgraded by design" in meaning
    results = (EVALDIR / "RESULTS-19B.md").read_text()
    assert "every frozen invariant held" in results
    assert "exactly 1" in results
    assert "byte-for-byte unchanged" in results
    assert "not a correctness claim about any" in results or \
        "humility rule" in results
