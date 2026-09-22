#!/usr/bin/env python3
"""Offline contract-relation verifier study (Phase 17).

Implements exactly the seven candidate relations, admission rule, and
paired evaluation fixed in
eval/evidence/v21-contract-relations-2026-09-22/PROTOCOL.md.

Pair discipline is mechanically enforced: a relation that admits ANY
control blocker corpus-wide is recorded FAILED and auto-excluded from
the candidate gate. Design evidence only — no gate, schema, rubric,
prompt, or corpus change.
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
import eval.v21_routes_replay as rr  # noqa: E402
import parse_review as pr  # noqa: E402

FREEZE = v21.FREEZE
EXPECTED_BLOCKERS = rr.EXPECTED_BLOCKERS

RELATIONS = (
    "pinned_sha_demoted_to_branch",
    "preserved_claim_vs_dropped_call_result",
    "consume_before_validate_ordering",
    "doc_contract_prefix_unanchored_match",
    "secret_logged_by_echo",
    "doc_self_contradiction",
    "jsonl_format_vs_unslurped_jq",
)

DOCS_SUFFIXES = (".md", ".mdx", ".rst", ".txt")


def _added(patch):
    return "\n".join(line[1:] for line in patch.splitlines()
                     if line.startswith("+")).lower()


def _removed(patch):
    return "\n".join(line[1:] for line in patch.splitlines()
                     if line.startswith("-")).lower()


def _contract_region(finding, fixture):
    """Contract side: docstring/comment region, or the whole cited
    content for documentation files (their content IS the contract)."""
    patch = v21._patch(fixture, finding)
    cited = finding.get("file") or ""
    if cited.endswith(DOCS_SUFFIXES):
        return patch.lower()
    return boundary._doc_region(patch).lower()


def relation_names(finding, fixture):
    """The seven preregistered relations; same-file rule inherited
    from Phase 15 (cited file's patch only)."""
    comment = (finding.get("comment") or "").lower()
    patch = v21._patch(fixture, finding).lower()
    added, removed = _added(v21._patch(fixture, finding)), \
        _removed(v21._patch(fixture, finding))
    doc = _contract_region(finding, fixture)
    found = []
    # 1. M2: pinned SHA demoted to a mutable branch ref in one patch.
    if (re.search(r"pin|mutable|supply|@main|branch", comment)
            and re.search(r"[0-9a-f]{40}", removed)
            and (re.search(r"@(?:main|master)\b", added)
                 or re.search(r"(?m)^\s*\w*_?ref:\s*(?:main|master)\s*$",
                              added))):
        found.append("pinned_sha_demoted_to_branch")
    # 2. M7: preserved-semantics claim vs discarded I/O call result.
    if (re.search(r"preserv|same [^\n.]{0,40}(?:semantics|behavior)"
                  r"|discard|no longer", comment)
            and re.search(r"(?:behavior-preserving|preserv\w*|same "
                          r"[^\n.]{0,40}(?:semantics|behavior))", patch)
            and re.search(r"(?m)^\s*urllib\.request\.urlopen\([^)]*\)"
                          r"\s*$", added)):
        found.append("preserved_claim_vs_dropped_call_result")
    # 3. M8: resource consumed (nulled) before a later null-guard.
    consume = [i for i, line in enumerate(added.splitlines())
               if re.search(r"\.state\s*=\s*null", line)]
    guard = [i for i, line in enumerate(added.splitlines())
             if re.search(r"if\s*\([^)]*==\s*null\s*\)\s*return", line)]
    if (re.search(r"clear|consum|before|race|drop", comment)
            and any(c < g for c in consume for g in guard)):
        found.append("consume_before_validate_ordering")
    # 4. M10: doc states a "only ... under <seg>/" prefix contract,
    # code matches <seg>/ unanchored.
    m = re.search(r"\bonly\b[^.\n]{0,80}\bunder\b[^.\n]{0,40}"
                  r"\b([\w-]+)/", doc)
    if (m and re.search(r"bypass|privileg|substring|anywhere|prefix",
                        comment)):
        seg = re.escape(m.group(1))
        if (re.search(r"(?:search|match|find)\([^)]*" + seg + r"/", patch)
                and not re.search(r"(?:search|match|find)\([^)]*\^"
                                  + seg, patch)):
            found.append("doc_contract_prefix_unanchored_match")
    # 5. M14: credential-bearing variable echoed/logged.
    if (re.search(r"leak|credential|token|secret", comment)
            and re.search(r"(?m)^\s*(?:echo|printf|print|log\w*)\b[^\n]*"
                          r"\$\{?[a-z_]*(?:token|secret|password|key|"
                          r"credential)", added)):
        found.append("secret_logged_by_echo")
    # 6. M17/M18: doc promises absolute behavior, same doc documents
    # an exception; comment claims the contradiction.
    if (re.search(r"\b(?:all|every|always|never|only|no human)\b", doc)
            and re.search(r"\b(?:bypass|approval|approvals|unless|"
                          r"manual(?:ly)?)\b", doc)
            and re.search(r"contradic|inconsist|cannot tell|which "
                          r"(?:claim|behavior)", comment)):
        found.append("doc_self_contradiction")
    # 7. M6: patch documents JSONL production, consumer jq reads it
    # with an array filter and no slurp.
    if re.search(r"format|input|per line|jq", comment):
        m = re.search(r"jq\s+-\w*c[^\n]*>>\"\$?([a-z_]\w*)\"", patch)
        if m:
            var = re.escape(m.group(1))
            if re.search(r"(?m)^[+\t ]*(?:if\s+!|!)?\s*jq\s+"
                         r"(?![^\n]*>>)"
                         r"(?![^\n]*(?:-s\b|--slurp\b))"
                         r"[^\n]*\[\][^\n]*[<\"']\"?\$?" + var + r"\b",
                         patch):
                found.append("jsonl_format_vs_unslurped_jq")
    return found


def _corpus_rows():
    fixtures = {f["id"]: f
                for f in rc.load_corpus(ROOT / "eval" / "fixtures")}
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
                rows.append({
                    "source": source,
                    "fixture": fixture["id"],
                    "role": v21._role(finding, fixture),
                    "quote_only": sim["g1_strict_quote"] == "BLOCK_SURVIVES",
                    "route": rr.route_of(finding, fixture, sim),
                    "witnesses": v21.predicate_names(finding, fixture),
                    "relations": relation_names(finding, fixture),
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


def eligibility(rows):
    """Pair discipline: any relation admitting a control is FAILED and
    excluded from the candidate gate."""
    report = {}
    for name in RELATIONS:
        tp = [r for r in rows if name in r["relations"]
              and r["role"] == "true_positive_detection"]
        controls = [r for r in rows if name in r["relations"]
                    and r["role"] == "control_blocker"]
        extras = [r for r in rows if name in r["relations"]
                  and r["role"] == "positive_extra_blocker"]
        report[name] = {
            "eligible": not controls,
            "tp_rows": len(tp),
            "tp_fixtures": sorted({r["fixture"] for r in tp}),
            "control_rows": len(controls),
            "control_fixtures": sorted({r["fixture"] for r in controls}),
            "extra_rows": len(extras),
            "extra_fixtures": sorted({r["fixture"] for r in extras}),
        }
    return report


def _candidate_admitted(row, eligible_names):
    if row["route_typed"]:
        return True
    return (row["route"] == "contract_contradiction"
            and row["quote_only"]
            and bool(set(row["relations"]) & eligible_names))


def _frozen_rows(eligible_names):
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
        relations = relation_names(target, fixture)
        route = rr.route_of(target, fixture)
        admitted = (quote_ok and route == "contract_contradiction"
                    and (bool(witnesses)
                         or bool(set(relations) & eligible_names)))
        if not quote_ok:
            reason = target.get("machine_reason") or "quote gate"
        elif route != "contract_contradiction":
            reason = "route %s (unchanged)" % route
        elif witnesses:
            reason = "existing registry witness: %s" % ",".join(witnesses)
        elif admitted:
            reason = "contract relation: %s" % ",".join(
                sorted(set(relations) & eligible_names))
        else:
            reason = "no eligible relation verifier"
        rows.append({
            "case_id": case["case_id"],
            "fixture": case["fixture"],
            "class": case["class"],
            "route": route,
            "baseline_admitted": bool(quote_ok and witnesses),
            "candidate_admitted": admitted,
            "relations": relations,
            "reason": reason,
        })
    must_admit = "M3-context-only-evidence-quote"
    must_refuse = ("C11-fabricated-contract-contradiction",
                   "M13-external-fact-extrapolation",
                   "C12-honest-uncertainty-downgrade",
                   "M12-contiguous-quote-downgrade")
    by_id = {r["case_id"]: r for r in rows}
    if not by_id[must_admit]["candidate_admitted"]:
        raise RuntimeError("invariant violated: %s must stay admitted"
                           % must_admit)
    for case_id in must_refuse:
        if by_id[case_id]["candidate_admitted"]:
            raise RuntimeError("invariant violated: %s must stay refused"
                               % case_id)
    return rows


def replay():
    rows = _corpus_rows()
    relations = eligibility(rows)
    eligible = {name for name, info in relations.items()
                if info["eligible"]}
    for row in rows:
        row["route_typed"] = bool(
            row["quote_only"] and row["route"] == "contract_contradiction"
            and row["witnesses"])
    for row in rows:
        row["candidate"] = _candidate_admitted(row, eligible)
    controls = [r for r in rows if r["role"] == "control_blocker"]
    if any(r["candidate"] for r in controls):
        raise RuntimeError("candidate gate admitted a control blocker")
    frozen = _frozen_rows(eligible)
    summary = {}
    for key in ("route_typed", "candidate"):
        by_role = {}
        for role in ("control_blocker", "true_positive_detection",
                     "positive_extra_blocker"):
            subset = [r for r in rows if r["role"] == role]
            by_role[role] = {"admitted": sum(r[key] for r in subset),
                             "total": len(subset)}
        summary[key] = by_role
    return {
        "oracle_version": rc.oracle_version(),
        "protocol":
            "eval/evidence/v21-contract-relations-2026-09-22/PROTOCOL.md",
        "phase09": {
            "gate_summary": summary,
            "relations": relations,
            "eligible": sorted(eligible),
            "rows": rows,
        },
        "frozen_cases": frozen,
    }


def main():
    print(json.dumps(replay(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
