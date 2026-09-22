#!/usr/bin/env python3
"""Phase 18B — first out-of-sample evaluation of the six frozen
Phase-17 contract relations on the preregistered holdout.

Implements exactly the operationalization and thresholds frozen in
eval/evidence/v21-contract-generalization-prereg-2026-09-22/PROTOCOL.md:

- per relation: admit-count over its 5 positives and 5 controls;
  GENERALIZATION PASS iff >=4/5 positives and 0/5 controls;
- standing regression guards (C11, C10/M10, M3, M13, C12, M12,
  oracle) via the existing frozen replays;
- fail-closed on any drift of verifier identity, fixture hashes, or
  manifest integrity.

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


def _fixture_defects(rows):
    """Preregistered INVALID path.

    A discovered fixture/oracle defect invalidates the whole authored
    pair. Invalid pairs are excluded from scoring and no relation-level
    PASS/FAIL verdict is assigned until a reviewed amendment and rerun.
    """
    by_id = {r["id"]: r for r in rows}
    defects = {}

    # psd-P4: the positive intended to remove a pinned 40-hex SHA was
    # authored with a 39-hex run instead.
    fixture = json.loads(
        (HOLDOUT / "fixtures" / "psd-P4.json").read_text())
    patch = [f for f in fixture["fixture"]["input"]["files"]
             if f["path"] == fixture["finding"]["file"]][0]["patch"]
    removed = "\n".join(line[1:] for line in patch.splitlines()
                        if line.startswith("-"))
    runs = [run for run in re.findall(r"[0-9a-fA-F]{10,}", removed)]
    lengths = [len(run) for run in runs]
    if lengths != [39]:
        raise RuntimeError("psd-P4 defect proof drift: %s" % lengths)
    defects["psd-P4"] = {
        "defect": "authored pinned ref is not a 40-hex commit SHA",
        "proof": {"hex_runs_in_removed_lines": runs,
                  "lengths": lengths},
        "pair_fixture_ids": ["psd-P4", "psd-C4"],
        "disposition": "INVALID pair per PROTOCOL.md; both P4/C4 are "
                       "excluded from scoring pending reviewed amendment "
                       "and rerun",
    }

    # jfu-P5: 18A authoring basis and the frozen relation definition
    # require an unslurped array consumer (.[]). P5 instead tests jq
    # 'length > 0', a different single-document assumption.
    fixture = json.loads(
        (HOLDOUT / "fixtures" / "jfu-P5.json").read_text())
    patch = [f for f in fixture["fixture"]["input"]["files"]
             if f["path"] == fixture["finding"]["file"]][0]["patch"]
    has_array_filter = ".[]" in patch
    if has_array_filter:
        raise RuntimeError("jfu-P5 scope-defect proof drift: .[] appeared")
    defects["jfu-P5"] = {
        "defect": "fixture is outside frozen relation scope: no .[] "
                  "array-filter consumer",
        "proof": {
            "requires_unslurped_array_consumer": True,
            "array_filter_present": has_array_filter,
            "fixture_rationale": fixture["rationale"],
        },
        "pair_fixture_ids": ["jfu-P5", "jfu-C5"],
        "disposition": "INVALID pair per PROTOCOL.md; both P5/C5 are "
                       "excluded from scoring pending reviewed amendment "
                       "and rerun",
    }

    for defect in defects.values():
        for fixture_id in defect["pair_fixture_ids"]:
            if fixture_id not in by_id:
                raise RuntimeError("invalid-pair member missing: %s"
                                   % fixture_id)
    return defects


def evaluate():
    manifest = json.loads((HOLDOUT / "MANIFEST.json").read_text())
    _fail_closed(manifest)
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
        })
    defects = _fixture_defects(rows)
    invalid_ids = {
        fixture_id
        for defect in defects.values()
        for fixture_id in defect["pair_fixture_ids"]
    }
    for row in rows:
        row["invalid"] = row["id"] in invalid_ids

    per_relation = {}
    for relation in RELATIONS:
        all_positives = [r for r in rows if r["relation"] == relation
                         and r["role"] == "positive"]
        all_controls = [r for r in rows if r["relation"] == relation
                        and r["role"] == "control"]
        positives = [r for r in all_positives if not r["invalid"]]
        controls = [r for r in all_controls if not r["invalid"]]
        invalid_fixture_ids = [r["id"] for r in all_positives + all_controls
                               if r["invalid"]]
        tp = sum(r["admitted"] for r in positives)
        leak = sum(r["admitted"] for r in controls)
        failed_positive_ids = [r["id"] for r in positives
                               if not r["admitted"]]
        leaked_control_ids = [r["id"] for r in controls if r["admitted"]]
        if invalid_fixture_ids:
            verdict = "INVALID_PENDING_AMENDMENT"
        else:
            if len(positives) != 5 or len(controls) != 5:
                raise RuntimeError("unexpected scored population for %s"
                                   % relation)
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
            "invalid_fixture_ids": invalid_fixture_ids,
            "verdict": verdict,
        }
    guards = _regression_guards()
    total_tp = sum(v["positives_admitted"] for v in per_relation.values())
    total_positive = sum(v["positives_total"] for v in per_relation.values())
    total_leak = sum(v["controls_admitted"]
                     for v in per_relation.values())
    total_controls = sum(v["controls_total"] for v in per_relation.values())
    return {
        "phase": "18B",
        "protocol":
            "eval/evidence/v21-contract-generalization-prereg-2026-09-22"
            "/PROTOCOL.md",
        "frozen_verifier": {
            "merge_sha": FROZEN_MERGE_SHA,
            "module_sha256": FROZEN_MODULE_SHA,
        },
        "oracle_version": ORACLE,
        "fixture_rows": rows,
        "per_relation": per_relation,
        "aggregate": {
            "positives_admitted": total_tp,
            "positives_total": total_positive,
            "controls_admitted": total_leak,
            "controls_total": total_controls,
            "raw_observed_positives_admitted": sum(
                r["admitted"] for r in rows if r["role"] == "positive"),
            "raw_observed_positives_total": 30,
            "raw_observed_controls_admitted": sum(
                r["admitted"] for r in rows if r["role"] == "control"),
            "raw_observed_controls_total": 30,
            "relations_pass": sum(1 for v in per_relation.values()
                                  if v["verdict"] == "GENERALIZATION_PASS"),
            "relations_fail": sum(1 for v in per_relation.values()
                                  if v["verdict"] == "GENERALIZATION_FAIL"),
            "relations_invalid": sum(
                1 for v in per_relation.values()
                if v["verdict"] == "INVALID_PENDING_AMENDMENT"),
            "all_pass": all(v["verdict"] == "GENERALIZATION_PASS"
                            for v in per_relation.values()),
            "blanket_promotion_eligible": False,
        },
        "standing_regression_guards": guards,
        "fixture_defects": defects,
    }


def main():
    print(json.dumps(evaluate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
