"""Phase-21A false-blocker reduction preregistration checks.

The R1 rule family and every cost ledger are frozen BEFORE any 21B
run exists. These tests pin REDUCTION_CONTRACT.json against live
reality and mechanically re-derive both variant ledgers and the
holdout ledger, so silent post-hoc edits are detectable. No
reduction evaluator exists yet; none is executed here.
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
    "v21-false-blocker-prereg-2026-09-23"
CONTRACT = json.loads(
    (PREREG / "REDUCTION_CONTRACT.json").read_text())
PHASE17_SIX = {"pinned_sha_demoted_to_branch",
             "preserved_claim_vs_dropped_call_result",
             "consume_before_validate_ordering",
             "secret_logged_by_echo",
             "doc_self_contradiction",
             "jsonl_format_vs_unslurped_jq"}
EVAL_21B = REPO / "eval" / "evidence" / \
    "v21-false-blocker-eval-2026-09-23"


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
                    "rels": frozen.relation_names(finding, fixture),
                    "fixture": fixture["id"],
                    "source": source, "ri": ri, "fi": fi,
                })
    return rows


def _survivors():
    return [r for r in _rows() if r["g2"] == "BLOCK_SURVIVES"]


def test_contract_pins_and_scope():
    assert CONTRACT["phase"] == "21A"
    assert CONTRACT["status"] == "preregistration-frozen__execution-not-approved"
    assert CONTRACT["execution_contract_21b"]["authorization"].startswith(
        "NOT_APPROVED")
    assert CONTRACT["preregistered_before_any_21b_run"] is True
    assert CONTRACT["problem"]["population"] == 276
    assert CONTRACT["problem"]["g2_survivors"] == 145
    assert CONTRACT["problem"]["false_blockers_surviving_g2"] == 34
    assert CONTRACT["rule_family"]["applies_to"] == (
        "g2_contract_aware == BLOCK_SURVIVES AND route == "
        "contract_contradiction")
    assert len(CONTRACT["decision_points"]) == 3
    assert CONTRACT["oracle_version"] == rc.oracle_version()
    module_names = set(frozen.RELATIONS)
    assert module_names - PHASE17_SIX == \
        {"doc_contract_prefix_unanchored_match"}
    assert module_names | PHASE17_SIX == module_names
    assert CONTRACT["problem"]["witness_qualification_note"].startswith(
        "Phase-17 six survived in-sample")
    assert CONTRACT["problem"]["bare_population"] == {
        "corpus_wide": {"survivors": 44, "controls": 26,
                        "TP": 13, "extras": 5},
        "non_contract": {"survivors": 22, "controls": 11,
                         "TP": 11, "extras": 0},
    }


def test_21b_has_not_started():
    assert not EVAL_21B.exists()
    assert not (REPO / "eval" / "v21_false_blocker.py").exists()


def test_survivor_surface_matches_frozen_table():
    surface = Counter()
    for r in _survivors():
        rels = set(r["rels"])
        if "pinned_sha_demoted_to_branch" in rels:
            key = "psd_relation_verified"
        elif rels & PHASE17_SIX:
            key = "relation_verified_six"
        elif "doc_contract_prefix_unanchored_match" in rels:
            key = "failed_relation_verified_m10_family"
        elif r["preds"]:
            key = "witnessed_predicate_only"
        elif r["route"] == "contract_contradiction":
            key = "bare_contract_route"
        elif r["route"] == "external_fact":
            key = "bare_external_fact_route"
        else:
            key = "bare_unwitnessed_route"
        role = {"true_positive_detection": "TP",
                "control_blocker": "control",
                "positive_extra_blocker": "extra"}[r["role"]]
        surface[(key, role)] += 1
    for key, expected in CONTRACT["problem"][
            "survivor_surface"].items():
        for role, count in expected.items():
            assert surface[(key, role)] == count, (key, role)


def test_loose_ledger_matches_frozen_prediction():
    falls = [r for r in _survivors()
             if r["route"] == "contract_contradiction"
             and not r["preds"] and not r["rels"]]
    predicted = CONTRACT["frozen_ledgers"]["loose"]
    assert len(falls) == predicted["falls"] == 22
    got = sorted((r["role"], r["fixture"], r["source"], r["ri"],
                  r["fi"]) for r in falls)
    want = sorted(tuple(x) for x in predicted["falls_by_id"])
    assert got == want
    assert dict(Counter(r["role"] for r in falls)) == \
        predicted["by_role"]
    survivors = _survivors()
    after = predicted["survivors_after"]
    assert len(survivors) - 22 == after["total"] == 123
    for role, delta in (("true_positive_detection", "TP"),
                        ("control_blocker", "control"),
                        ("positive_extra_blocker", "extra")):
        kept = sum(1 for r in survivors if r["role"] == role) - \
            sum(1 for r in falls if r["role"] == role)
        assert kept == after[delta]


def test_strict_delta_is_exactly_the_m10_row():
    loose_ids = {tuple(x[:4]) for x in
                 CONTRACT["frozen_ledgers"]["loose"]["falls_by_id"]}
    strict = [r for r in _survivors()
              if r["route"] == "contract_contradiction"
              and not r["preds"]
              and not (set(r["rels"]) & PHASE17_SIX)
              and tuple((r["role"], r["fixture"], r["source"],
                         r["ri"])) not in loose_ids]
    assert len(strict) == 1
    row = strict[0]
    want = CONTRACT["frozen_ledgers"]["strict"][
        "extra_fall_vs_loose"][0]
    assert (row["role"], row["fixture"], row["source"], row["ri"]) \
        == tuple(want[:4])
    assert row["rels"] == ["doc_contract_prefix_unanchored_match"]


def test_holdout_ledger_matches_frozen_prediction():
    hold = json.loads(
        (REPO / "eval" / "evidence" /
         "v21-contract-generalization-prereg-2026-09-22" /
         "MANIFEST.json").read_text())
    ledger = CONTRACT["frozen_ledgers"]["holdout"]
    survivors = {}
    for entry in hold["fixtures"]:
        f = json.loads((REPO / "eval" / "evidence" /
                        "v21-contract-generalization-prereg-2026-09-22"
                        / "fixtures" / (entry["id"] + ".json"))
                       .read_text())
        sim = boundary.simulate_finding(f["finding"], f["fixture"])
        if sim["g2_contract_aware"] == "BLOCK_SURVIVES":
            survivors[entry["id"]] = entry
    assert len(survivors) == ledger["g2_survivors"] == 3
    for fid, label, verdict, _note in ledger["survivors_by_id"]:
        assert fid in survivors
        assert survivors[fid]["expected_label"] == label
    falls = [fid for fid, label, verdict, _ in
             ledger["survivors_by_id"] if verdict == "falls"]
    assert falls == ["dsc-P4"]
    for fid in falls:
        f = json.loads((REPO / "eval" / "evidence" /
                        "v21-contract-generalization-prereg-2026-09-22"
                        / "fixtures" / (fid + ".json")).read_text())
        sim = boundary.simulate_finding(f["finding"], f["fixture"])
        assert rr.route_of(f["finding"], f["fixture"], sim) == \
            "contract_contradiction"
        assert not v21.predicate_names(f["finding"], f["fixture"])
        assert not frozen.relation_names(f["finding"], f["fixture"])


def test_protocol_freezes_decision_points_and_halt_language():
    protocol = (PREREG / "PROTOCOL.md").read_text()
    for phrase in ("preregistration only",
                   "D1 — variant", "D2 — M4 cost",
                   "D3 — dsc-P4 holdout cost",
                   "reproduce its frozen", "halt",
                   "silently reconciled",
                   "explicitly NOT resolved by this experiment",
                   "psd promotion row", "No variant selected",
                   "five of those six FAILED", "22 non-contract bare"):
        assert phrase in protocol, phrase
