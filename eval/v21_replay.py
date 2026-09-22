#!/usr/bin/env python3
"""Offline v2.1 candidate-mechanism replay.

This is design evidence, not a gate implementation. It replays two
admission candidates against the frozen Phase-09 records and the five
post-trial regression cases:

quote_only
    Phase-09 G1: a quoted span exists in the cited patch.
closed_world_predicates
    quote_only plus a small, independently checkable predicate that
    recognizes the claimed defect shape from the patch. This is
    intentionally conservative: it demonstrates the coverage tradeoff
    rather than claiming general semantic entailment.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import eval.evidence_boundary_sim as boundary  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import parse_review as pr  # noqa: E402

FREEZE = ROOT / "eval" / "evidence" / "v2-declaration-regression-freeze-2026-09-22"


def _patch(fixture, finding):
    """Patch text for the finding's cited file only.

    A structural witness must not borrow evidence from another changed
    file in the same fixture.
    """
    cited = finding.get("file")
    for f in fixture["input"]["files"]:
        if f["path"] == cited:
            return f.get("patch") or ""
    return ""


def predicate_names(finding, fixture):
    """Closed-world, evidence-independent structural witnesses.

    A predicate checks code/patch structure plus the finding's claimed
    defect family. It never treats quote existence as semantic proof.
    The small registry is intentionally not a universal reviewer.
    """
    comment = (finding.get("comment") or "").lower()
    patch = _patch(fixture, finding).lower()
    found = []
    # M3: a documented parsed-date freshness contract implemented with
    # filesystem mtime. Both sides are checked from the patch.
    if ("mtime" in comment and "-mtime" in patch
            and ("parsed date" in patch or "last reviewed" in patch)):
        found.append("parsed_date_vs_mtime")
    # M11: failure result discarded and success hard-coded. C11 has a
    # status=failed path, so it deliberately does not match.
    if ("status=ok" in patch and "|| true" in patch
            and "status=failed" not in patch
            and re.search(r"success|status|discard|ignore", comment)):
        found.append("hardcoded_success_status")
    # M12: caught parse/origin failures return a fallback value.
    if ("except (originerror, parseerror)" in patch
            and "return _cache.get" in patch
            and re.search(r"mask|swallow|parseerror|empty cache|stale", comment)):
        found.append("masked_failure_fallback")
    # M16: generic exception is swallowed before a success response.
    if ("except exception:" in patch
            and re.search(r"(?m)^\s*[+-]?\s*pass\s*$", patch)
            and re.search(r"success|swallow|fabricat|false|mislead|discard", comment)):
        found.append("swallowed_exception_success")
    # A mutable action reference is independently visible in the diff.
    if (re.search(r"uses:\s*[^\s@]+@v\d+\b", patch)
            and re.search(
                r"\b(?:pin|pinned|floating|mutable|immutable)\b|@v\d+\b",
                comment)):
        found.append("mutable_action_reference")
    return found


def _role(finding, fixture):
    if fixture["kind"] == "control":
        return "control_blocker"
    if rc.matches_any_alternative(fixture["expected"]["groups"], finding):
        return "true_positive_detection"
    return "positive_extra_blocker"


def _phase09_rows():
    fixtures = {f["id"]: f for f in rc.load_corpus(ROOT / "eval" / "fixtures")}
    rows = []
    source_records = 0
    for source, rel in boundary.SOURCES.items():
        records = [json.loads(line) for line in (ROOT / rel).read_text().splitlines()
                   if line.strip()]
        source_records += len(records)
        for rec in records:
            fixture = fixtures[rec["fixture"]]
            for finding in (rec.get("result") or {}).get("findings", []):
                if finding.get("severity") != "blocking":
                    continue
                sim = boundary.simulate_finding(finding, fixture)
                quotes = sim["g1_strict_quote"] == "BLOCK_SURVIVES"
                predicates = predicate_names(finding, fixture)
                rows.append({
                    "source": source,
                    "fixture": fixture["id"],
                    "role": _role(finding, fixture),
                    "quote_only": quotes,
                    "closed_world_predicates": bool(quotes and predicates),
                    "predicates": predicates,
                })
    if source_records != boundary.EXPECTED_TOTAL:
        raise RuntimeError(
            "Phase-09 source population drift: expected %d records, found %d"
            % (boundary.EXPECTED_TOTAL, source_records))
    return rows, source_records


def _frozen_rows():
    fixtures = {f["id"]: f for f in rc.load_corpus(ROOT / "eval" / "fixtures")}
    rows = []
    for path in sorted((FREEZE / "cases").glob("*.json")):
        case = json.loads(path.read_text())
        fixture = fixtures[case["fixture"]]
        result, audit = pr.normalize_v2(case["raw_model_output"],
                                        {f["path"]: f["patch"]
                                         for f in fixture["input"]["files"]},
                                        gate=True)
        if result != case["expected_result"]:
            raise RuntimeError("frozen result drift for %s" % case["case_id"])
        if audit != case["expected_gate_audit"]:
            raise RuntimeError("frozen gate-audit drift for %s"
                               % case["case_id"])
        # Failure cases target their sole admitted blocker. Good controls
        # target their sole machine-downgraded finding (M12's record also
        # has an unrelated honest survivor, which must not mask the
        # downgrade control in this projection). Cardinality is explicit
        # so a future multi-finding record cannot silently retarget replay.
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
        predicates = predicate_names(target, fixture) if target else []
        rows.append({
            "case_id": case["case_id"],
            "fixture": case["fixture"],
            "class": case["class"],
            "quote_only": bool(target and target["severity"] == "blocking"),
            "closed_world_predicates": bool(
                target and target["severity"] == "blocking" and predicates),
            "predicates": predicates,
        })
    return rows


def _summary(rows, keys=("quote_only", "closed_world_predicates")):
    out = {}
    for key in keys:
        by_role = {}
        for role in ("control_blocker", "true_positive_detection", "positive_extra_blocker"):
            subset = [r for r in rows if r.get("role") == role]
            by_role[role] = {"admitted": sum(r[key] for r in subset),
                             "total": len(subset)}
        out[key] = by_role
    return out


def replay():
    phase09, source_records = _phase09_rows()
    frozen = _frozen_rows()
    return {
        "oracle_version": rc.oracle_version(),
        "methodology": {
            "quote_only": "Phase-09 G1 quoted-span admission",
            "closed_world_predicates": "G1 plus a matching independently "
                                       "checkable patch predicate",
            "limit": "predicate registry is deliberately narrow; replay "
                     "measures coverage loss, not semantic completeness",
        },
        "phase09": {
            "source_records": source_records,
            "rows": phase09,
            "summary": _summary(phase09),
        },
        "frozen_cases": frozen,
    }


def main():
    print(json.dumps(replay(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
