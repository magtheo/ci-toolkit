"""Phase-20 closeout checks.

Binds the psd qualification closeout record to live reality: every
referenced artifact hash is re-verified against disk, the report
summaries must agree with the record's claims, the oracle identity
must match the live corpus module, and the void conditions must be
mechanically checkable.
"""
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.run_corpus as rc  # noqa: E402
import eval.v21_generalization_eval as gen  # noqa: E402

CLOSEOUT = REPO / "eval" / "evidence" / \
    "v21-psd-qualification-closeout-2026-09-23"
RECORD = json.loads((CLOSEOUT / "RECORD.json").read_text())

VERIFIER = REPO / "eval" / "v21_contract_relations.py"
ARTIFACTS = {
    "generalization_report_18b_sha256": (
        REPO / "eval" / "evidence" /
        "v21-contract-generalization-eval-2026-09-22" /
        "generalization-report.json"),
    "generalization_report_18d_sha256": (
        REPO / "eval" / "evidence" /
        "v21-contract-generalization-eval-2026-09-22" /
        "generalization-report-18d.json"),
    "psd_promotion_report_sha256": (
        REPO / "eval" / "evidence" /
        "v21-psd-promotion-eval-2026-09-23" /
        "psd-promotion-report.json"),
    "integration_contract_sha256": (
        REPO / "eval" / "evidence" /
        "v21-psd-promotion-prereg-2026-09-23" /
        "INTEGRATION_CONTRACT.json"),
    "holdout_manifest_sha256": (
        REPO / "eval" / "evidence" /
        "v21-contract-generalization-prereg-2026-09-22" /
        "MANIFEST.json"),
}


EXPECTED_CHAIN = {
    "17": (93, "0631b0956f795ab1ee6d13f68b0c1cebe8a6d23b"),
    "18A": (94, "600f3a6e739053bdc5b06fd54c480c71dc572eca"),
    "18B": (95, "76e076f9a0b91df6ddafa3f3daca8fc940546424"),
    "18C": (96, "15cbdd114baa7f03c50d1ab6e0bdfac2f1c65c0e"),
    "18D": (97, "59656caeac9c00f4e5710f9db0821e7794224039"),
    "19A": (98, "00f8237ff0bfe5daef8535314df046b0038ac65b"),
    "19B": (99, "04db3e10c53ab053e2d1a4a4304f06c487ff75b4"),
}
EXPECTED_ARTIFACT_KEYS = {
    "17": set(),
    "18A": {"holdout_manifest_sha256", "manifest_lines_sha256"},
    "18B": {"generalization_report_18b_sha256"},
    "18C": set(),
    "18D": {"generalization_report_18d_sha256"},
    "19A": {"integration_contract_sha256"},
    "19B": {"psd_promotion_report_sha256"},
}


def test_record_subject_pins_match_live_reality():
    assert RECORD["status"] == \
        "EVIDENCE_BACKED_ELIGIBLE__CONTRACT_ROUTE_ONLY"
    assert RECORD["subject"]["relation"] == \
        "pinned_sha_demoted_to_branch"
    assert RECORD["subject"]["verifier_module_sha256"] == \
        hashlib.sha256(VERIFIER.read_bytes()).hexdigest()
    assert RECORD["subject"]["verifier_module_sha256"] == \
        "bb0ebdeeb7fc80395626bf10d3e9ad1a730936ccf0ab7e719c43c1b5754b" \
        "1b57"
    assert RECORD["subject"]["verifier_merge_sha"] == \
        "0631b0956f795ab1ee6d13f68b0c1cebe8a6d23b"
    assert RECORD["oracle_version"] == rc.oracle_version()


def test_every_referenced_artifact_hash_matches_disk():
    chain = {e["phase"]: e for e in RECORD["evidence_chain"]}
    assert len(chain) == len(RECORD["evidence_chain"]) == 7
    assert set(chain) == set(EXPECTED_CHAIN)
    for phase, (pr, sha) in EXPECTED_CHAIN.items():
        entry = chain[phase]
        assert (entry["pr"], entry["merge_sha"]) == (pr, sha)
        artifacts = entry.get("artifacts", {})
        assert set(artifacts) == EXPECTED_ARTIFACT_KEYS[phase]
        for key in EXPECTED_ARTIFACT_KEYS[phase] & set(ARTIFACTS):
            digest = hashlib.sha256(ARTIFACTS[key].read_bytes()).hexdigest()
            assert digest == artifacts[key], (phase, key)


