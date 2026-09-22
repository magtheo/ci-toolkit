#!/usr/bin/env python3
"""Offline v2.1 claim-route replay (Phase 16).

Implements exactly the taxonomy, precedence, and admission rules fixed
in eval/evidence/v21-routes-2026-09-22/PROTOCOL.md. Design evidence
only: no gate, schema, rubric, prompt, or corpus change.

The route step never widens admission relative to the Phase-15
closed-world registry: both require the quote gate plus a registry
witness. Routes explain refusals and locate the missing verification
infrastructure per claim class.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import eval.evidence_boundary_sim as boundary  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import eval.v21_replay as v21  # noqa: E402
import parse_review as pr  # noqa: E402

FREEZE = v21.FREEZE

EXPECTED_BLOCKERS = 276

ROUTES = ("out_of_diff", "contract_contradiction", "witnessed_behavior",
          "external_fact", "unwitnessed_behavior")

# Protocol route 4 vocabulary: the harm's actor or resource lies
# outside the diff. Fixed in PROTOCOL.md before results were recorded.
EXTERNAL_ACTOR_RE = re.compile(
    r"secret|credential|token\b|registry|publish|exfiltrat|leak|"
    r"attacker|untrusted|pull_request_target|reusable workflow|"
    r"deploy|privileg", re.I)


def route_of(finding, fixture, sim=None):
    """Single claim route per finding, by fixed precedence."""
    sim = sim or boundary.simulate_finding(finding, fixture)
    if not sim["file_in_diff"]:
        return "out_of_diff"
    comment = finding.get("comment") or ""
    if (boundary.CONTRACT_REF_RE.search(comment)
            and boundary.CONTRADICTION_RE.search(comment)):
        return "contract_contradiction"
    if v21.predicate_names(finding, fixture):
        return "witnessed_behavior"
    if EXTERNAL_ACTOR_RE.search(comment):
        return "external_fact"
    return "unwitnessed_behavior"


def route_admits(route, quote_ok, witnesses):
    """Fixed admission rules from PROTOCOL.md."""
    if not quote_ok:
        return False, "quote gate not satisfied"
    if route == "witnessed_behavior":
        return True, "witness: %s" % ",".join(witnesses)
    if route == "contract_contradiction":
        if witnesses:
            return True, "relation witness: %s" % ",".join(witnesses)
        return False, "no registered relation verifier"
    if route == "external_fact":
        return False, "external route offline-refused (needs pinned fact + bounded consequence)"
    if route == "out_of_diff":
        return False, "cited file not in diff"
    return False, "no witness infrastructure"


def _corpus_rows():
    fixtures = {f["id"]: f for f in rc.load_corpus(ROOT / "eval" / "fixtures")}
    rows = []
    source_records = 0
    for source, rel in boundary.SOURCES.items():
        records = [json.loads(line)
                   for line in (ROOT / rel).read_text().splitlines()
                   if line.strip()]
        source_records += len(records)
        for rec in records:
            fixture = fixtures[rec["fixture"]]
            for finding in (rec.get("result") or {}).get("findings", []):
                if finding.get("severity") != "blocking":
                    continue
                sim = boundary.simulate_finding(finding, fixture)
                quote_ok = sim["g1_strict_quote"] == "BLOCK_SURVIVES"
                witnesses = v21.predicate_names(finding, fixture)
                route = route_of(finding, fixture, sim)
                admitted, reason = route_admits(route, quote_ok, witnesses)
                closed_world = bool(quote_ok and witnesses)
                if admitted != closed_world:
                    raise RuntimeError(
                        "route admission identity violated at %s/%s"
                        % (source, fixture["id"]))
                rows.append({
                    "source": source,
                    "fixture": fixture["id"],
                    "role": v21._role(finding, fixture),
                    "quote_only": quote_ok,
                    "closed_world_predicates": closed_world,
                    "route_typed": admitted,
                    "route": route,
                    "witnesses": witnesses,
                    "admission_reason": reason,
                })
    if source_records != boundary.EXPECTED_TOTAL:
        raise RuntimeError(
            "Phase-09 source population drift: expected %d records, found %d"
            % (boundary.EXPECTED_TOTAL, source_records))
    if len(rows) != EXPECTED_BLOCKERS:
        raise RuntimeError(
            "blocking-finding population drift: expected %d, found %d"
            % (EXPECTED_BLOCKERS, len(rows)))
    return rows


def _frozen_rows():
    fixtures = {f["id"]: f
                for f in rc.load_corpus(ROOT / "eval" / "fixtures")}
    rows = []
    for path in sorted((FREEZE / "cases").glob("*.json")):
        case = json.loads(path.read_text())
        fixture = fixtures[case["fixture"]]
        result, audit = pr.normalize_v2(
            case["raw_model_output"],
            {f["path"]: f["patch"] for f in fixture["input"]["files"]},
            gate=True)
        if result != case["expected_result"]:
            raise RuntimeError("frozen result drift for %s" % case["case_id"])
        if audit != case["expected_gate_audit"]:
            raise RuntimeError("frozen gate-audit drift for %s"
                               % case["case_id"])
        if case["class"] == "good_boundary_control":
            targets = [f for f in result["findings"]
                       if f.get("machine_reason")]
        else:
            targets = [f for f in result["findings"]
                       if f["severity"] == "blocking"]
        if len(targets) != 1:
            raise RuntimeError(
                "expected exactly one replay target for %s, found %d"
                % (case["case_id"], len(targets)))
        target = targets[0]
        quote_ok = target["severity"] == "blocking"
        witnesses = v21.predicate_names(target, fixture)
        route = route_of(target, fixture)
        admitted, reason = route_admits(route, quote_ok, witnesses)
        if admitted != bool(quote_ok and witnesses):
            raise RuntimeError(
                "route admission identity violated for %s" % case["case_id"])
        if not quote_ok:
            reason = target.get("machine_reason") or reason
        rows.append({
            "case_id": case["case_id"],
            "fixture": case["fixture"],
            "class": case["class"],
            "quote_only": quote_ok,
            "closed_world_predicates": bool(quote_ok and witnesses),
            "route_typed": admitted,
            "route": route,
            "witnesses": witnesses,
            "admission_reason": reason,
        })
    return rows


def _gate_summary(rows):
    out = {}
    for key in ("quote_only", "closed_world_predicates", "route_typed"):
        by_role = {}
        for role in ("control_blocker", "true_positive_detection",
                     "positive_extra_blocker"):
            subset = [r for r in rows if r.get("role") == role]
            by_role[role] = {"admitted": sum(r[key] for r in subset),
                             "total": len(subset)}
        out[key] = by_role
    return out


def _route_summary(rows):
    out = {}
    for route in ROUTES:
        subset = [r for r in rows if r["route"] == route]
        out[route] = {}
        for role in ("control_blocker", "true_positive_detection",
                     "positive_extra_blocker"):
            cells = [r for r in subset if r["role"] == role]
            out[route][role] = {
                "total": len(cells),
                "admitted": sum(r["route_typed"] for r in cells),
            }
    return out


def replay():
    corpus = _corpus_rows()
    frozen = _frozen_rows()
    return {
        "oracle_version": rc.oracle_version(),
        "protocol": "eval/evidence/v21-routes-2026-09-22/PROTOCOL.md",
        "methodology": {
            "routes": list(ROUTES),
            "precedence": "out_of_diff > contract_contradiction > "
                          "witnessed_behavior > external_fact > "
                          "unwitnessed_behavior",
            "identity": "route_typed admission == Phase-15 "
                        "closed_world_predicates admission (checked per "
                        "row, fail-closed)",
            "limit": "route classification is comment/patch heuristics on "
                     "v1 records; an UPPER BOUND reconstruction, as in "
                     "Phase 09",
        },
        "phase09": {
            "rows": corpus,
            "gate_summary": _gate_summary(corpus),
            "route_summary": _route_summary(corpus),
        },
        "frozen_cases": frozen,
    }


def main():
    print(json.dumps(replay(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
