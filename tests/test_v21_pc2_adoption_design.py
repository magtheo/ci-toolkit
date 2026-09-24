"""Phase-23A PC2 disposition + combined-policy adoption design checks.

Mechanically re-derives the combined ledger from frozen records,
enforces the existing authority boundaries (m4rel grant scope, psd
untouched, no authority for failed relations/M10), verifies the
observed-fact blocks against the frozen 18A/18D reports, and pins
the design-only/no-selection status of both documents.
"""
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.evidence_boundary_sim as boundary  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import eval.v21_contract_relations as frozen  # noqa: E402
import eval.v21_m4_relation as m4  # noqa: E402
import eval.v21_replay as v21  # noqa: E402
import eval.v21_routes_replay as rr  # noqa: E402

DESIGN_DIR = REPO / "eval" / "evidence" / \
    "v21-pc2-adoption-design-2026-09-23"
LEDGER = json.loads((DESIGN_DIR / "COMBINED-LEDGER.json").read_text())
GEN = DESIGN_DIR / "generate_ledger.py"

T2_PSD = "pinned_sha_demoted_to_branch"
M10_REL = "doc_contract_prefix_unanchored_match"


def _sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def _derive():
    fixtures = {f["id"]: f
                for f in rc.load_corpus(REPO / "eval" / "fixtures")}
    rows = []
    for source, rel in boundary.SOURCES.items():
        recs = [json.loads(line)
                for line in (REPO / rel).read_text().splitlines()
                if line.strip()]
        for ri, rec in enumerate(recs):
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
                    "preds": list(v21.predicate_names(finding,
                                                      fixture)),
                    "rels": sorted(frozen.relation_names(finding,
                                                         fixture)),
                    "fixture": rec["fixture"],
                    "source": source, "ri": ri, "fi": fi,
                    "covers": bool(m4.covers(finding, fixture)),
                })
    return fixtures, rows


def _key(r):
    return (r["source"], r["ri"], r["fi"], r["role"], r["fixture"])


def test_status_design_only_pc2_unresolved():
    assert LEDGER["status"] == ("design-only__no-execution__"
                                "no-adoption__pc2-unresolved")
    assert rc.oracle_version() == LEDGER["oracle_version"]


def test_provenance_input_hashes_live():
    pins = LEDGER["provenance"]["input_sha256"]
    assert len(pins) >= 20
    for rel, want in pins.items():
        assert _sha(REPO / rel) == want, rel
    assert LEDGER["provenance"]["parent_pr107_merge_sha"] == \
        "71f78a19ab6297c89186552dbe03efd5a587c3d9"
    assert _sha(REPO / "eval" / "v21_m4_relation.py") == pins[
        "eval/v21_m4_relation.py"]


def test_corpus_populations_rederived_and_identical():
    fixtures, rows = _derive()
    assert len(rows) == 276
    surv = [r for r in rows if r["g2"] == "BLOCK_SURVIVES"]
    assert len(surv) == 145
    bare = {r["role"]: [] for r in []}
    bare_rows = [r for r in surv
                 if r["route"] == "contract_contradiction"
                 and not r["preds"] and not r["rels"]]
    relcar = [r for r in surv
              if r["role"] == "true_positive_detection"
              and r["route"] == "contract_contradiction"
              and not r["preds"] and r["rels"]
              and T2_PSD not in r["rels"]]
    eligible = [r for r in rows
                if r["g2"] == "BLOCK_SURVIVES"
                and r["route"] == "contract_contradiction"
                and r["role"] == "true_positive_detection"
                and r["covers"]]
    of = LEDGER["observed_facts"]["corpus"]
    assert {_key(r) for r in bare_rows} == {
        _key(dict(r, role=r["role"]))
        for r in of["bare_contract_survivors"]["rows"]} if False \
        else {_key(r) for r in bare_rows} == {
            (x["source"], x["record_index"], x["finding_index"],
             x["role"], x["fixture"])
            for x in of["bare_contract_survivors"]["rows"]}
    assert len(bare_rows) == len(
        of["bare_contract_survivors"]["rows"]) == 22
    assert of["bare_contract_survivors"][
        "identical_to_21a_loose_fall_set"] is True
    assert {(x["source"], x["record_index"], x["finding_index"],
             x["role"], x["fixture"])
            for x in of["relation_carried_tps"]["rows"]} == \
        {_key(r) for r in relcar}
    assert len(relcar) == 24
    assert of["relation_carried_tps"][
        "no_t1_or_t2_evidence_by_construction"] is True
    assert {(x["source"], x["record_index"], x["finding_index"],
             x["role"], x["fixture"])
            for x in of["grant_eligible_rows"]["rows"]} == \
        {_key(r) for r in eligible}
    assert len(eligible) == 2
    assert {r["source"] for r in eligible} == {"b1-low",
                                                   "stage-a-max"}
    assert of["other_survivors"] == len(surv) - len(bare_rows) \
        - len(relcar) == 99


