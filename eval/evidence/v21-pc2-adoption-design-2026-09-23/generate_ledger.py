"""Phase-23A combined-policy ledger generator.

Re-derives the corpus populations mechanically from frozen records
and frozen modules, assembles observed facts (frozen evaluation
records), counterfactual effects, and authorized effects into
COMBINED-LEDGER.json. Run from repo root:

    python3 eval/evidence/v21-pc2-adoption-design-2026-09-23/generate_ledger.py --check
    # Only for an explicitly reviewed regeneration of the ledger:
    python3 eval/evidence/v21-pc2-adoption-design-2026-09-23/generate_ledger.py --write
"""
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import eval.evidence_boundary_sim as boundary  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import eval.v21_contract_relations as frozen  # noqa: E402
import eval.v21_m4_relation as m4  # noqa: E402
import eval.v21_replay as v21  # noqa: E402
import eval.v21_routes_replay as rr  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent

T2_PSD = "pinned_sha_demoted_to_branch"
M10_REL = "doc_contract_prefix_unanchored_match"
FAILED_FIVE = sorted([
    "doc_self_contradiction",
    "preserved_claim_vs_dropped_call_result",
    "consume_before_validate_ordering",
    "jsonl_format_vs_unslurped_jq",
    "secret_logged_by_echo",
])

EVIDENCE_INPUTS = [
    "eval/evidence/v21-false-blocker-prereg-2026-09-23/"
    "REDUCTION_CONTRACT.json",
    "eval/evidence/v21-false-blocker-prereg-2026-09-23/PROTOCOL.md",
    "eval/evidence/v21-witness-policy-design-2026-09-23/"
    "POLICY_DESIGN.json",
    "eval/evidence/v21-witness-policy-design-2026-09-23/PROPOSAL.md",
    "eval/evidence/v21-preservation-authority-prereg-2026-09-23/"
    "QUALIFICATION_CONTRACT.json",
    "eval/evidence/v21-preservation-authority-prereg-2026-09-23/"
    "PROTOCOL.md",
    "eval/evidence/v21-m4rel-prereg-2026-09-23/TARGETS_CONTRACT.json",
    "eval/evidence/v21-m4rel-prereg-2026-09-23/PROTOCOL.md",
    "eval/evidence/v21-m4rel-implementation-2026-09-23/EVIDENCE.json",
    "eval/evidence/v21-m4rel-qualification-2026-09-23/"
    "qualification-report.json",
    "eval/evidence/v21-m4rel-qualification-2026-09-23/"
    "qualification-report.execution-4.json",
    "eval/evidence/v21-m4rel-qualification-2026-09-23/"
    "qualification-report.execution-1.json",
    "eval/evidence/v21-m4rel-qualification-2026-09-23/"
    "execution-log.jsonl",
    "eval/evidence/v21-m4rel-qualification-2026-09-23/"
    "PHASE_TRANSITION.json",
    "eval/evidence/v21-m4rel-qg5-grant-2026-09-23/GRANT_RECORD.json",
    "eval/evidence/v21-m4rel-qg5-grant-2026-09-23/GRANT.md",
    "eval/evidence/v21-contract-generalization-prereg-2026-09-22/"
    "MANIFEST.json",
    "eval/evidence/v21-contract-generalization-eval-2026-09-22/"
    "generalization-report.json",
    "eval/evidence/v21-contract-generalization-eval-2026-09-22/"
    "generalization-report-18d.json",
    "eval/v21_m4_relation.py",
    "eval/v21_contract_relations.py",
]


def sha(rel):
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def canon(rows):
    return sorted((r["source"], r["ri"], r["fi"]) for r in rows)


def rowid(r, fixtures):
    return {
        "role": r["role"],
        "fixture": r["fixture"],
        "source": r["source"],
        "record_index": r["ri"],
        "finding_index": r["fi"],
        "route": r["route"],
        "baseline_g2": r["g2"],
        "predicates": r["preds"],
        "relations": r["rels"],
        "m4rel_covers": r["covers"],
    }


