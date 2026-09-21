"""Phase-09 evidence-boundary SIMULATION — deterministic, offline,
zero provider calls, zero evidence mutation.

Question replayed over the frozen 414 Stage-A/B1 records:

    Had a blocker required a verifiable harm-bearing quote from the
    cited diff, which historical blocking findings would have
    survived?

Two simulated gates (NO rubric, parser, or schema change — this is a
measurement, not an implementation of ReviewResult v2):

  G1 "strict quote": a blocking finding survives only if the cited
     file exists in the diff AND at least one candidate quote
     extracted from its comment occurs (after Phase-08 normalization)
     in that file's patch text.

  G2 "contract-aware": G1, OR the (ii-a) file-local
     contract-contradiction path: the finding cites an in-diff file,
     contains contract-reference language, contains contradiction
     language, AND quotes text from the cited file's documentation
     region (comment/docstring lines of the patch) — i.e. it names
     the file's own contract and asserts the shown code defeats it.

Known, deliberate limits (methodology honesty):
  - v1 comments carry no evidence fields, so quotes are EXTRACTED
    heuristically (backtick spans, double-quoted spans, long
    code-shaped tokens). Comments often quote real code as CONTEXT
    while the harm lives in unquoted prose — so G1/G2 survival here
    is an UPPER BOUND on what a v2 model-emitted `evidence.quote`
    gate would allow (v2 requires the harm-bearing claim itself to
    carry the quote, and adds `harm: demonstrated|presumed`).
  - The line-in-hunk rule of the v2 design is REPORTED, not gated:
    v1 line fields are too noisy to make it signal-bearing here.
  - The simulation cannot adjudicate claim DIRECTION: a finding that
    quotes real code but misstates the contract (C12's KeyError
    family) survives any quote gate; that failure mode belongs to
    the oracle (contract clarity), not the boundary.
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import eval.run_corpus as rc  # noqa: E402

SOURCES = {
    "stage-a-low": "eval/evidence/stage-a-glm-profiles-2026-09-19/low/records.jsonl",
    "stage-a-high": "eval/evidence/stage-a-glm-profiles-2026-09-19/high/records.jsonl",
    "stage-a-max": "eval/evidence/stage-a-glm-profiles-2026-09-19/max/records.jsonl",
    "b1-low": "eval/evidence/stage-b1-glm-profiles-2026-09-20/low/records.jsonl",
    "b1-high": "eval/evidence/stage-b1-glm-profiles-2026-09-20/high/records.jsonl",
}

B1 = {"b1-low", "b1-high"}

# Simulation input validation: record sources must sum to the frozen
# 414 (324 Stage-A + 90 B1). Any other total fails loudly — this tool
# measures a frozen corpus, it does not define one.
EXPECTED_TOTAL = 414

BACKTICK_RE = re.compile(r"`([^`\n]{3,120})`")
DQUOTE_RE = re.compile(r'"([^"\n]{6,120})"')
# single-quoted spans, guarded against apostrophe-in-word matches
SQUOTE_RE = re.compile(r"(?<![A-Za-z0-9])'([^'\n]{6,120})'"
                       r"(?![A-Za-z0-9])")
CONTRACT_REF_RE = re.compile(
    r"docstring|comment|header|contract|documented|documentation|"
    r"promis|states?\b|claims?\b|says|stated|declares", re.I)
CONTRADICTION_RE = re.compile(
    r"contradic|instead of|but the code|actually|violat|narrower|"
    r"not what the|differs from|despite|mismatch|never\b|fails to",
    re.I)
# Exploratory third measurement (beyond the two required gates):
# HARM-ANCHOR variant — a quote only counts when it occurs in the
# same sentence as harm/presumption language. Labels the boundary's
# real separating power on v1 comments.
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.:;!?)\]])\s+|\n+")
HARM_SENTENCE_RE = re.compile(
    r"callers?|consumers?|downstream|attackers?|credential|secret|"
    r"registry|unreviewed|untrusted|privilege|silent|mask|fabricat|"
    r"mislead|defeat|vulnerab|unsafe|insecure|broken|exfiltrat|"
    r"(would|could|will|can|may)\s+(not|never|be\s|publish|run|fail|"
    r"pass|silently|never)", re.I)


def _norm(text):
    return rc._norm_needle_text(text or "")


def _patch_body(patch):
    """Patch text without diff headers/hunk markers; +/- stripped so
    added and removed lines are searchable content."""
    out = []
    for line in patch.splitlines():
        if line.startswith(("@@", "+++", "---")):
            continue
        if line.startswith(("+", "-")):
            line = line[1:]
        out.append(line)
    return _norm("\n".join(out))


def _doc_region(patch):
    """Normalized text of documentation-ish patch lines: comment and
    docstring content (the (ii-a) contract region)."""
    keep, in_doc = [], False
    for line in patch.splitlines():
        if line.startswith(("@@", "+++", "---")):
            continue
        body = line[1:] if line.startswith(("+", "-")) else line
        s = body.strip()
        if '"""' in s or "'''" in s:
            in_doc = not in_doc if s.count('"""') % 2 or s.count(
                "'''") % 2 else False
            keep.append(body)
            continue
        if in_doc or s.startswith("#"):
            keep.append(body)
    return _norm("\n".join(keep))