def test_variant_aggregates_recomputed():
    fixtures, rows = _derive()
    surv = [r for r in rows if r["g2"] == "BLOCK_SURVIVES"]
    bare = [r for r in surv
            if r["route"] == "contract_contradiction"
            and not r["preds"] and not r["rels"]]
    relcar = [r for r in surv
              if r["role"] == "true_positive_detection"
              and r["route"] == "contract_contradiction"
              and not r["preds"] and r["rels"]
              and T2_PSD not in r["rels"]]
    eligible = [r for r in rows
                if r["g2"] == "BLOCK_SURVIVES"
                and r["route"] == "contract_contradiction"
                and r["role"] == "true_positive_detection"
                and r["covers"]]

    def cnt(falls, preserved):
        return {
            "true_positive_losses":
                sum(1 for r in falls
                    if r["role"] == "true_positive_detection"),
            "controls_downgraded":
                sum(1 for r in falls
                    if r["role"] == "control_blocker"),
            "extras_downgraded":
                sum(1 for r in falls
                    if r["role"] == "positive_extra_blocker"),
            "true_positives_preserved_by_grant": len(preserved),
            "controls_erroneously_preserved": 0,
            "extras_erroneously_preserved": 0,
            "unchanged_survivors":
                len(surv) - len(falls) - len(preserved),
        }

    cv = LEDGER["counterfactual_effects"]["corpus_variants"]
    expect = {
        "V0_baseline_g2_unchanged": cnt([], []),
        "V1_bare_scope_alone": cnt(bare, []),
        "V2_bare_scope_plus_m4rel_grant": cnt(
            [r for r in bare if r not in eligible], eligible),
        "V3_qualified_evidence_only": cnt(bare + relcar, []),
        "V3_plus_grant": cnt(
            [r for r in bare + relcar if r not in eligible],
            eligible),
    }
    for name, want in expect.items():
        got = {k: cv[name]["counts"][k] for k in want}
        assert got == want, (name, got, want)
    assert len(cv["V2_bare_scope_plus_m4rel_grant"]["falls"]) == 20
    assert len(cv["V3_qualified_evidence_only"]["falls"]) == 46
    assert cv["V2_bare_scope_plus_m4rel_grant"][
        "relation_carried_tps"]["no_new_authority"] is True
    assert "not resurrected" in cv["V2_bare_scope_plus_m4rel_grant"][
        "relation_carried_tps"]["caveat"]
    # the 20 V2 falls are exactly the bare set minus the grant rows
    v2_falls = {(x["source"], x["record_index"],
                 x["finding_index"])
                for x in cv["V2_bare_scope_plus_m4rel_grant"][
                    "falls"]}
    assert v2_falls == {(r["source"], r["ri"], r["fi"])
                        for r in bare} - {
        (r["source"], r["ri"], r["fi"]) for r in eligible}


def test_authority_boundaries():
    ae = LEDGER["authorized_effects"]
    grant = ae["m4rel_preservation_grant"]
    assert len(grant["measured_corpus_eligible_rows"]) == 2
    assert grant["controls_preserved"] == 0
    assert grant["extras_preserved"] == 0
    for excl in ("no admission", "no block creation",
                 "no extra-blocker preservation",
                 "no route expansion", "no GATING activation",
                 "no deployed change"):
        assert excl in grant["exclusions"]
    assert grant["sha256"] == _sha(
        REPO / "eval/evidence/v21-m4rel-qg5-grant-2026-09-23/"
        "GRANT_RECORD.json")
    assert "no expansion" in ae["psd_admission_authority"]["status"]
    assert "no preservation authority" in \
        ae["failed_relations_and_m10"]["status"]
    relcar_keys = {(x["source"], x["record_index"],
                    x["finding_index"])
                   for x in LEDGER["observed_facts"]["corpus"][
                       "relation_carried_tps"]["rows"]}
    grant_keys = {(x["source"], x["record_index"],
                   x["finding_index"])
                  for x in grant["measured_corpus_eligible_rows"]}
    assert not (relcar_keys & grant_keys)


