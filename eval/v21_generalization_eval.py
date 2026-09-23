#!/usr/bin/env python3
"""Phase 18B/18D — out-of-sample evaluation of the six frozen
Phase-17 contract relations on the preregistered holdout.

18B ran this evaluator against the original holdout and its frozen
report is published verbatim under
eval/evidence/v21-contract-generalization-eval-2026-09-22/ (0 PASS,
4 FAIL, 2 INVALID). The two INVALID pairs were corrected by the
reviewed 18C amendment (see AMENDMENT.md in the holdout directory);
this evaluator now carries the amended state:

- `_amendments()` fail-closed asserts the CORRECTED fixture state;
- `evaluate_amended_pairs()` runs the frozen verifier on exactly the
  four amended fixtures (18D step 1);
- `evaluate()` performs the full reconciliation run (18D step 2):
  all 60 fixtures, no exclusions, thresholds unchanged.

The subject module is called, never modified. Fixture files are read,
never written.
"""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import eval.run_corpus as rc  # noqa: E402
import eval.v21_contract_relations as frozen  # noqa: E402
import eval.v21_routes_replay as rr  # noqa: E402

HOLDOUT = ROOT / "eval" / "evidence" / \
    "v21-contract-generalization-prereg-2026-09-22"

FROZEN_MERGE_SHA = "0631b0956f795ab1ee6d13f68b0c1cebe8a6d23b"
FROZEN_MODULE_SHA = ("bb0ebdeeb7fc80395626bf10d3e9ad1a730936ccf0a"
                     "b7e719c43c1b5754b1b57")
ORACLE = "117b4164e5446f50"
THRESHOLD_TP = 4

RELATIONS = (
    "pinned_sha_demoted_to_branch",
    "preserved_claim_vs_dropped_call_result",
    "consume_before_validate_ordering",
    "secret_logged_by_echo",
    "doc_self_contradiction",
    "jsonl_format_vs_unslurped_jq",
)


def _fail_closed(manifest):
    if manifest["frozen_verifier"]["merge_sha"] != FROZEN_MERGE_SHA:
        raise RuntimeError("frozen verifier merge-SHA drift")
    current = hashlib.sha256(
        (ROOT / "eval" / "v21_contract_relations.py").read_bytes()
    ).hexdigest()
    if manifest["frozen_verifier"]["module_sha256"] != FROZEN_MODULE_SHA:
        raise RuntimeError("manifest pins a different verifier module")
    if current != FROZEN_MODULE_SHA:
        raise RuntimeError(
            "eval/v21_contract_relations.py does not match the frozen "
            "Phase-17 implementation; evaluation is void")
    counts = manifest["counts"]
    if counts != {"relations": 6, "pairs_per_relation": 5,
                  "positives": 30, "controls": 30, "total": 60}:
        raise RuntimeError("holdout population drift")
    entries = sorted(manifest["fixtures"], key=lambda e: e["id"])
    if len(entries) != 60:
        raise RuntimeError("fixture count drift")
    lines = []
    for entry in entries:
        raw = (HOLDOUT / "fixtures" / (entry["id"] + ".json")).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise RuntimeError("fixture hash drift for %s" % entry["id"])
        lines.append("%s  %s" % (entry["sha256"], entry["id"]))
    digest = hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()
    if digest != manifest["manifest_lines_sha256"]:
        raise RuntimeError("manifest lines hash drift")


