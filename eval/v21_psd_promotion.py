#!/usr/bin/env python3
"""Phase 19B — execute the frozen psd-only blocking-boundary
promotion preregistered in Phase 19A.

Implements exactly the rule and invariants of
eval/evidence/v21-psd-promotion-prereg-2026-09-23/INTEGRATION_CONTRACT.json:

- baseline decision = `g2_contract_aware` over the frozen 276-row
  blocking population;
- integrated decision = `BLOCK_EVIDENCE_BACKED` iff the finding is on
  the contract_contradiction route AND the frozen verifier fires
  `pinned_sha_demoted_to_branch` AND baseline is DOWNGRADE;
- every other row keeps its baseline decision byte-identically
  (zero-collateral halt gate);
- promotion set must equal the frozen one-row prediction exactly;
- landscape (psd-fired counts and splits) must equal the frozen
  predictions exactly;
- zero promotions on control/extra rows;
- standing regression guards and historical-artifact hashes verified.

The frozen Phase-17 verifier, routes, predicates, parser, fixtures,
and oracle are called, never modified.
"""
import hashlib
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import eval.evidence_boundary_sim as boundary  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import eval.v21_contract_relations as frozen  # noqa: E402
import eval.v21_generalization_eval as gen  # noqa: E402
import eval.v21_replay as v21  # noqa: E402
import eval.v21_routes_replay as rr  # noqa: E402

PREREG = ROOT / "eval" / "evidence" / "v21-psd-promotion-prereg-2026-09-23"
PSD = "pinned_sha_demoted_to_branch"
CONTRACT_ROUTE = "contract_contradiction"
EVIDENCE_BLOCK = "BLOCK_EVIDENCE_BACKED"

ORACLE = "117b4164e5446f50"
FROZEN_18B_REPORT = gen.FROZEN_18B_REPORT
FROZEN_18B_REPORT_SHA = gen.FROZEN_18B_REPORT_SHA
FROZEN_18D_REPORT = (ROOT / "eval" / "evidence" /
                     "v21-contract-generalization-eval-2026-09-22" /
                     "generalization-report-18d.json")
FROZEN_18D_REPORT_SHA = ("0a2bb7fa64be61a4c6b1f4b00b63c53a758fe1fed5d2"
                         "1fd169d067011af8dc26")


def _halt(message):
    raise RuntimeError("19B halt: %s" % message)


def _contract():
    raw = (PREREG / "INTEGRATION_CONTRACT.json").read_bytes()
    contract = json.loads(raw)
    subject = contract["subject"]
    current = hashlib.sha256(
        (ROOT / "eval" / "v21_contract_relations.py").read_bytes()
    ).hexdigest()
    if subject["verifier_module_sha256"] != current:
        _halt("prereg contract pins a different verifier module")
    if subject["verifier_merge_sha"] != gen.FROZEN_MERGE_SHA:
        _halt("prereg contract merge-SHA drift")
    if contract["oracle_version"] != ORACLE:
        _halt("oracle identity drift in prereg contract")
    if contract["phase"] != "19A" or not contract[
            "preregistered_before_any_19b_run"]:
        _halt("prereg contract is not a 19A preregistration")
    if contract["promotion_rule"]["promoted_value"] != EVIDENCE_BLOCK:
        _halt("promotion-rule value drift")
    if contract["scope"]["route"] != CONTRACT_ROUTE or \
            contract["scope"]["relations_promoted"] != [PSD]:
        _halt("promotion-scope drift")
    return raw, contract


def _rows():
    fixtures = {f["id"]: f
                for f in rc.load_corpus(ROOT / "eval" / "fixtures")}
    rows = []
    total_records = 0
    for source, rel in boundary.SOURCES.items():
        records = [json.loads(line)
                   for line in (ROOT / rel).read_text().splitlines()
                   if line.strip()]
        total_records += len(records)
        for ri, rec in enumerate(records):
            fixture = fixtures[rec["fixture"]]
            for fi, finding in enumerate(
                    (rec.get("result") or {}).get("findings", [])):
                if finding.get("severity") != "blocking":
                    continue
                sim = boundary.simulate_finding(finding, fixture)
                rows.append({
                    "source": source, "record_index": ri,
                    "finding_index": fi, "fixture": fixture["id"],
                    "role": v21._role(finding, fixture),
                    "route": rr.route_of(finding, fixture, sim),
                    "fired_relations": frozen.relation_names(finding,
                                                             fixture),
                    "g1_strict_quote": sim["g1_strict_quote"],
                    "baseline": sim["g2_contract_aware"],
                })
    if total_records != boundary.EXPECTED_TOTAL:
        _halt("record population drift: %d" % total_records)
    if len(rows) != 276:
        _halt("blocking-row population drift: %d" % len(rows))
    return rows


def _identity(row):
    return {
        "source": row["source"],
        "record_index": row["record_index"],
        "finding_index": row["finding_index"],
        "fixture": row["fixture"],
        "route": row["route"],
        "role": row["role"],
        "g1_strict_quote": row["g1_strict_quote"],
        "baseline": row["baseline"],
    }


def _same_identity(row, predicted):
    """A live row matches a frozen promotion prediction. The frozen
    shape names the baseline field `g2_contract_aware` and carries
    `finding_file`, which is verified against the record itself."""
    return (row["source"] == predicted["source"]
            and row["record_index"] == predicted["record_index"]
            and row["finding_index"] == predicted["finding_index"]
            and row["fixture"] == predicted["fixture"]
            and row["route"] == predicted["route"]
            and row["role"] == predicted["role"]
            and row["g1_strict_quote"] == predicted["g1_strict_quote"]
            and row["baseline"] == predicted["g2_contract_aware"])


