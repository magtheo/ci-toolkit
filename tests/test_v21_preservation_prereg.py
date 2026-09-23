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
            per_rel[sorted(r["rels"])[0]] += 1
    assert dict(per_rel) == pop["P_RELCARRIED"]["per_relation"]
    p_m4 = pop["P_M4"]
    m4_surv = [r for r in surv if r["fixture"] == "M4"
               and r["role"] == "true_positive_detection"
               and r["route"] == "contract_contradiction"
               and not r["preds"] and not r["rels"]]
    assert sorted((r["source"], r["ri"], r["fi"])
                  for r in m4_surv) == sorted(
        tuple(x[2:]) for x in p_m4["ids"])
    # b1-low r29 (unwitnessed route) is explicitly not a target
    r29 = next(r for r in rows if r["fixture"] == "M4"
               and r["source"] == "b1-low" and r["ri"] == 29)
    assert r29["route"] == "unwitnessed_behavior"
    assert r29["g2"] == "BLOCK_SURVIVES"
    # anti-targets
    bare = [r for r in surv if not r["preds"] and not r["rels"]]
    bare_controls = [r for r in bare
                     if r["role"] == "control_blocker"]
    non_contract = [r for r in bare_controls
                    if r["route"] != "contract_contradiction"]
    assert pop["anti_targets"]["bare_controls_corpus_wide"] == \
        len(bare_controls) == 26
    assert pop["anti_targets"]["bare_controls_non_contract"] == \
        len(non_contract) == 11


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


def test_protocol_freezes_framework_language():
    protocol = (PREREG / "PROTOCOL.md").read_text()
    for phrase in ("preregistration only",
                   "No evidence currently",
                   "never creates a block",
                   "remediation validation, not",
                   "auto-excluded",
                   "never tuned",
                   "Agents never",
                       "Anti-targets",
                   "bb0ebdee",
                   "117b4164e5446f50"):
        assert phrase in protocol, phrase
