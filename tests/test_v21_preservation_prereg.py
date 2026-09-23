"""Phase-22A preservation-authority preregistration checks.

The qualification framework is frozen BEFORE any candidate exists.
These tests pin QUALIFICATION_CONTRACT.json against live reality,
re-derive every frozen population mechanically (including the
anti-targets), verify the authority separation against the merged
18D/19B/21A/21B records, and assert no candidate module exists yet.
"""
import hashlib
import json
import pathlib
import sys
from collections import Counter

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.evidence_boundary_sim as boundary  # noqa: E402
import eval.v21_generalization_eval as gen  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import eval.v21_contract_relations as frozen  # noqa: E402
import eval.v21_replay as v21  # noqa: E402
import eval.v21_routes_replay as rr  # noqa: E402

PREREG = REPO / "eval" / "evidence" / \
    "v21-preservation-authority-prereg-2026-09-23"
CONTRACT = json.loads(
    (PREREG / "QUALIFICATION_CONTRACT.json").read_text())
PSD = "pinned_sha_demoted_to_branch"


def _rows():
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
                rows.append({
                    "role": v21._role(finding, fixture),
                    "route": rr.route_of(finding, fixture, sim),
                    "g2": sim["g2_contract_aware"],
                    "preds": v21.predicate_names(finding, fixture),
                    "rels": set(frozen.relation_names(finding,
                                                      fixture)),
                    "fixture": fixture["id"],
                    "source": source, "ri": ri, "fi": fi,
                })
    return rows


def test_contract_pins_and_status():
    assert CONTRACT["status"] == \
        "preregistration-only-no-candidate-no-execution"
    assert CONTRACT["preregistered_before_any_candidate_exists"] is True
    assert CONTRACT["pins"]["oracle_version"] == rc.oracle_version()
    assert CONTRACT["pins"]["frozen_verifier_module_sha256"] == \
        hashlib.sha256(
            (REPO / "eval" / "v21_contract_relations.py")
            .read_bytes()).hexdigest()
    assert CONTRACT["pins"]["18d_report_sha256"] == hashlib.sha256(
        (REPO / "eval" / "evidence" /
         "v21-contract-generalization-eval-2026-09-22" /
         "generalization-report-18d.json").read_bytes()).hexdigest()
    assert CONTRACT["pins"]["21a_contract_sha256"] == hashlib.sha256(
        (REPO / "eval" / "evidence" /
         "v21-false-blocker-prereg-2026-09-23" /
         "REDUCTION_CONTRACT.json").read_bytes()).hexdigest()
    assert (REPO / CONTRACT["pins"]["21b_policy_design_json"]).exists()
    assert set(CONTRACT["qualification_gates"]) == {
        "QG1_corpus_pair_discipline", "QG2_holdout",
        "QG3_independence", "QG4_standing_guards",
        "QG5_human_acceptance"}


def test_authority_separation():
    auth = CONTRACT["authorities"]
    assert auth["admission"]["current_holders"] == [PSD]
    assert auth["preservation"]["current_holders"] == []
    assert "never creates a block" in auth["preservation"]["grant_scope"]
    assert "never admits" in auth["preservation"]["grant_scope"]


def test_no_candidate_exists_yet():
    assert not (REPO / "eval" / "v21_m4_relation.py").exists()
    assert not list((REPO / "eval" / "evidence").glob(
        "v21-m4-relation-*"))
    assert not list((REPO / "eval" / "evidence").glob(
        "v21-preservation-qualification-*"))


def test_affected_populations_rederived():
    rows = _rows()
    surv = [r for r in rows if r["g2"] == "BLOCK_SURVIVES"]
    relcarried = sorted(
        (r["fixture"], r["source"], r["ri"], r["fi"])
        for r in surv
        if r["role"] == "true_positive_detection"
        and r["route"] == "contract_contradiction"
        and not r["preds"]
        and not (r["rels"] & {PSD}) and r["rels"])
    pop = CONTRACT["affected_populations"]
    assert len(relcarried) == pop["P_RELCARRIED"]["rows"] == 24
    per_rel = Counter()
    for r in surv:
        if (r["role"] == "true_positive_detection"
                and r["route"] == "contract_contradiction"
                and not r["preds"]
                and not (r["rels"] & {PSD}) and r["rels"]):
            # The frozen 24-row breakdown must not silently assign
            # multi-relation rows to an arbitrary alphabetic first.
            assert len(r["rels"]) == 1, (r["fixture"], r["source"],
                                         r["ri"], r["fi"], r["rels"])
            per_rel[next(iter(r["rels"]))] += 1
    assert dict(per_rel) == pop["P_RELCARRIED"]["per_relation"]
    assert sum(per_rel.values()) == 24
    p_m4 = pop["P_M4"]
    m4_surv = [r for r in surv if r["fixture"] == "M4"
               and r["role"] == "true_positive_detection"
               and r["route"] == "contract_contradiction"
               and not r["preds"] and not r["rels"]]
    assert sorted((r["source"], r["ri"], r["fi"])
                  for r in m4_surv) == sorted(
        tuple(x[2:]) for x in p_m4["ids"])
    # b1-low r29 (unwitnessed route) is explicitly not a target
    r29s = [r for r in rows if r["fixture"] == "M4"
            and r["source"] == "b1-low" and r["ri"] == 29]
    assert len(r29s) == 1, "M4 b1-low r29 identity changed"
    r29 = r29s[0]
    assert r29["route"] == "unwitnessed_behavior"
    assert r29["g2"] == "BLOCK_SURVIVES"
    # anti-targets
    bare = [r for r in surv if not r["preds"] and not r["rels"]]
    bare_controls = [r for r in bare
                     if r["role"] == "control_blocker"]
    non_contract = [r for r in bare_controls
                    if r["route"] != "contract_contradiction"]
    controls = [r for r in rows if r["role"] == "control_blocker"]
    extras = [r for r in rows if r["role"] == "positive_extra_blocker"]
    surviving_extras = [r for r in surv
                        if r["role"] == "positive_extra_blocker"]
    assert pop["anti_targets"]["control_blockers_all_corpus"] == \
        len(controls) == 77
    assert pop["anti_targets"]["bare_controls_corpus_wide"] == \
        len(bare_controls) == 26
    assert pop["anti_targets"]["bare_controls_non_contract"] == \
        len(non_contract) == 11
    assert pop["anti_targets"]["positive_extra_blockers_all_corpus"] == \
        len(extras) == 34
    assert pop["anti_targets"]["positive_extra_blockers_g2_survivors"] == \
        len(surviving_extras) == 7