def _hunks(patch):
    """[(file_start, file_end)] new-side ranges from hunk headers."""
    ranges = []
    for m in re.finditer(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", patch):
        start = int(m.group(1))
        length = int(m.group(2)) if m.group(2) is not None else 1
        ranges.append((start, start + max(length, 1) - 1))
    return ranges


def _quotes(comment):
    """Candidate quotes: EXPLICIT quoted spans only — backtick spans,
    double-quoted spans, guarded single-quoted spans. Bare identifiers
    are NOT quotes (v1 comments quote real diff text as context so
    indiscriminate token harvesting would make the gate vacuously
    satisfiable). Normalized; duplicates removed; order kept; each
    quote records whether it is harm-anchored (co-occurs with
    harm/presumption language in its sentence)."""
    cands = []
    for rx in (BACKTICK_RE, DQUOTE_RE, SQUOTE_RE):
        for m in rx.finditer(comment):
            cands.append(m.group(1))
    sentences = [s for s in SENTENCE_SPLIT_RE.split(comment) if s]
    seen, out = set(), []
    for c in cands:
        n = _norm(c)
        if not n or n in seen:
            continue
        seen.add(n)
        harm_anchored = any(c in s and HARM_SENTENCE_RE.search(s)
                            for s in sentences)
        out.append({"quote": c, "normalized": n,
                    "harm_anchored": harm_anchored})
    return out


def simulate_finding(finding, fixture):
    files = {f["path"]: f["patch"]
             for f in fixture["input"]["files"]}
    cited = finding.get("file")
    line = finding.get("line")
    comment = finding.get("comment", "")
    file_in_diff = cited in files
    line_ok = None
    if file_in_diff and line is not None:
        line_ok = any(a <= int(line) <= b for a, b in _hunks(files[cited]))
    quotes = _quotes(comment) if file_in_diff else []
    body = _patch_body(files[cited]) if file_in_diff else ""
    doc = _doc_region(files[cited]) if file_in_diff else ""
    for q in quotes:
        q["in_cited_patch"] = q["normalized"] in body
        q["in_doc_region"] = q["normalized"] in doc
    g1 = file_in_diff and any(q["in_cited_patch"] for q in quotes)
    g1_harm = file_in_diff and any(
        q["in_cited_patch"] and q["harm_anchored"] for q in quotes)
    contract_ref = bool(CONTRACT_REF_RE.search(comment))
    contradiction = bool(CONTRADICTION_RE.search(comment))
    quotes_doc = any(q["in_doc_region"] for q in quotes)
    ii_a = bool(file_in_diff and contract_ref and contradiction
                and quotes_doc)
    if not file_in_diff:
        outcome = {g: "DOWNGRADE" for g in ("g1_strict_quote",
                                            "g1h_harm_anchored",
                                            "g2_contract_aware")}
        reason = "cited file not in diff"
    else:
        outcome = {
            "g1_strict_quote": "BLOCK_SURVIVES" if g1 else "DOWNGRADE",
            "g1h_harm_anchored": ("BLOCK_SURVIVES" if g1_harm
                                  else "DOWNGRADE"),
            "g2_contract_aware": ("BLOCK_SURVIVES" if (g1 or ii_a)
                                  else "DOWNGRADE")}
        reasons = []
        reasons.append("quote-in-patch: %s" %
                       ("yes" if g1 else "no"))
        reasons.append("harm-anchored quote: %s" %
                       ("yes" if g1_harm else "no"))
        if not g1:
            reasons.append("ii-a contract-contradiction: %s "
                           "(contract-ref=%s contradiction-lang=%s "
                           "doc-quote=%s)" %
                           ("yes" if ii_a else "no", contract_ref,
                            contradiction, quotes_doc))
        reason = "; ".join(reasons)
    return {
        "cited_file": cited, "cited_line": line,
        "file_in_diff": file_in_diff, "line_in_hunk": line_ok,
        "quotes": quotes,
        "g1_strict_quote": outcome["g1_strict_quote"],
        "g1h_harm_anchored": outcome["g1h_harm_anchored"],
        "g2_contract_aware": outcome["g2_contract_aware"],
        "reason": reason,
        "ii_a_contract_path": ii_a,
    }


def _classify(finding, fixture):
    """control_blocker | true_positive_detection |
    positive_extra_blocker (a blocking finding on a positive that
    matches no oracle alternative)."""
    if fixture["kind"] == "control":
        return "control_blocker"
    if rc.matches_any_alternative(fixture["expected"]["groups"],
                                  finding):
        return "true_positive_detection"
    return "positive_extra_blocker"


def replay(sources=None):
    fixtures = {f["id"]: f for f in
                rc.load_corpus(ROOT / "eval" / "fixtures")}
    report = {
        "oracle_version": rc.oracle_version(),
        "methodology": {
            "gates": ["g1_strict_quote", "g2_contract_aware"],
            "normalization": "eval.run_corpus._norm_needle_text "
                             "(Phase-08 matcher normalization)",
            "limits": "v1 comments have no evidence fields; quotes "
                      "are heuristic extractions, so survival is an "
                      "UPPER BOUND on a v2 model-emitted-quote gate; "
                      "line-in-hunk reported but not gated; claim "
                      "DIRECTION is not adjudicable by quote gates",
        },
        "sources": {},
    }
    total_findings = 0
    total_records = 0
    source_map = sources or SOURCES
    for name, rel in source_map.items():
        path = ROOT / rel
        if not path.exists():
            report["sources"][name] = {"missing": rel}
            continue
        rows = []
        records = [json.loads(l) for l in
                   path.read_text().splitlines() if l.strip()]
        total_records += len(records)
        for rec in records:
            fx = fixtures.get(rec["fixture"])
            if fx is None or rec.get("result") is None:
                continue
            for f in rec["result"].get("findings", []):
                if f.get("severity") != "blocking":
                    continue
                total_findings += 1
                sim = simulate_finding(f, fx)
                rows.append({
                    "source": name,
                    "fixture": rec["fixture"],
                    "kind": fx["kind"],
                    "role": _classify(f, fx),
                    "effort": name.split("-")[-1],
                    "run_index": rec["run_index"],
                    "original_severity": f.get("severity"),
                    **sim,
                })
        report["sources"][name] = {"blocking_findings": len(rows),
                                   "findings": rows}
    if sources is None and total_records != EXPECTED_TOTAL:
        raise SystemExit(
            "frozen corpus mismatch: expected %d records, found %d"
            % (EXPECTED_TOTAL, total_records))
    report["total_records"] = total_records
    report["total_blocking_findings"] = total_findings
    report["summary"] = summarize(report)
    return report


def summarize(report):
    """Survival tables: role x gate overall AND per source, plus the
    focused C3/C12/C13 vs M3/M12/M16 breakdown, plus how often the
    (ii-a) contract path fired."""
    def bucket(rows, gate):
        surv = [r for r in rows
                if r[gate] == "BLOCK_SURVIVES"]
        return {"total": len(rows), "survives": len(surv),
                "downgraded": len(rows) - len(surv)}

    agg = {}
    focus = {}
    per_source = {}
    ii_a_fired = 0
    for name, s in report["sources"].items():
        if "missing" in s:
            continue
        for r in s["findings"]:
            role = r["role"]
            agg.setdefault(role, []).append(r)
            per_source.setdefault(name, {}).setdefault(role, []).append(r)
            if r["fixture"] in ("C3", "C12", "C13", "M3", "M12",
                                "M16"):
                focus.setdefault(r["fixture"], []).append(r)
            ii_a_fired += int(r["ii_a_contract_path"])
    out = {"by_role": {}, "by_source": {}, "focus_fixtures": {},
           "ii_a_contract_path_fired": ii_a_fired,
           "ii_a_rescued_any_g1_downgrade": any(
               r["ii_a_contract_path"]
               and r["g1_strict_quote"] == "DOWNGRADE"
               for s in report["sources"].values()
               for r in s["findings"])}
    for role, rows in sorted(agg.items()):
        out["by_role"][role] = {
            "g1_strict_quote": bucket(rows, "g1_strict_quote"),
            "g1h_harm_anchored": bucket(rows, "g1h_harm_anchored"),
            "g2_contract_aware": bucket(rows, "g2_contract_aware"),
        }
    for name, roles in sorted(per_source.items()):
        out["by_source"][name] = {
            role: {"g1_strict_quote": bucket(rows, "g1_strict_quote"),
                   "g1h_harm_anchored": bucket(rows, "g1h_harm_anchored"),
                   "g2_contract_aware":
                       bucket(rows, "g2_contract_aware")}
            for role, rows in sorted(roles.items())}
    for fid, rows in sorted(focus.items()):
        out["focus_fixtures"][fid] = {
            "g1_strict_quote": bucket(rows, "g1_strict_quote"),
            "g1h_harm_anchored": bucket(rows, "g1h_harm_anchored"),
            "g2_contract_aware": bucket(rows, "g2_contract_aware"),
        }
    return out


def main():
    ap = argparse.ArgumentParser(
        description="blocking-evidence boundary simulation over "
                    "frozen Stage-A/B1 records (offline)")
    ap.add_argument("--out", default=str(
        ROOT / "eval/evidence/blocking-boundary-sim-2026-09-21"
               / "boundary-sim-report.json"))
    args = ap.parse_args()
    report = replay()
    n = report["total_blocking_findings"]
    print(f"blocking findings replayed: {n}")
    for role, b in report["summary"]["by_role"].items():
        print(f"{role}:")
        for gate, v in b.items():
            print(f"  {gate}: survives {v['survives']}/{v['total']} "
                  f"(downgraded {v['downgraded']})")
    print("focus fixtures:")
    for fid, b in report["summary"]["focus_fixtures"].items():
        print(f"  {fid}: g1 {b['g1_strict_quote']['survives']}/"
              f"{b['g1_strict_quote']['total']} | g1h "
              f"{b['g1h_harm_anchored']['survives']}/"
              f"{b['g1h_harm_anchored']['total']} | g2 "
              f"{b['g2_contract_aware']['survives']}/"
              f"{b['g2_contract_aware']['total']}")
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(f"report written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
