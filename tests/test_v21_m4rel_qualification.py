"""Phase-22D m4rel qualification record checks.

Pins the official qualification report and its provenance: verdict,
all gates, the preserved execution-1 HALT report, detector byte
identity across executions, interpretation language, and live
re-derivation of the corpus gates. The sealed holdout is NOT
re-executed here; its results are verified against the report and
the manifest only.
"""
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.evidence_boundary_sim as boundary  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import eval.v21_m4_relation as m4  # noqa: E402
import eval.v21_replay as v21  # noqa: E402
import eval.v21_routes_replay as rr  # noqa: E402

QUAL = REPO / "eval" / "evidence" / \
    "v21-m4rel-qualification-2026-09-23"
REPORT = json.loads((QUAL / "qualification-report.json").read_text())
EXEC1 = json.loads(
    (QUAL / "qualification-report.execution-1.json").read_text())
HOLDOUT_22B = REPO / "eval" / "evidence" / \
    "v21-m4rel-holdout-2026-09-23"
MANIFEST = json.loads((HOLDOUT_22B / "MANIFEST.json").read_text())
EVID_22C = json.loads(
    (REPO / "eval" / "evidence" /
     "v21-m4rel-implementation-2026-09-23" /
     "EVIDENCE.json").read_text())

MODULE_SHA = "1a01d8ff6f15fd050eb290da4f20a2d99dacb59ea183b0dc6b803c6004139596"
EXEC1_SHA = "b368b5a4dcb7dbd9113e60cfbd514c8e17447722e60ca8748beae85620a13aa2"


def _sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def test_verdict_and_gate_pins():
    assert REPORT["verdict"] == "SUCCESS"
    assert EXEC1["verdict"] == "HALT"
    assert set(REPORT["gates"]) == {
        "G1_corpus_targets", "G2_corpus_controls", "G3_extras",
        "G4_existing_holdout_controls",
        "G5_fresh_holdout_single_execution",
        "G6_standing_guards"}
    for name, gate in REPORT["gates"].items():
        assert gate["ok"] is True, name
    g5 = REPORT["gates"]["G5_fresh_holdout_single_execution"]
    assert g5["positives_fired"] == 6
    assert g5["positives_total"] == 6
    assert g5["controls_fired"] == 0
    assert g5["controls_total"] == 6
    assert REPORT["gates"]["G2_corpus_controls"]["fired"] == 0
    assert REPORT["gates"]["G2_corpus_controls"]["total"] == 77
    assert REPORT["gates"]["G1_corpus_targets"]["covered"] == 2
    assert REPORT["gates"]["G3_extras"]["claim_linked"] == 0
    assert REPORT["gates"]["G3_extras"]["total"] == 34
    assert REPORT["gates"]["G4_existing_holdout_controls"][
        "fired"] == 0
    assert REPORT["gates"]["G4_existing_holdout_controls"][
        "total"] == 30


def test_detector_byte_identity_across_executions():
    assert _sha(REPO / "eval" / "v21_m4_relation.py") == MODULE_SHA
    assert REPORT["pins"]["module_sha256_22c"] == MODULE_SHA
    assert EXEC1["pins"]["module_sha256_22c"] == MODULE_SHA
    assert EVID_22C["candidate"]["module_sha256"] == MODULE_SHA
    correction = REPORT["evaluator_correction"]
    assert correction["found_after_first_execution"] is True
    assert correction["detector_bytes_identical"] is True
    assert correction["fixture_level_outputs_identical"] is True
    assert correction["first_execution_verdict"] == "HALT"
    assert correction["first_execution_report_sha256"] == EXEC1_SHA
    assert _sha(QUAL /
                "qualification-report.execution-1.json") == EXEC1_SHA
    assert REPORT["execution"][
        "no_detector_changes_after_observation"] is True
    assert REPORT["execution"][
        "fresh_holdout_sanctioned_observation"] == 1
    assert REPORT["execution"][
        "fresh_holdout_deterministic_reexecutions"] == 3


def test_transition_binding():
    path = QUAL / "PHASE_TRANSITION.json"
    assert path.exists()
    assert REPORT["phase_transition"]["sha256"] == _sha(path)
    assert REPORT["phase_transition"]["parent_merge_sha"] == \
        "b518333175948896892e263a3880982ba96ea17e"
    transition = json.loads(path.read_text())
    assert "qualification-execution-authorized" in \
        transition["status"]
    assert "adoption-not-authorized" in transition["status"]
    assert "no-authority-grant" in transition["status"]
    assert transition["prerequisites"][
        "frozen_22c_module_sha256"] == MODULE_SHA


