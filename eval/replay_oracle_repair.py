"""Deterministic Phase-08 replay: old-vs-new matcher over FROZEN
records. Zero network, zero spend, no evidence mutation.

The legacy matcher below is a byte-faithful copy of the pre-Phase-08
_finding_matches (case-insensitive substring, no normalization), kept
here so both scorings run under the SAME process. The new scoring uses
eval.run_corpus's live implementation. Integrity check: legacy scoring
of the B1 records must reproduce the committed b1-report detection
counts — proving the legacy copy is faithful before any delta is
reported."""
import argparse
import json
import pathlib
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

# B1 committed detection (b1-report-*.json detection.per_positive).
# Scalar entries are single-group fixtures; M2 carries per-group hits.
B1_COMMITTED = {
    "b1-low": {"M12": 3, "M16": 2, "M2": [1, 3], "M3": 2},
    "b1-high": {"M12": 3, "M16": 3, "M2": [0, 3], "M3": 3},
}

# Needles ADDED by Phase-08 (documented in the repair PR). Legacy
# scoring = current corpus MINUS these additions + the legacy matcher,
# so the pre-Phase-08 scorer is reconstructed exactly (the integrity
# check below proves it against the committed B1 reports).
PHASE08_ADDED = {
    "M4": ["not part of the diff", "outside of the diff",
           "outside this diff", "not in the diff",
           "absent from the diff", "beyond the diff",
           "not shown in the diff", "cannot be verified from the diff"],
    "M16": ["discard", "discards", "fall through", "falls through",
            "reports success", "success summary",
            "pretends", "even when the request failed",
            "even when it failed", "unconditionally return"],
}


def _legacy_fixture(fx):
    """Fixture with pre-Phase-08 needle lists (Phase-08 additions
    removed)."""
    import copy
    out = copy.deepcopy(fx)
    added = PHASE08_ADDED.get(out["id"], [])
    for g in out["expected"].get("groups", []):
        for alt in g.get("alternatives", []):
            if added and alt.get("comment_any"):
                alt["comment_any"] = [n for n in alt["comment_any"]
                                      if n not in added]
    return out


def _legacy_finding_matches(expected_entry, finding):
    """EXACT pre-Phase-08 semantics (do not 'improve' this function):
    lowercase substring containment, no normalization."""
    if finding.get("severity") != expected_entry["severity"]:
        return False
    comment = finding.get("comment", "").lower()
    for needle in expected_entry.get("comment_all", []):
        if needle.lower() not in comment:
            return False
    any_of = expected_entry.get("comment_any")
    if any_of and not any(n.lower() in comment for n in any_of):
        return False
    return True


def _legacy_group_detected(group, result):
    return any(_legacy_finding_matches(alt, f)
               for alt in group["alternatives"]
               for f in result.get("findings", []))


def _legacy_run_detect(groups, result):
    if not groups:
        return False
    return all(_legacy_group_detected(g, result) for g in groups)


def _run_detect(groups, result, matcher):
    return matcher(groups, result)


def replay(sources=None):
    fixtures = {f["id"]: f for f in
                rc.load_corpus(ROOT / "eval" / "fixtures")}
    legacy_fixtures = {fid: _legacy_fixture(fx)
                       for fid, fx in fixtures.items()}
    report = {"oracle_version": rc.oracle_version(),
              "note": "deterministic offline replay over FROZEN "
                      "records; legacy scoring = pre-Phase-08 matcher "
                      "+ pre-Phase-08 needles (Phase-08 additions "
                      "removed); controls are severity-scored and "
                      "matcher-independent by construction",
              "sources": {}}
    for name, rel in (sources or SOURCES).items():
        path = ROOT / rel
        if not path.exists():
            report["sources"][name] = {"missing": rel}
            continue
        records = [json.loads(l) for l in
                   path.read_text().splitlines() if l.strip()]
        per_fixture = {}
        group_hits = {}
        flips = []
        control_blockers = 0
        for r in records:
            fid = r["fixture"]
            fx = fixtures.get(fid)
            if fx is None or r.get("result") is None:
                continue
            if fx["kind"] == "control":
                control_blockers += sum(
                    1 for f in r["result"].get("findings", [])
                    if f.get("severity") == "blocking")
                continue
            groups = fx["expected"]["groups"]
            legacy_groups = legacy_fixtures[fid]["expected"]["groups"]
            old = _run_detect(legacy_groups, r["result"],
                              _legacy_run_detect)
            new = _run_detect(groups, r["result"],
                              rc.run_detects_all_groups)
            entry = per_fixture.setdefault(
                fid, {"old": 0, "new": 0, "runs": 0})
            entry["runs"] += 1
            entry["old"] += int(old)
            entry["new"] += int(new)
            if old != new:
                flips.append({"fixture": fid,
                              "run_index": r["run_index"],
                              "legacy": old, "phase08": new})
            for gi, g in enumerate(legacy_groups):
                hits = group_hits.setdefault(fid, [0] * len(groups))
                hits[gi] += int(_legacy_group_detected(g, r["result"]))
        integrity = None
        if name in B1_COMMITTED:
            integrity = {}
            for fid, want in B1_COMMITTED[name].items():
                want_list = want if isinstance(want, list) else [want]
                got = group_hits.get(fid, [])
                integrity[fid] = {"committed": want_list,
                                  "legacy_replay": got,
                                  "match": got == want_list}
        report["sources"][name] = {
            "records": len(records),
            "control_blocking_findings": control_blockers,
            "per_positive_fixture": per_fixture,
            "per_positive_group_hits_legacy": group_hits,
            "detection_flips_legacy_to_phase08": flips,
            "legacy_integrity_vs_committed_b1_report": integrity,
        }
    return report


def main():
    ap = argparse.ArgumentParser(
        description="old-vs-new matcher replay over frozen records")
    ap.add_argument("--out", default=str(
        ROOT / "eval/evidence/matcher-repair-replay-2026-09-21"
               / "replay-report.json"))
    args = ap.parse_args()
    report = replay()
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    total = 0
    for name, s in report["sources"].items():
        if "missing" in s:
            print(f"{name}: MISSING {s['missing']}")
            continue
        flips = s["detection_flips_legacy_to_phase08"]
        total += len(flips)
        print(f"{name}: {s['records']} records | "
              f"control blockers (unchanged): "
              f"{s['control_blocking_findings']} | flips: {len(flips)}")
        for f in flips:
            print(f"   {f['fixture']} run{f['run_index']}: "
                  f"{f['legacy']} -> {f['phase08']}")
        if s.get("legacy_integrity_vs_committed_b1_report"):
            ok = all(v["match"] for v in
                     s["legacy_integrity_vs_committed_b1_report"]
                     .values())
            print(f"   legacy-copy integrity vs committed b1 report: "
                  f"{'OK' if ok else 'MISMATCH — DO NOT TRUST DELTAS'}")
    print(f"total run-level detection flips: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