def test_record_claims_agree_with_published_reports():
    holdout = json.loads((ARTIFACTS["holdout_manifest_sha256"])
                         .read_text())
    entries = sorted(holdout["fixtures"], key=lambda e: e["id"])
    assert len(entries) == 60
    fixture_dir = ARTIFACTS["holdout_manifest_sha256"].parent / "fixtures"
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids))
    assert {p.stem for p in fixture_dir.glob("*.json")} == set(ids)
    for entry in entries:
        raw = (fixture_dir / (entry["id"] + ".json")).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"], entry["id"]
    lines = ["%s  %s" % (e["sha256"], e["id"]) for e in entries]
    digest = hashlib.sha256(("\n".join(lines) + "\n")
                            .encode()).hexdigest()
    chain = {e["phase"]: e for e in RECORD["evidence_chain"]}
    assert digest == holdout["manifest_lines_sha256"]
    assert digest == chain["18A"]["artifacts"]["manifest_lines_sha256"]

    r18d = json.loads((ARTIFACTS["generalization_report_18d_sha256"])
                      .read_text())
    psd = r18d["per_relation"]["pinned_sha_demoted_to_branch"]
    assert psd["verdict"] == "GENERALIZATION_PASS"
    assert psd["positives_admitted"] == 5
    assert psd["controls_admitted"] == 0
    assert r18d["reconciliation"]["unchanged_fixture_count"] == 56
    assert r18d["reconciliation"]["mismatches"] == []

    r19b = json.loads((ARTIFACTS["psd_promotion_report_sha256"])
                      .read_text())
    assert r19b["success"] is True
    assert len(r19b["promotion_set"]) == 1
    assert r19b["promotion_set"][0]["fixture"] == "M2"
    assert r19b["unchanged_rows"] == 275
    assert r19b["collateral_changes"] == []
    assert r19b["control_or_extra_promotions"] == []
    assert r19b["integrated_aggregate"] == {
        "BLOCK_EVIDENCE_BACKED": 1,
        "BLOCK_SURVIVES": 145,
        "DOWNGRADE": 130,
    }
    contract = json.loads((ARTIFACTS["integration_contract_sha256"])
                          .read_text())
    assert r19b["rule"] == contract["promotion_rule"]["condition"]


def test_current_regression_guards_match_frozen_record():
    expected = {
        "oracle": "117b4164e5446f50",
        "C11_refused": True,
        "M3_admitted_via_existing_witness": True,
        "M13_refused": True,
        "C12_refused": True,
        "M12_refused": True,
        "M10_relation_still_FAILED": True,
        "C10_standing_near_miss": True,
    }
    # This executes the existing deterministic guards; it does not
    # invoke an external model or change any fixture/verifier bytes.
    guards = gen._regression_guards()
    assert guards == expected
    r19b = json.loads(ARTIFACTS["psd_promotion_report_sha256"].read_text())
    assert r19b["standing_regression_guards"] == guards


def test_non_claims_scope_and_exclusions():
    non_claims = " ".join(RECORD["non_claims"])
    for phrase in ("NOT a GATING activation",
                   "NOT a deployed reviewer change",
                   "does NOT promote the broader relation registry",
                   "27 surviving control blockers",
                   "downgraded by design",
                   "NOT a correctness claim"):
        assert phrase in non_claims
    assert RECORD["eligibility"]["route"] == "contract_contradiction"
    assert RECORD["eligibility"]["decision_value"] == \
        "BLOCK_EVIDENCE_BACKED"
    assert len(RECORD["invalidation_conditions"]) == 5
    assert len(RECORD["future_work_excluded_from_this_record"]) == 4
    assert "PENDING ACTIVATION" in \
        RECORD["deployment_contract_note"]


def test_qualification_document_is_reviewable_standalone():
    doc = (CLOSEOUT / "QUALIFICATION.md").read_text()
    for phrase in ("standalone, reviewable result",
                   "GENERALIZATION PASS: 5/5 positives, 0/5 controls",
                   "1 promotion, 275 decisions unchanged",
                   "Not a GATING activation",
                   "27 surviving control blockers",
                   "Void conditions",
                   "bb0ebdee",
                   "117b4164e5446f50"):
        assert phrase in doc