def _regression_guards():
    rr_report = rr.replay()
    if rr_report["oracle_version"] != ORACLE:
        raise RuntimeError("oracle identity drift")
    five = {c["case_id"]: c for c in rr_report["frozen_cases"]}
    guards = {
        "oracle": ORACLE,
        "C11_refused": not five["C11-fabricated-contract-contradiction"]
        ["closed_world_predicates"],
        "M3_admitted_via_existing_witness": five[
            "M3-context-only-evidence-quote"]["closed_world_predicates"],
        "M13_refused": not five["M13-external-fact-extrapolation"]
        ["closed_world_predicates"],
        "C12_refused": not five["C12-honest-uncertainty-downgrade"]
        ["closed_world_predicates"],
        "M12_refused": not five["M12-contiguous-quote-downgrade"]
        ["closed_world_predicates"],
    }
    m10 = frozen.replay()["phase09"]["relations"][
        "doc_contract_prefix_unanchored_match"]
    guards["M10_relation_still_FAILED"] = m10["eligible"] is False
    guards["C10_standing_near_miss"] = "C10" in m10["control_fixtures"]
    if not all(v is True for k, v in guards.items() if k != "oracle"):
        raise RuntimeError("standing regression guard violated: %s"
                           % guards)
    return guards


def _fixture_patch(fixture_id):
    fixture = json.loads(
        (HOLDOUT / "fixtures" / (fixture_id + ".json")).read_text())
    return fixture, [f for f in fixture["fixture"]["input"]["files"]
                     if f["path"] == fixture["finding"]["file"]][0]["patch"]


def _amendments():
    """18C amendment state (fail-closed): the two 18B INVALID pairs
    were corrected by the reviewed amendment; proofs assert the
    CORRECTED state. Re-evaluation of the amended pairs is reserved
    for 18D."""
    _, psd_patch = _fixture_patch("psd-P4")
    removed = "\n".join(line[1:] for line in psd_patch.splitlines()
                        if line.startswith("-"))
    runs = [run for run in re.findall(r"[0-9a-fA-F]{10,}", removed)]
    lengths = [len(run) for run in runs]
    if lengths != [40]:
        raise RuntimeError("psd-P4 amendment proof drift: %s" % lengths)
    _, jfu_patch = _fixture_patch("jfu-P5")
    if ".[]" not in jfu_patch:
        raise RuntimeError("jfu-P5 amendment proof drift: no .[] consumer")
    if not re.search(r"jq\s+-\w*c[^\n]*>>\"\$?[a-z_]\w*\"", jfu_patch):
        raise RuntimeError("jfu-P5 amendment proof drift: no JSONL "
                           "producer")
    return {
        "psd-P4": {
            "original_defect": "authored pinned ref was a 39-hex run, "
                               "not a 40-hex commit SHA",
            "proof": {"hex_runs_in_removed_lines": runs,
                      "lengths": lengths},
            "pair_fixture_ids": ["psd-P4", "psd-C4"],
            "disposition": "AMENDED by reviewed 18C amendment; all refs "
                           "are genuine 40-hex SHAs; pair re-enters "
                           "scoring in 18D",
        },
        "jfu-P5": {
            "original_defect": "positive tested jq 'length > 0' over "
                               "JSONL, outside the frozen unslurped-array "
                               "relation definition",
            "proof": {"array_filter_present": True,
                      "jsonl_producer_present": True},
            "pair_fixture_ids": ["jfu-P5", "jfu-C5"],
            "disposition": "AMENDED by reviewed 18C amendment; frozen-"
                           "definition positive in place; pair re-enters "
                           "scoring in 18D",
        },
    }


def evaluate_amended_pairs():
    """18D step 1: frozen-verifier results for exactly the four
    amended fixtures (psd-P4, psd-C4, jfu-P5, jfu-C5)."""
    manifest = json.loads((HOLDOUT / "MANIFEST.json").read_text())
    _fail_closed(manifest)
    amended = sorted({fixture_id
                      for record in _amendments().values()
                      for fixture_id in record["pair_fixture_ids"]})
    rows = []
    for entry in sorted(manifest["fixtures"], key=lambda e: e["id"]):
        if entry["id"] not in amended:
            continue
        fixture = json.loads(
            (HOLDOUT / "fixtures" / (entry["id"] + ".json")).read_text())
        fired = sorted(frozen.relation_names(fixture["finding"],
                                             fixture["fixture"]))
        rows.append({
            "id": entry["id"],
            "relation": entry["relation"],
            "role": entry["role"],
            "expected_label": entry["expected_label"],
            "fired_relations": fired,
            "admitted": entry["relation"] in fired,
        })
    return rows