def test_slate_order_and_gate_bindings():
    slate = CONTRACT["candidate_slate"]
    assert [c["order"] for c in slate] == [1, 2, 3, 4, 5, 6, 7]
    assert slate[0]["name"] == "m4rel"
    assert slate[0]["targets"] == "P_M4"
    dsc = next(c for c in slate if c["name"] == "dsc-prime")
    assert dsc["must_not_fire"] == ["dsc-C1", "dsc-C2"]
    assert dsc["carries"] == "PC2"
    sle = next(c for c in slate if c["name"] == "sle-prime")
    assert sle["must_not_fire"] == ["sle-C3"]
    assert sle["targets"].startswith("UNSPECIFIED; zero sle-attributed")
    assert "secret_logged_by_echo" not in CONTRACT[
        "affected_populations"]["P_RELCARRIED"]["per_relation"]
    assert "disjoint" in sle["targets"]
    m10 = next(c for c in slate if c["name"] == "m10-prime")
    assert m10["must_clear"] == "C10 standing near-miss"
    # T3 membership agrees with the merged 18D report
    r18d = json.loads(
        (REPO / "eval" / "evidence" /
         "v21-contract-generalization-eval-2026-09-22" /
         "generalization-report-18d.json").read_text())
    for name, rec in r18d["per_relation"].items():
        if name == PSD:
            assert rec["verdict"] == "GENERALIZATION_PASS"
        else:
            assert rec["verdict"] == "GENERALIZATION_FAIL"


def test_dsc_p4_and_holdout_antitargets_are_actual_frozen_rows():
    hold_dir = (REPO / "eval" / "evidence" /
                "v21-contract-generalization-prereg-2026-09-22")
    manifest = json.loads((hold_dir / "MANIFEST.json").read_text())
    controls = [e for e in manifest["fixtures"] if e["role"] == "control"]
    assert len(manifest["fixtures"]) == 60
    assert len(controls) == 30
    f = json.loads((hold_dir / "fixtures" / "dsc-P4.json").read_text())
    assert f["role"] == "positive" and f["expected_label"] == "ADMITS"
    finding, fixture = f["finding"], f["fixture"]
    sim = boundary.simulate_finding(finding, fixture)
    assert sim["g2_contract_aware"] == "BLOCK_SURVIVES"
    assert rr.route_of(finding, fixture, sim) == "contract_contradiction"
    assert not v21.predicate_names(finding, fixture)
    assert not frozen.relation_names(finding, fixture)


def test_standing_guards_and_candidate_specific_freeze():
    guards = gen._regression_guards()
    assert guards == {
        "oracle": "117b4164e5446f50",
        "C11_refused": True,
        "M3_admitted_via_existing_witness": True,
        "M13_refused": True,
        "C12_refused": True,
        "M12_refused": True,
        "M10_relation_still_FAILED": True,
        "C10_standing_near_miss": True,
    }
    gates = CONTRACT["qualification_gates"]
    assert "77" in gates["QG1_corpus_pair_discipline"]
    assert "34" in gates["QG1_corpus_pair_discipline"]
    assert "zero extra-blocker preservation" in gates[
        "QG1_corpus_pair_discipline"]
    assert "30 existing holdout controls" in gates["QG2_holdout"]
    assert "fresh independently authored" in gates["QG2_holdout"]
    assert "before first run" in gates["QG2_holdout"]
    assert "review near-miss behavior and source" in (
        PREREG / "PROTOCOL.md").read_text()
    assert "explicit human" in gates["QG5_human_acceptance"]
    assert "freeze exact target ids and disjoint ownership" in \
        CONTRACT["candidate_specific_preregistration_required"]


def test_protocol_freezes_framework_language():
    protocol = (PREREG / "PROTOCOL.md").read_text()
    for phrase in ("preregistration only",
                   "No evidence currently",
                   "never creates a block",
                   "remediation validation, NOT",
                   "auto-excluded",
                   "never tuned",
                   "Agents never",
                   "Anti-targets", "ALL **77 corpus",
                   "zero extra blockers gain preservation",
                   "ZERO of the 77",
                   "bb0ebdee",
                   "117b4164e5446f50"):
        assert phrase in protocol, phrase
