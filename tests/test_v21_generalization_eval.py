"""Phase-18D evaluation checks.

Executes the frozen 18C rerun procedure: the published 18D report is
bound EXACTLY to live `evaluate()` output (the only module that may
call the frozen Phase-17 verifier on the holdout), the reconciliation
halt gate is proven against the SHA-pinned 18B observations, and the
historical 18B record stays frozen by hash.
"""
import copy
import hashlib
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.v21_generalization_eval as eval_mod  # noqa: E402

HOLDOUT = REPO / "eval" / "evidence" / \
    "v21-contract-generalization-prereg-2026-09-22"
EVALDIR = REPO / "eval" / "evidence" / \
    "v21-contract-generalization-eval-2026-09-22"
FROZEN_18B_REPORT_SHA = ("a56235b59bd104f9a6d868fad67d6ea1fe65f01a4987d"
                         "f02e257031e05587eec")
FROZEN_18D_REPORT_SHA = ("0a2bb7fa64be61a4c6b1f4b00b63c53a758fe1fed5d2"
                         "1fd169d067011af8dc26")
AMENDED_IDS = ("psd-P4", "psd-C4", "jfu-P5", "jfu-C5")


def _fixture(fid):
    return json.loads((HOLDOUT / "fixtures" / (fid + ".json")).read_text())