def test_execution_log_discipline():
    log = [json.loads(line) for line in
           (QUAL / "execution-log.jsonl")
           .read_text().splitlines() if line.strip()]
    assert [e["run_index"] for e in log] == [1, 2, 3, 4]
    assert [e["verdict"] for e in log] == [
        "HALT", "SUCCESS", "SUCCESS", "SUCCESS"]
    assert all(e["detector_sha256"] == MODULE_SHA for e in log)
    assert log[0]["reconstructed"] is True
    assert log[0]["report_sha256"] == EXEC1_SHA
    assert log[-1]["reconstructed"] is False
    assert log[-1]["report_sha256"] == \
        "a4ebaabac2dea4c662541f433aeb580bd91d301e45dde576ce3688eb4a422c1f"


def test_fixture_level_matches_manifest():
    g5 = REPORT["gates"]["G5_fresh_holdout_single_execution"]
    by_id = {f["id"]: f for f in g5["fixtures"]}
    assert set(by_id) == {e["id"] for e in MANIFEST["fixtures"]}
    for entry in MANIFEST["fixtures"]:
        rec = by_id[entry["id"]]
        assert rec["expected_label"] == entry["expected_label"]
        assert rec["role"] == entry["role"]
        expect_fire = entry["expected_label"] == "ADMITS"
        assert rec["fired"] is expect_fire
        assert rec["ok"] is True
    assert MANIFEST["counts"]["total"] == 12


def test_report_file_pins():
    assert _sha(QUAL / "qualification-report.json") == \
        "a4ebaabac2dea4c662541f433aeb580bd91d301e45dde576ce3688eb4a422c1f"
    assert REPORT["pins"]["22b_contract_sha256"] == _sha(
        REPO / "eval" / "evidence" /
        "v21-m4rel-prereg-2026-09-23" / "TARGETS_CONTRACT.json")
    assert REPORT["pins"]["22b_holdout_manifest_sha256"] == _sha(
        HOLDOUT_22B / "MANIFEST.json")
    assert REPORT["pins"]["18a_holdout_manifest_sha256"] == _sha(
        REPO / "eval" / "evidence" /
        "v21-contract-generalization-prereg-2026-09-22" /
        "MANIFEST.json")
    assert REPORT["pins"]["18d_report_sha256"] == _sha(
        REPO / "eval" / "evidence" /
        "v21-contract-generalization-eval-2026-09-22" /
        "generalization-report-18d.json")
    assert REPORT["pins"]["oracle_version"] == rc.oracle_version()
    assert REPORT["pins"]["frozen_verifier_module_sha256"] == _sha(
        REPO / "eval" / "v21_contract_relations.py")


def test_interpretation_language():
    interp = json.dumps(REPORT["interpretation"])
    assert "preregistered validation against the frozen holdout" \
        in interp
    assert "NOT vocabulary-independent generalization" in interp
    assert "no preservation authority granted" in interp
    assert "human adoption decision" in interp
    results = (QUAL / "RESULTS-22D.md").read_text()
    for phrase in ("Verdict: SUCCESS",
                   "preregistered validation against the frozen "
                   "holdout",
                   "no preservation authority is granted",
                   "Evaluator correction",
                   "b368b5a4",
                   "a4ebaaba",
                   "STOPPED for human review"):
        assert phrase in results, phrase


def test_corpus_gates_rederivable_live():
    fixtures = {f["id"]: f
                for f in rc.load_corpus(REPO / "eval" / "fixtures")}
    rows = []
    for source, rel in boundary.SOURCES.items():
        records = [json.loads(line)
                   for line in (REPO / rel).read_text().splitlines()
                   if line.strip()]
        for ri, rec in enumerate(records):
            fixture = fixtures[rec["fixture"]]
            for fi, finding in enumerate(
                    (rec.get("result") or {}).get("findings", [])):
                if finding.get("severity") != "blocking":
                    continue
                sim = boundary.simulate_finding(finding, fixture)
                rows.append(dict(
                    role=v21._role(finding, fixture),
                    route=rr.route_of(finding, fixture, sim),
                    g2=sim["g2_contract_aware"],
                    fixture=rec["fixture"], source=source,
                    ri=ri, fi=fi, finding=finding))
    targets = [r for r in rows if r["fixture"] == "M4"
               and r["role"] == "true_positive_detection"
               and r["route"] == "contract_contradiction"
               and r["g2"] == "BLOCK_SURVIVES"]
    assert len(targets) == 2
    assert all(m4.covers(r["finding"], fixtures["M4"])
               for r in targets)
    controls = [r for r in rows if r["role"] == "control_blocker"]
    assert len(controls) == 77
    assert not any(m4.covers(r["finding"], fixtures[r["fixture"]])
                   for r in controls)