def build():
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
    assert len(rows) == 276, len(rows)
    assert set(n for r in rows for n in r["rels"]) == \
        set(FAILED_FIVE) | {M10_REL, T2_PSD}, "relation universe drift"

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
    for r in bare:
        r["bare"] = True
    for r in relcar:
        r["bare"] = False
        r["bucket"] = ("m10_family"
                       if r["rels"] == [M10_REL] else
                       "failed_five:" + r["rels"][0]
                       if len(r["rels"]) == 1
                       and r["rels"][0] in FAILED_FIVE
                       else "mixed")
    assert len(bare) == 22 and len(relcar) == 24 and len(eligible) == 2
    assert not (set(canon(eligible)) - set(canon(bare)))
    assert not (set(canon(bare)) & set(canon(relcar)))
    assert not any(r["covers"] for r in rows
                   if r["role"] != "true_positive_detection")

    # cross-check against the frozen 21A loose fall ledger
    rc21a = json.loads((REPO / EVIDENCE_INPUTS[0]).read_text())
    frozen21a = sorted(
        tuple(x) for x in
        rc21a["frozen_ledgers"]["loose"]["falls_by_id"])
    mine21a = sorted((r["role"], r["fixture"], r["source"],
                      r["ri"], r["fi"]) for r in bare)
    assert frozen21a == mine21a, "bare set drifted from 21A ledger"

    v1_falls = sorted(bare, key=lambda r: (r["source"], r["ri"],
                                           r["fi"]))
    v2_falls = [r for r in bare if r not in eligible]
    v2_preserved = sorted(eligible, key=lambda r: (r["source"],
                                                   r["ri"], r["fi"]))
    v3_falls = sorted(bare + relcar,
                      key=lambda r: (r["source"], r["ri"], r["fi"]))

    def counts(falls, preserved):
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
            "true_positives_preserved_by_grant":
                sum(1 for r in preserved
                    if r["role"] == "true_positive_detection"),
            "controls_erroneously_preserved":
                sum(1 for r in preserved
                    if r["role"] == "control_blocker"),
            "extras_erroneously_preserved":
                sum(1 for r in preserved
                    if r["role"] == "positive_extra_blocker"),
            "unchanged_survivors": len(surv) - len(falls)
                                   - len(preserved),
        }

    gen = json.loads((REPO / EVIDENCE_INPUTS[16]).read_text())
    r18a = json.loads((REPO / EVIDENCE_INPUTS[17]).read_text())
    r18d = json.loads((REPO / EVIDENCE_INPUTS[18]).read_text())
    p4 = [r for r in r18a["fixture_rows"] if r["id"] == "dsc-P4"][0]
    dsc18d = r18d["per_relation"]["doc_self_contradiction"]
    assert p4["admitted"] is False and \
        p4["fired_relations"] == [] and \
        "dsc-P4" in dsc18d["failed_positive_ids"]

    ledger = {
        "phase": "23A",
        "kind": "combined-policy-ledger",
        "status": "design-only__no-execution__no-adoption__"
                  "pc2-unresolved",
        "oracle_version": rc.oracle_version(),
        "result_kinds": {
            "observed_fact": "derived mechanically from frozen "
                             "evaluation records and frozen modules "
                             "at generation time; re-derivable",
            "counterfactual_effect": "outcome a proposed rule WOULD "
                                     "produce; not executed as policy",
            "authorized_effect": "outcome permitted by an accepted "
                                 "authority grant; nothing here "
                                 "executes the grant",
        },
        "provenance": {
            "parent_pr107_merge_sha":
                "71f78a19ab6297c89186552dbe03efd5a587c3d9",
            "input_sha256": {rel: sha(rel)
                             for rel in EVIDENCE_INPUTS},
            "generation": "mechanically re-derived from frozen "
                          "records via boundary simulation, frozen "
                          "relation verifier, and the frozen m4rel "
                          "detector; no summary number is copied",
        },
        "observed_facts": {
            "corpus": {
                "population": 276,
                "g2_survivors": len(surv),
                "bare_contract_survivors": {
                    "count": len(bare),
                    "definition": "g2 BLOCK_SURVIVES, route "
                                  "contract_contradiction, no "
                                  "predicate firing, no relation "
                                  "firing of any tier",
                    "identical_to_21a_loose_fall_set": True,
                    "rows": [rowid(r, fixtures) for r in v1_falls],
                },
                "grant_eligible_rows": {
                    "count": len(eligible),
                    "rows": [rowid(r, fixtures)
                             for r in v2_preserved],
                },
                "relation_carried_tps": {
                    "count": len(relcar),
                    "definition": "frozen 22B population: g2 "
                                  "BLOCK_SURVIVES TPs on the "
                                  "contract route with no predicate "
                                  "and at least one non-psd relation "
                                  "firing",
                    "no_t1_or_t2_evidence_by_construction": True,
                    "buckets": dict(sorted(
                        (b, sum(1 for r in relcar
                                if r["bucket"] == b))
                        for b in {r["bucket"]
                                  for r in relcar})),
                    "rows": [dict(rowid(r, fixtures),
                                  relation_bucket=r["bucket"])
                             for r in sorted(relcar,
                                             key=lambda r: (
                                                 r["source"],
                                                 r["ri"], r["fi"]))],
                },
                "other_survivors": len(surv) - len(bare)
                                   - len(relcar),
            },
            "holdout_18a_18d": {
                "status": "observed facts from frozen reports",
                "aggregate_18a": r18a["aggregate"],
                "dsc_P4_row_18a": p4,
                "dsc_18d": dsc18d,
                "note": "dsc-P4 is a holdout positive whose oracle "
                        "probe was not admitted in 18A and on which "
                        "the dsc relation did not fire; 18D failed "
                        "the dsc family (missed P3/P4/P5; leaked "
                        "C1/C2)",
            },
            "holdout_21b_prediction_V2": {
                "status": "frozen prediction from the 21B design; "
                          "never executed; executing it requires an "
                          "execution authorization",
                "predicted_g2_survivors": 3,
                "predicted_kept": ["dsc-C4", "dsc-P2"],
                "predicted_bare_contract_route_positive":
                    ["dsc-P4"],
            },
        },
        "counterfactual_effects": {
            "corpus_variants": {
                "V0_baseline_g2_unchanged": {
                    "semantics": "no reduction applied",
                    "falls": [], "preserved_by_grant": [],
                    "counts": counts([], []),
                },
                "V1_bare_scope_alone": {
                    "semantics": "downgrade contract-route g2 "
                                 "survivors with no evidence of any "
                                 "kind; m4rel grant NOT applied",
                    "status": "exploratory measurement; not "
                              "adoptable (would sacrifice the two "
                              "grant-protected M4 rows)",
                    "falls": [rowid(r, fixtures) for r in v1_falls],
                    "preserved_by_grant": [],
                    "counts": counts(v1_falls, []),
                },
                "V2_bare_scope_plus_m4rel_grant": {
                    "semantics": "V1 with the accepted m4rel "
                                 "preservation grant applied to "
                                 "eligible existing blocks",
                    "status": "the authorized combination on paper; "
                              "adoption still requires the Phase-23A "
                              "gates and explicit authorizations",
                    "falls": [rowid(r, fixtures) for r in v2_falls],
                    "preserved_by_grant":
                        [rowid(r, fixtures)
                         for r in v2_preserved],
                    "counts": counts(v2_falls, v2_preserved),
                    "relation_carried_tps": {
                        "outcome": "all 24 unchanged",
                        "no_new_authority": True,
                        "caveat": "the rule is evidence-presence-"
                                  "dependent: rows are not bare "
                                  "because failed-relation firings "
                                  "exist; their preservation is NOT "
                                  "granted authority and must not "
                                  "acquire it implicitly; the "
                                  "rejected 21B redaction-equivalence "
                                  "claim is not resurrected; if a "
                                  "future policy redacts failed-"
                                  "relation firings the V3 delta "
                                  "becomes binding",
                    },
                },
                "V3_qualified_evidence_only": {
                    "semantics": "witness = qualified evidence only "
                                 "(T1 predicates or T2 psd); "
                                 "failed-relation firings do not "
                                 "witness (redaction-accounting "
                                 "variant)",
                    "status": "warning variant; NOT proposed; shown "
                              "because any future policy must state "
                              "its evidence semantics precisely",
                    "falls": [rowid(r, fixtures) for r in v3_falls],
                    "preserved_by_grant": [],
                    "counts": counts(v3_falls, []),
                },
                "V3_plus_grant": {
                    "semantics": "V3 with the m4rel grant applied",
                    "falls": [rowid(r, fixtures)
                              for r in v3_falls
                              if r not in eligible],
                    "preserved_by_grant":
                        [rowid(r, fixtures)
                         for r in v2_preserved],
                    "counts": counts([r for r in v3_falls
                                      if r not in eligible],
                                     v2_preserved),
                },
            },
            "holdout_variants_pc2": {
                "status": "all holdout extension effects are "
                          "counterfactuals over the frozen 21B V2 "
                          "prediction and 18A/18D facts; none is "
                          "executed here",
                "EXT_A_accept_cost": {
                    "pc2_path": "A",
                    "effect": "dsc-P4's future detected block "
                              "downgrades: 1 true-positive loss on "
                              "holdout material",
                    "requires": "explicit human risk acceptance "
                                "recorded in the adoption "
                                "preregistration; an acceptance of "
                                "scope is NOT a qualified preservation "
                                "witness and creates no authority",
                    "counts": {"true_positive_losses": 1,
                               "controls_downgraded": 0,
                               "extras_downgraded": 0,
                               "true_positives_preserved_by_grant": 0,
                               "controls_erroneously_preserved": 0,
                               "extras_erroneously_preserved": 0,
                               "unchanged_survivors": 2},
                },
                "EXT_B_qualify_dsc_prime_first": {
                    "pc2_path": "B",
                    "effect": "holdout fall set 0 (dsc-P4 witnessed "
                              "by a qualified dsc-prime through its "
                              "own preregistered cycle)",
                    "requires": "full 22A-framework qualification: "
                                "remediation of dsc-C1/C2 control "
                                "leaks and the P3/P4/P5 misses, "
                                "candidate-specific preregistration "
                                "with fresh independent holdout, "
                                "pair discipline, measured "
                                "qualification (N=5, >=4/5, paired "
                                "control clean), then a separate "
                                "preservation-authority decision; "
                                "dsc-P4 itself is burned as a target "
                                "and may not serve as one",
                    "counts": {"true_positive_losses": 0,
                               "controls_downgraded": 0,
                               "extras_downgraded": 0,
                               "true_positives_preserved_by_grant": 0,
                               "controls_erroneously_preserved": 0,
                               "extras_erroneously_preserved": 0,
                               "unchanged_survivors": 3},
                    "contingent": "only if the dsc-prime cycle "
                                  "PASSES and authority is granted",
                },
                "EXT_C_scope_boundary": {
                    "pc2_path": "C",
                    "effect": "the reduction's applicability boundary "
                              "excludes holdout-context decisions, "
                              "so dsc-P4 is untouched within scope",
                    "legitimacy_conditions": [
                        "no fixture IDs, oracle roles, hidden "
                        "labels, or known holdout membership may be "
                        "runtime policy inputs",
                        "a provenance/rollout boundary (e.g. "
                        "records produced by the qualification "
                        "corpus pipeline) is an operational "
                        "rollout scope only; it DEFERS PC2 and must "
                        "be labeled as deferment, never as "
                        "generalization",
                        "a structural boundary that happens to "
                        "exclude dsc-P4 would be a disguised "
                        "holdout exception and is rejected",
                    ],
                    "counts": {"true_positive_losses": 0,
                               "controls_downgraded": 0,
                               "extras_downgraded": 0,
                               "true_positives_preserved_by_grant": 0,
                               "controls_erroneously_preserved": 0,
                               "extras_erroneously_preserved": 0,
                               "unchanged_survivors": 3},
                },
            },
        },
        "authorized_effects": {
            "m4rel_preservation_grant": {
                "record":
                    "eval/evidence/v21-m4rel-qg5-grant-2026-09-23/"
                    "GRANT_RECORD.json",
                "sha256": sha(EVIDENCE_INPUTS[14]),
                "scope": "preservation only; existing g2 "
                         "BLOCK_SURVIVES on contract_contradiction "
                         "with claim-linked m4rel.covers; effect = "
                         "exemption from a future separately "
                         "approved bare-scope downgrade",
                "measured_corpus_eligible_rows":
                    [rowid(r, fixtures) for r in v2_preserved],
                "controls_preserved": 0, "extras_preserved": 0,
                "exclusions": ["no admission", "no block creation",
                               "no extra-blocker preservation",
                               "no route expansion",
                               "no GATING activation",
                               "no deployed change"],
            },
            "psd_admission_authority": {
                "status": "unchanged; previously qualified, "
                          "contract-route admission; no expansion",
            },
            "failed_relations_and_m10": {
                "status": "no preservation authority; firings must "
                          "not acquire authority implicitly",
            },
        },
        "authority_boundary_assertions": [
            "grant eligibility is exactly the two named M4 rows on "
            "the frozen corpus",
            "zero control rows and zero extra rows are preserved by "
            "any variant",
            "no relation-carried row appears in any authorized "
            "effect",
            "failed relations and the M10 family appear in no "
            "authorized effect",
            "psd admission scope is referenced as unchanged only",
        ],
    }
    # Building a ledger is pure: never rewrite a checked-in evidence
    # artifact during tests or verification. Writing needs explicit
    # --write and must not be done after the record is accepted/frozen.
    return json.dumps(ledger, indent=2, sort_keys=False) + "\n"


def main(argv):
    if argv not in (["--check"], ["--write"]):
        raise SystemExit("usage: generate_ledger.py --check|--write")
    content = build()
    path = OUT / "COMBINED-LEDGER.json"
    if argv == ["--check"]:
        if not path.exists() or path.read_bytes() != content.encode():
            print("HALT: committed ledger differs from frozen derivation",
                  file=sys.stderr)
            return 1
        print("ledger matches derived bytes; no files changed")
        return 0
    path.write_text(content)
    print("ledger written explicitly; review and freeze its new SHA")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