def test_published_18d_report_matches_evaluator_exactly():
    raw = (EVALDIR / "generalization-report-18d.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FROZEN_18D_REPORT_SHA
    published = json.loads(raw)
    live = eval_mod.evaluate()
    assert published == live


def test_18d_verdicts_and_reconciliation():
    report = json.loads(
        (EVALDIR / "generalization-report-18d.json").read_text())
    assert report["phase"] == "18D"
    verdicts = {name: rec["verdict"]
                for name, rec in report["per_relation"].items()}
    assert verdicts == {
        "pinned_sha_demoted_to_branch": "GENERALIZATION_PASS",
        "preserved_claim_vs_dropped_call_result": "GENERALIZATION_FAIL",
        "consume_before_validate_ordering": "GENERALIZATION_FAIL",
        "secret_logged_by_echo": "GENERALIZATION_FAIL",
        "doc_self_contradiction": "GENERALIZATION_FAIL",
        "jsonl_format_vs_unslurped_jq": "GENERALIZATION_FAIL",
    }
    psd = report["per_relation"]["pinned_sha_demoted_to_branch"]
    assert psd["positives_admitted"] == 5 and psd["controls_admitted"] == 0
    jfu = report["per_relation"]["jsonl_format_vs_unslurped_jq"]
    assert jfu["positives_admitted"] == 3 and jfu["controls_admitted"] == 0
    assert jfu["failed_positive_ids"] == ["jfu-P2", "jfu-P5"]
    aggregate = report["aggregate"]
    assert aggregate["positives_admitted"] == 17
    assert aggregate["controls_admitted"] == 3
    assert aggregate["relations_pass"] == 1
    assert aggregate["relations_fail"] == 5
    assert aggregate["all_pass"] is False
    assert aggregate["blanket_promotion_eligible"] is False
    reconciliation = report["reconciliation"]
    assert reconciliation["frozen_18b_report_sha256"] == \
        FROZEN_18B_REPORT_SHA
    assert reconciliation["unchanged_fixture_count"] == 56
    assert reconciliation["mismatches"] == []


def test_18d_amended_pair_observations():
    report = json.loads(
        (EVALDIR / "generalization-report-18d.json").read_text())
    rows = {r["id"]: r for r in report["fixture_rows"]}
    observed = {
        "psd-P4": (True, ["pinned_sha_demoted_to_branch"]),
        "psd-C4": (False, []),
        "jfu-P5": (False, []),
        "jfu-C5": (False, []),
    }
    for fid, (admitted, fired) in observed.items():
        row = rows[fid]
        assert row["amended"] is True
        assert row["admitted"] is admitted
        assert row["fired_relations"] == fired
    step1 = eval_mod.evaluate_amended_pairs()
    assert [(r["id"], r["admitted"]) for r in step1] == [
        ("jfu-C5", False), ("jfu-P5", False),
        ("psd-C4", False), ("psd-P4", True)]


def test_frozen_18b_report_is_unchanged():
    raw = (EVALDIR / "generalization-report.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FROZEN_18B_REPORT_SHA
    report = json.loads(raw)
    assert report["phase"] == "18B"
    assert report["aggregate"]["relations_pass"] == 0
    assert report["aggregate"]["relations_fail"] == 4
    assert report["aggregate"]["relations_invalid"] == 2
    assert report["aggregate"]["positives_admitted"] == 16
    assert report["aggregate"]["controls_admitted"] == 3
    verdicts = {name: rec["verdict"]
                for name, rec in report["per_relation"].items()}
    assert verdicts == {
        "pinned_sha_demoted_to_branch": "INVALID_PENDING_AMENDMENT",
        "preserved_claim_vs_dropped_call_result": "GENERALIZATION_FAIL",
        "consume_before_validate_ordering": "GENERALIZATION_FAIL",
        "secret_logged_by_echo": "GENERALIZATION_FAIL",
        "doc_self_contradiction": "GENERALIZATION_FAIL",
        "jsonl_format_vs_unslurped_jq": "INVALID_PENDING_AMENDMENT",
    }


def test_amended_psd_pair_has_genuine_40_hex_refs():
    for fid in ("psd-P4", "psd-C4"):
        fixture = _fixture(fid)
        patch = fixture["fixture"]["input"]["files"][0]["patch"]
        runs = re.findall(r"[0-9a-fA-F]{10,}", patch)
        assert runs and all(len(run) == 40 for run in runs), fid
        assert "uses: acme/shared-ci/.github/workflows/" in patch
        assert fixture["expected_label"] == (
            "ADMITS" if fid == "psd-P4" else "REFUSES")
    positive = _fixture("psd-P4")["fixture"]["input"]["files"][0]["patch"]
    control = _fixture("psd-C4")["fixture"]["input"]["files"][0]["patch"]
    assert "@main" in positive and "@main" not in control
    assert "test.yml@f2a3b4c5d6e7f8091a2b3c4d5e6f7a8b9c0d1e2f" in control


def test_amended_jfu_pair_matches_frozen_definition():
    positive = _fixture("jfu-P5")
    control = _fixture("jfu-C5")
    pos_patch = positive["fixture"]["input"]["files"][0]["patch"]
    ctl_patch = control["fixture"]["input"]["files"][0]["patch"]
    for fid, patch, label in (("jfu-P5", pos_patch, "ADMITS"),
                              ("jfu-C5", ctl_patch, "REFUSES")):
        assert re.search(r"jq\s+-\w*c[^\n]*>>\"\$?stages_jsonl\"", patch), fid
        assert re.search(
            r"jq\s+(?:-s\s+)?-e\s+'any\(\.\[\]; \.failed\)'",
            patch), fid
        assert 'stages_jsonl' in patch, fid
        assert _fixture(fid)["expected_label"] == label
    # the pair differs only in the semantic feature: slurp
    assert "jq -s -e 'any(.[]; .failed)'" in ctl_patch
    assert "jq -e 'any(.[]; .failed)'" in pos_patch
    assert "-s" not in pos_patch.split("any(.[]")[0].splitlines()[-1]
    assert positive["probe"] is False and control["probe"] is False


def test_manifest_records_amendment_and_hashes_match():
    manifest = json.loads((HOLDOUT / "MANIFEST.json").read_text())
    amendments = manifest["amendments"]
    assert len(amendments) == 1
    record = amendments[0]
    assert record["amendment"] == "18C"
    assert record["authorized_by"].startswith(
        "human merge review of PR #95")
    pairs = {pair["pair"] for pair in record["pairs"]}
    assert pairs == {"psd-P4/psd-C4", "jfu-P5/jfu-C5"}
    assert sorted(record["hashes_refreshed"]) == sorted(AMENDED_IDS)
    for entry in manifest["fixtures"]:
        raw = (HOLDOUT / "fixtures" / (entry["id"] + ".json")).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    entries = sorted(manifest["fixtures"], key=lambda e: e["id"])
    lines = ["%s  %s" % (e["sha256"], e["id"]) for e in entries]
    digest = hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()
    assert digest == manifest["manifest_lines_sha256"]


def test_fail_closed_integrity_and_verifier_identity():
    manifest = json.loads((HOLDOUT / "MANIFEST.json").read_text())
    eval_mod._fail_closed(manifest)
    # fail-closed also rejects a tampered verifier pin
    tampered = copy.deepcopy(manifest)
    tampered["frozen_verifier"]["module_sha256"] = "0" * 64
    try:
        eval_mod._fail_closed(tampered)
    except RuntimeError as exc:
        assert "different verifier module" in str(exc)
    else:
        raise AssertionError("drifted verifier identity was accepted")
    # the corrected-state proofs hold
    amendments = eval_mod._amendments()
    assert set(amendments) == {"psd-P4", "jfu-P5"}
    assert amendments["psd-P4"]["proof"]["all_refs_are_40_hex"] is True
    assert amendments["psd-P4"]["proof"][
        "all_hex_ref_lengths_by_fixture"] == {
            "psd-P4": [40, 40],
            "psd-C4": [40, 40, 40],
        }
    assert amendments["jfu-P5"]["proof"]["array_filter_present"] is True


def test_18d_reconciliation_gate_halts_on_divergence():
    frozen = json.loads((EVALDIR / "generalization-report.json").read_text())
    rows = [
        {
            "id": row["id"],
            "admitted": row["admitted"],
            "fired_relations": row["fired_relations"],
        }
        for row in frozen["fixture_rows"]
    ]
    amended = set(AMENDED_IDS)

    result = eval_mod._reconcile_unchanged(rows, amended)
    assert result["unchanged_fixture_count"] == 56
    assert result["mismatches"] == []

    tampered = copy.deepcopy(rows)
    target = next(row for row in tampered if row["id"] not in amended)
    target["admitted"] = not target["admitted"]
    try:
        eval_mod._reconcile_unchanged(tampered, amended)
    except RuntimeError as exc:
        assert "18D reconciliation halt" in str(exc)
        assert target["id"] in str(exc)
    else:
        raise AssertionError("unchanged-fixture divergence did not halt")


def test_results_18d_document_freezes_scope_and_humility():
    results = (EVALDIR / "RESULTS-18D.md").read_text()
    assert "GENERALIZATION PASS" in results
    assert "1 PASS, 5 FAIL" in results
    assert "56 unchanged fixtures" in results
    assert "Zero mismatches" in results
    assert "17/30 positives admitted, 3/30 controls admitted" in results
    assert "guard polarity" in results
    assert "no relation may be changed in response to" in results
    assert "no blanket promotion" in results
    assert "byte-for-byte" in results