def _splits_match(expected, observed):
    """Split dictionaries match with explicit frozen zeros allowed:
    every expected count must equal the observed count (0 if absent),
    and no unexpected key may appear."""
    return (all(observed.get(k, 0) == v for k, v in expected.items())
            and set(observed) <= set(expected))


def evaluate():
    contract_raw, contract = _contract()
    predictions = contract["frozen_predictions"]
    rows = _rows()
    for row in rows:
        row["psd"] = PSD in row["fired_relations"]
        row["integrated"] = (
            EVIDENCE_BLOCK
            if row["route"] == CONTRACT_ROUTE and row["psd"]
            and row["baseline"] == "DOWNGRADE"
            else row["baseline"])

    # landscape checks against the frozen predictions
    fired = [r for r in rows if r["psd"]]
    landscape = {
        "psd_fires_on": len(fired),
        "psd_fired_roles": dict(Counter(r["role"] for r in fired)),
        "psd_fired_fixtures": dict(Counter(r["fixture"] for r in fired)),
        "psd_fired_baseline_split": dict(Counter(r["baseline"]
                                                 for r in fired)),
        "downgraded_psd_fired_by_route": dict(
            Counter(r["route"] for r in fired
                    if r["baseline"] == "DOWNGRADE")),
    }
    for key, expected in predictions.items():
        if key not in landscape:
            continue
        if isinstance(expected, int):
            ok = expected == landscape[key]
        else:
            ok = _splits_match(expected, landscape[key])
        if not ok:
            _halt("frozen landscape prediction drift for %s: "
                  "expected %s, observed %s"
                  % (key, expected, landscape[key]))

    # promotion set must equal the frozen prediction exactly
    promoted = [r for r in rows if r["integrated"] == EVIDENCE_BLOCK]
    predicted = predictions["promotion_set"]
    if len(promoted) != len(predicted):
        _halt("promotion-set size drift: expected %d, observed %d"
              % (len(predicted), len(promoted)))
    for row, want in zip(promoted, predicted):
        if not _same_identity(row, want):
            _halt("promotion-set identity drift: observed %s vs "
                  "frozen %s" % (_identity(row), want))
        record = [json.loads(line)
                  for line in (ROOT / boundary.SOURCES[row["source"]])
                  .read_text().splitlines() if line.strip()][
                      row["record_index"]]
        finding = record["result"]["findings"][row["finding_index"]]
        if finding.get("file") != want["finding_file"]:
            _halt("promotion-set finding-file drift for %s" % want)

    # zero-collateral halt gate: rows whose decision changed must be
    # exactly the rule-promoted rows (mechanical, not by construction)
    def _key(row):
        return json.dumps(_identity(row), sort_keys=True)

    changed = {k for k, r in (( _key(r), r) for r in rows)
               if r["integrated"] != r["baseline"]}
    promoted_ids = {_key(r) for r in promoted}
    if changed != promoted_ids:
        _halt("collateral decision change outside the promotion rule")
    collateral = []
    control_or_extra = [
        {"row": _identity(r), "integrated": r["integrated"]}
        for r in promoted
        if r["role"] in ("control_blocker", "positive_extra_blocker")]
    if control_or_extra:
        _halt("control or extra promotion: %s"
              % json.dumps(control_or_extra, sort_keys=True))

    # historical artifacts must be byte-for-byte unchanged
    historical = {}
    for path, pin in ((FROZEN_18B_REPORT, FROZEN_18B_REPORT_SHA),
                      (FROZEN_18D_REPORT, FROZEN_18D_REPORT_SHA)):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != pin:
            _halt("historical artifact drift: %s" % path.name)
        historical[path.name] = digest

    baseline_split = Counter(r["baseline"] for r in rows)
    integrated_split = Counter(r["integrated"] for r in rows)
    guards = gen._regression_guards()
    return {
        "phase": "19B",
        "prereg": {
            "protocol":
                "eval/evidence/v21-psd-promotion-prereg-2026-09-23"
                "/PROTOCOL.md",
            "contract":
                "eval/evidence/v21-psd-promotion-prereg-2026-09-23"
                "/INTEGRATION_CONTRACT.json",
            "contract_sha256": hashlib.sha256(
                contract_raw).hexdigest(),
        },
        "frozen_verifier": {
            "merge_sha": gen.FROZEN_MERGE_SHA,
            "module_sha256": gen.FROZEN_MODULE_SHA,
        },
        "oracle_version": ORACLE,
        "rule": contract["promotion_rule"]["condition"],
        "population": len(rows),
        "baseline_aggregate": dict(baseline_split),
        "integrated_aggregate": dict(integrated_split),
        "promotion_set": [dict(_identity(r),
                               integrated=r["integrated"],
                               fired_relations=r["fired_relations"])
                          for r in promoted],
        "unchanged_rows": sum(1 for r in rows
                              if r["integrated"] == r["baseline"]),
        "collateral_changes": collateral,
        "control_or_extra_promotions": control_or_extra,
        "landscape_observed": landscape,
        "historical_artifacts_unchanged": historical,
        "standing_regression_guards": guards,
        "success": True,
        "meaning": (
            "psd is eligible as the first evidence-backed blocker on "
            "the contract_contradiction route for this oracle only. "
            "This does NOT authorize GATING activation, does not "
            "promote the broader registry, and does not address the "
            "baseline's 27 surviving control blockers. The 18 "
            "psd-matching downgrades outside the contract route "
            "remain downgraded by design (route boundary preserved)."),
    }


def main():
    print(json.dumps(evaluate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