def test_holdout_observed_facts_match_frozen_reports():
    r18a = json.loads(
        (REPO / "eval/evidence/v21-contract-generalization-eval-"
         "2026-09-22/generalization-report.json").read_text())
    r18d = json.loads(
        (REPO / "eval/evidence/v21-contract-generalization-eval-"
         "2026-09-22/generalization-report-18d.json").read_text())
    hold = LEDGER["observed_facts"]["holdout_18a_18d"]
    assert hold["aggregate_18a"] == r18a["aggregate"]
    p4 = [r for r in r18a["fixture_rows"]
          if r["id"] == "dsc-P4"][0]
    assert hold["dsc_P4_row_18a"] == p4
    assert p4["admitted"] is False
    assert p4["fired_relations"] == []
    dsc = r18d["per_relation"]["doc_self_contradiction"]
    assert hold["dsc_18d"] == dsc
    assert dsc["verdict"] == "GENERALIZATION_FAIL"
    assert set(dsc["failed_positive_ids"]) >= {"dsc-P3", "dsc-P4",
                                               "dsc-P5"}
    assert set(dsc["leaked_control_ids"]) == {"dsc-C1", "dsc-C2"}
    pred = LEDGER["observed_facts"]["holdout_21b_prediction_V2"]
    assert "never executed" in pred["status"]
    assert pred["predicted_bare_contract_route_positive"] == \
        ["dsc-P4"]
    hv = LEDGER["counterfactual_effects"]["holdout_variants_pc2"]
    assert hv["EXT_A_accept_cost"]["counts"][
        "true_positive_losses"] == 1
    assert hv["EXT_B_qualify_dsc_prime_first"]["counts"][
        "true_positive_losses"] == 0
    assert hv["EXT_B_qualify_dsc_prime_first"]["contingent"]
    assert "rejected" in " ".join(
        hv["EXT_C_scope_boundary"]["legitimacy_conditions"])


def test_pc2_disposition_document():
    md = (DESIGN_DIR / "PC2-DISPOSITION.md").read_text()
    for phrase in ("UNRESOLVED", "does not select one",
                   "Path A — Accept the recall cost",
                   "Path B — Qualify dsc′ first",
                   "Path C — Limit the reduction's scope",
                   "not a qualified preservation witness",
                   "burned", "disguised holdout exception",
                   "Exact authorization required",
                   "UNRESOLVED by design",
                   "dsc-C1/C2", "GENERALIZATION_FAIL"):
        assert phrase in md, phrase
    assert "| A — accept cost |" in md and \
        "| B — qualify dsc′ first |" in md and \
        "| C — scope boundary |" in md


def test_adoption_design_document():
    md = (DESIGN_DIR / "ADOPTION-DESIGN.md").read_text()
    for phrase in ("design preparation",
                   "V3 — qualified-evidence-only",
                   "the 24 relation-carried true positives",
                   "no preservation authority",
                   "No fixture IDs, oracle roles, hidden labels",
                   "evidence-presence dependence, admitted",
                   "not resurrected",
                   "Policy-design approval",
                   "Execution authorization",
                   "Authority grant",
                   "Deployment / GATING activation",
                   "None follows automatically from another",
                   "Zero extra-blocker preservation",
                   "fail-closed",
                   "no grant registry", "Stopped for human review"):
        assert phrase in md, phrase
    gates = md[md.find("## Adoption gates"):
               md.find("## The four authorization kinds")]
    for gate in ("Exact-head evidence and hash integrity",
                 "No new admission authority; psd unchanged",
                 "No preservation authority from failed relations",
                 "Preservation of the two qualified M4 rows",
                 "Explicit PC2 disposition and holdout recall "
                 "accounting",
                 "Unchanged standing guards",
                 "No hidden oracle-role branching",
                 "Independently reviewed"):
        assert gate in gates, gate


def test_generator_is_deterministic_source():
    import subprocess
    out = subprocess.run(
        [sys.executable, str(GEN)], capture_output=True, text=True,
        cwd=str(REPO))
    assert out.returncode == 0, out.stderr
    regenerated = (DESIGN_DIR / "COMBINED-LEDGER.json").read_text()
    assert regenerated == json.dumps(
        json.loads(regenerated), indent=2) + "\n"
    after = hashlib.sha256(
        (DESIGN_DIR / "COMBINED-LEDGER.json").read_bytes()).hexdigest()
    assert out.returncode == 0
    # rerunning produced a byte-identical ledger
    subprocess.run([sys.executable, str(GEN)], check=True,
                   capture_output=True, cwd=str(REPO))
    assert hashlib.sha256(
        (DESIGN_DIR / "COMBINED-LEDGER.json").read_bytes()).hexdigest() \
        == after