def evaluate():
    """18D step 2: full reconciliation run over all 60 amended-state
    fixtures. By determinism the 52 unchanged fixtures must reproduce
    the 18B valid observations exactly; 18D pins that reconciliation
    before publishing final verdicts."""
    manifest = json.loads((HOLDOUT / "MANIFEST.json").read_text())
    _fail_closed(manifest)
    amendments = _amendments()
    amended_ids = {fixture_id
                   for record in amendments.values()
                   for fixture_id in record["pair_fixture_ids"]}
    rows = []
    for entry in sorted(manifest["fixtures"], key=lambda e: e["id"]):
        fixture = json.loads(
            (HOLDOUT / "fixtures" / (entry["id"] + ".json")).read_text())
        fired = sorted(frozen.relation_names(fixture["finding"],
                                             fixture["fixture"]))
        rows.append({
            "id": entry["id"],
            "relation": entry["relation"],
            "role": entry["role"],
            "probe": entry["probe"],
            "expected_label": entry["expected_label"],
            "fired_relations": fired,
            "admitted": entry["relation"] in fired,
            "amended": entry["id"] in amended_ids,
        })

    per_relation = {}
    for relation in RELATIONS:
        positives = [r for r in rows if r["relation"] == relation
                     and r["role"] == "positive"]
        controls = [r for r in rows if r["relation"] == relation
                    and r["role"] == "control"]
        if len(positives) != 5 or len(controls) != 5:
            raise RuntimeError("unexpected scored population for %s"
                               % relation)
        tp = sum(r["admitted"] for r in positives)
        leak = sum(r["admitted"] for r in controls)
        failed_positive_ids = [r["id"] for r in positives
                               if not r["admitted"]]
        leaked_control_ids = [r["id"] for r in controls if r["admitted"]]
        verdict = ("GENERALIZATION_PASS"
                   if tp >= THRESHOLD_TP and leak == 0
                   else "GENERALIZATION_FAIL")
        per_relation[relation] = {
            "positives_admitted": tp,
            "positives_total": len(positives),
            "controls_admitted": leak,
            "controls_total": len(controls),
            "failed_positive_ids": failed_positive_ids,
            "leaked_control_ids": leaked_control_ids,
            "verdict": verdict,
        }
    guards = _regression_guards()
    total_tp = sum(v["positives_admitted"] for v in per_relation.values())
    total_leak = sum(v["controls_admitted"]
                     for v in per_relation.values())
    return {
        "phase": "18D",
        "protocol":
            "eval/evidence/v21-contract-generalization-prereg-2026-09-22"
            "/PROTOCOL.md",
        "amendment":
            "eval/evidence/v21-contract-generalization-prereg-2026-09-22"
            "/AMENDMENT.md",
        "frozen_verifier": {
            "merge_sha": FROZEN_MERGE_SHA,
            "module_sha256": FROZEN_MODULE_SHA,
        },
        "oracle_version": ORACLE,
        "fixture_rows": rows,
        "per_relation": per_relation,
        "aggregate": {
            "positives_admitted": total_tp,
            "positives_total": 30,
            "controls_admitted": total_leak,
            "controls_total": 30,
            "relations_pass": sum(1 for v in per_relation.values()
                                  if v["verdict"] == "GENERALIZATION_PASS"),
            "relations_fail": sum(1 for v in per_relation.values()
                                  if v["verdict"] == "GENERALIZATION_FAIL"),
            "all_pass": all(v["verdict"] == "GENERALIZATION_PASS"
                            for v in per_relation.values()),
            "blanket_promotion_eligible": False,
        },
        "standing_regression_guards": guards,
        "amendments": amendments,
    }


def main():
    print(json.dumps(evaluate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
