"""Phase-21B witness-policy design checks.

DESIGN-ONLY pins: the tier table is verified against the 18D report
verdicts, the corrected population language is mechanically
re-derived, the R1-prime bare fall set equals the merged 21A
exploratory ledger's common core, and the quantified trap (psd-only
witness beyond bare rows) is reproduced. Nothing executes a reduction
rule; no evaluator exists.
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

DESIGN = REPO / "eval" / "evidence" / \
    "v21-witness-policy-design-2026-09-23"
POLICY = json.loads((DESIGN / "POLICY_DESIGN.json").read_text())
PREREG_21A = REPO / "eval" / "evidence" / \
    "v21-false-blocker-prereg-2026-09-23"
CONTRACT_21A = json.loads(
    (PREREG_21A / "REDUCTION_CONTRACT.json").read_text())
EVAL_18D = REPO / "eval" / "evidence" / \
    "v21-contract-generalization-eval-2026-09-22" / \
    "generalization-report-18d.json"
PSD_RECORD = REPO / "eval" / "evidence" / \
    "v21-psd-qualification-closeout-2026-09-23" / "RECORD.json"


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


def test_design_is_design_only():
    assert POLICY["status"] == "design-only-no-adoption-no-execution"
    assert POLICY["design_only"] is True
    # the blocking review finding is encoded in the design itself:
    # R1-prime is relation-dependent and NOT adoptable
    assert POLICY["rule_r1_prime"]["relation_blind"] is False
    assert POLICY["rule_r1_prime"]["adoptable"] is False
    assert POLICY["rule_r1_prime"]["status"] == \
        "exploratory-relation-dependent-measurement"
    assert POLICY["adoption_paths"]["none_taken_by_this_design"] is True
    assert POLICY["oracle_version"] == rc.oracle_version()
    assert not (REPO / "eval" / "v21_false_blocker.py").exists()
    assert not (REPO / "eval" / "v21_witness_policy.py").exists()
    assert not (REPO / "eval" / "evidence" /
                "v21-false-blocker-eval-2026-09-23").exists()


def test_tier_table_matches_18d_verdicts():
    r18d = json.loads(EVAL_18D.read_text())
    verdicts = {name: rec["verdict"]
                for name, rec in r18d["per_relation"].items()}
    t2 = POLICY["witness_tiers"]["T2_psd"]
    assert verdicts[t2["relation"]] == "GENERALIZATION_PASS"
    t3 = set(POLICY["witness_tiers"]["T3_failed_five"]["relations"])
    assert len(t3) == 5
    for name in t3:
        assert verdicts[name] == "GENERALIZATION_FAIL"
    leaks = r18d["per_relation"]["secret_logged_by_echo"][
        "leaked_control_ids"] + \
        r18d["per_relation"]["doc_self_contradiction"][
            "leaked_control_ids"]
    assert sorted(leaks) == ["dsc-C1", "dsc-C2", "sle-C3"]
    t4 = POLICY["witness_tiers"]["T4_m10_family"]
    assert t4["authority"] == "regression-evidence-only"
    # the M10-family relation never entered the holdout: its FAILED
    # status is pinned by the Phase-17 replay, not the 18D report
    assert t4["relation"] not in verdicts
    m10 = frozen.replay()["phase09"]["relations"][t4["relation"]]
    assert m10["eligible"] is False
    assert "C10" in m10["control_fixtures"]
    assert json.loads(PSD_RECORD.read_text())["status"] == \
        "EVIDENCE_BACKED_ELIGIBLE__CONTRACT_ROUTE_ONLY"


def test_corrected_population_language_rederived():
    surv = [r for r in _rows() if r["g2"] == "BLOCK_SURVIVES"]
    bare = [r for r in surv if not r["preds"] and not r["rels"]]
    bare_controls = [r for r in bare
                     if r["role"] == "control_blocker"]
    non_contract = [r for r in bare
                    if r["route"] != "contract_contradiction"]
    non_contract_controls = [r for r in non_contract
                             if r["role"] == "control_blocker"]
    pop = POLICY["corrected_population_language"]
    assert pop["bare_survivors_corpus_wide"] == len(bare) == 44
    assert pop["bare_controls_corpus_wide"] == len(bare_controls) == 26
    assert pop["non_contract_bare_survivors"] == \
        len(non_contract) == 22
    assert pop["non_contract_bare_controls"] == \
        len(non_contract_controls) == 11
    assert pop["contract_route_bare_rows_in_scope"] == \
        (len(bare) - len(non_contract)) == 22


def test_r1_prime_fall_set_equals_21a_common_core():
    bare_fall = sorted(
        (r["role"], r["fixture"], r["source"], r["ri"], r["fi"])
        for r in _rows()
        if r["g2"] == "BLOCK_SURVIVES"
        and r["route"] == "contract_contradiction"
        and not r["preds"] and not r["rels"])
    ledger = POLICY["rule_r1_prime"]["fall_set"]
    assert len(bare_fall) == ledger["rows"] == 22
    assert dict(Counter(r[0] for r in bare_fall)) == ledger["by_role"]
    want_21a = sorted(tuple(x) for x in
                      CONTRACT_21A["frozen_ledgers"]["loose"]
                      ["falls_by_id"])
    assert bare_fall == want_21a
    # M10 rec55 is NOT in the set: it carries a T4 firing (not bare)
    assert ("true_positive_detection", "M10", "stage-a-max", 55, 0) \
        not in bare_fall


def test_relation_dependence_is_measured_not_asserted():
    """The replacement for the withdrawn redaction-equivalence
    claim: the T3/T4 redaction delta is mechanically computed and
    must match the design's admitted dependence exactly."""
    surv = [r for r in _rows() if r["g2"] == "BLOCK_SURVIVES"]
    bare = sorted(
        (r["role"], r["fixture"], r["source"], r["ri"], r["fi"])
        for r in surv
        if r["route"] == "contract_contradiction"
        and not r["preds"] and not r["rels"])
    redacted = [r for r in surv
                if r["route"] == "contract_contradiction"
                and not r["preds"]
                and not (r["rels"] & {"pinned_sha_demoted_to_branch"})]
    dep = POLICY["relation_dependence"]
    assert dep["admitted"] is True
    assert dep["invariant_cannot_hold"]
    assert len(bare) == dep["original_fall_set"] == 22
    assert len(redacted) == dep["redacted_fall_set"] == 46
    delta = [r for r in redacted
             if (r["role"], r["fixture"], r["source"], r["ri"],
                 r["fi"]) not in set(bare)]
    assert len(delta) == dep["additional_rows"] == 24
    assert all(r["role"] == "true_positive_detection" for r in delta)
    # breakdown: 23 from the five Phase-18D failures + 1 M10-family
    m10_name = "doc_contract_prefix_unanchored_match"
    five_fail = [r for r in delta
                 if r["rels"] - {m10_name,
                                 "pinned_sha_demoted_to_branch"}]
    m10_rows = [r for r in delta if r["rels"] == {m10_name}]
    assert len(five_fail) == dep["breakdown"][
        "five_phase18d_failures"] == 23
    assert len(m10_rows) == dep["breakdown"]["m10_family"] == 1
    per_relation = Counter(
        sorted(r["rels"] - {"pinned_sha_demoted_to_branch"})[0]
        for r in five_fail)
    assert dict(per_relation) == dep["per_relation_five_phase18d_failures"]
    # independence impossibility on current validated evidence:
    # none of the 24 rows carries a T1 predicate or a T2 psd firing
    for r in delta:
        assert not r["preds"]
        assert "pinned_sha_demoted_to_branch" not in r["rels"]


def test_proposal_admits_dependence_and_states_paths():
    proposal = (DESIGN / "PROPOSAL.md").read_text()
    for phrase in ("DESIGN ONLY",
                   "advisory only", "never decision-bearing",
                   "evidence-presence-dependent by construction",
                   "cannot", "relation-dependent, not relation-blind",
                   "not adoptable",
                   "23 from the five Phase-18D failures",
                   "1 M10-family row",
                       "evidence predicate is derivable",
                   "PA1", "PA2", "PA3",
                   "preservation authority",
                   "PC1", "PC2", "V1", "V2", "V3", "V4",
                   "22 non-contract bare survivors",
                   "witness question remains open"):
        assert phrase in proposal, phrase
    # the withdrawn claim must be gone
    for withdrawn in ("Authority invariant", "byte-identical whether "
                      "T3/T4 firings are present or redacted",
                      "hence bare scoping"):
        assert withdrawn not in proposal, withdrawn
