#!/usr/bin/env python3
"""Build the auditable per-finding classification for Stage B0.

Reads the frozen Stage-A records and assigns every blocking finding
emitted against a control fixture to exactly one attribution
category. Fails closed: if any blocking control finding is not
covered by the classification table, or if any table entry matches
nothing, the script exits non-zero. Zero model calls; pure
reprocessing of persisted evidence.
"""
import json
import sys
from pathlib import Path

EV = Path("eval/evidence/stage-a-glm-profiles-2026-09-19")

# (fixture, effort, run_index, line) -> (primary, tag)
# primary: invented | severity | rubric | pending-adjudication | correct-not-fp
TABLE = {
    # C2 — pwn-request speculation about the unseen callee
    ("C2", "low", 0, 4): ("invented", "callee-speculation"),
    ("C2", "low", 1, 4): ("invented", "callee-speculation"),
    ("C2", "low", 2, 4): ("invented", "callee-speculation"),
    ("C2", "high", 1, 3): ("invented", "callee-speculation"),
    ("C2", "max", 1, 3): ("invented", "callee-speculation"),
    # C3 — contract invented from the word "guard" in the title
    ("C3", "high", 0, 11): ("invented", "title-contract"),
    ("C3", "high", 1, 6): ("invented", "title-contract"),
    ("C3", "low", 0, 6): ("invented", "title-contract"),
    ("C3", "low", 1, 14): ("invented", "title-contract"),
    ("C3", "low", 2, 14): ("invented", "title-contract"),
    ("C3", "low", 2, 6): ("invented", "title-contract"),
    ("C3", "max", 1, 13): ("invented", "title-contract"),
    ("C3", "max", 2, 13): ("invented", "title-contract"),
    ("C3", "max", 0, 8): ("severity", "deployment-context"),
    ("C3", "max", 2, 8): ("severity", "deployment-context"),
    # C4 — scope-violation policing (rubric clause)
    ("C4", "high", 1, 8): ("rubric", "scope-violation-clause"),
    ("C4", "high", 2, 8): ("rubric", "scope-violation-clause"),
    ("C4", "max", 1, 8): ("rubric", "scope-violation-clause"),
    # C8 — lifecycle-claim vs already-set-course race
    ("C8", "high", 0, 19): ("invented", "beyond-diff-race"),
    ("C8", "high", 0, 19.1): ("rubric", "missing-tests-clause"),
    ("C8", "high", 1, 15): ("pending-adjudication", "framework-contract-listenManual"),
    ("C8", "low", 0, 15): ("pending-adjudication", "framework-contract-listenManual"),
    ("C8", "low", 1, 15): ("pending-adjudication", "framework-contract-listenManual"),
    ("C8", "low", 2, 17): ("pending-adjudication", "framework-contract-listenManual"),
    # C10 — missing tests only
    ("C10", "high", 0, 4): ("rubric", "missing-tests-clause"),
    ("C10", "max", 1, 7): ("rubric", "missing-tests-clause"),
    ("C10", "max", 2, 7): ("rubric", "missing-tests-clause"),
    # C11 — model factually right, oracle wrong (verified: Prisma CLI ref)
    ("C11", "high", 2, 7): ("correct-not-fp", "oracle-defect-invalid-flag"),
    ("C11", "max", 1, 7): ("correct-not-fp", "oracle-defect-invalid-flag"),
    # C12 — dead-except speculation / KeyError type polish / tests
    ("C12", "low", 0, 31): ("invented", "session-protocol-speculation"),
    ("C12", "low", 0, 32): ("severity", "exception-type-polish"),
    ("C12", "low", 2, 33): ("severity", "exception-type-polish"),
    ("C12", "high", 0, 33): ("severity", "exception-type-polish"),
    ("C12", "high", 0, 23): ("rubric", "missing-tests-clause"),
    ("C12", "high", 1, 32): ("invented", "session-protocol-speculation"),
    ("C12", "high", 1, 33): ("severity", "exception-type-polish"),
    ("C12", "high", 1, 23): ("rubric", "missing-tests-clause"),
    ("C12", "max", 0, 33): ("severity", "exception-type-polish"),
    ("C12", "max", 0, 23): ("rubric", "missing-tests-clause"),
    ("C12", "max", 1, 33): ("rubric", "missing-tests-clause"),
    ("C12", "max", 2, 33): ("invented", "session-protocol-speculation"),
    # C13 — trigger-vs-title mismatch, real observation, blocking escalation
    ("C13", "low", 0, 4): ("severity", "trigger-title-mismatch"),
    ("C13", "low", 1, 3): ("severity", "trigger-title-mismatch"),
    ("C13", "low", 2, 3): ("severity", "trigger-title-mismatch"),
    ("C13", "high", 0, 3): ("severity", "trigger-title-mismatch"),
    ("C13", "high", 1, 3): ("severity", "trigger-title-mismatch"),
    ("C13", "high", 2, 4): ("severity", "trigger-title-mismatch"),
    ("C13", "max", 0, 3): ("severity", "trigger-title-mismatch"),
    ("C13", "max", 1, 3): ("severity", "trigger-title-mismatch"),
    ("C13", "max", 2, 3): ("severity", "trigger-title-mismatch"),
    # C15 — missing tests only
    ("C15", "max", 0, 1): ("rubric", "missing-tests-clause"),
    ("C15", "max", 1, 0): ("rubric", "missing-tests-clause"),
    # C16 — REST semantics invented / HTTP-status robustness / tests
    ("C16", "high", 1, 10): ("invented", "api-semantics-speculation"),
    ("C16", "low", 1, 9): ("invented", "api-semantics-speculation"),
    ("C16", "low", 2, 9): ("invented", "api-semantics-speculation"),
    ("C16", "max", 0, 10): ("severity", "http-status-robustness"),
    ("C16", "max", 1, 10): ("severity", "http-status-robustness"),
    ("C16", "max", 1, 7): ("rubric", "missing-tests-clause"),
}


def main():
    out = []
    seen = set()
    for effort in ("low", "high", "max"):
        for raw in (EV / effort / "records.jsonl").read_text().splitlines():
            r = json.loads(raw)
            if not r["fixture"].startswith("C"):
                continue
            if r["terminal_state"] != "OK_CONTENT":
                continue
            if r["result"]["assessment"] != "ISSUES_FOUND":
                continue
            for f in r["result"]["findings"]:
                if f["severity"] != "blocking":
                    continue
                key = (r["fixture"], effort, r["run_index"], f["line"])
                # disambiguate the two same-line findings in C8 high r0
                if key in seen and key == ("C8", "high", 0, 19):
                    key = ("C8", "high", 0, 19.1)
                if key not in TABLE:
                    sys.exit("unclassified blocking finding: %s" % (key,))
                primary, tag = TABLE[key]
                seen.add(key)
                out.append({
                    "fixture": r["fixture"], "effort": effort,
                    "run_index": r["run_index"], "line": f["line"],
                    "primary": primary, "tag": tag,
                    "comment_excerpt": f["comment"][:160],
                })
    unmatched = set(TABLE) - seen
    if unmatched:
        sys.exit("table entries matching no finding: %s" % sorted(unmatched))
    counts = {}
    for row in out:
        counts[row["primary"]] = counts.get(row["primary"], 0) + 1
    dest = Path("eval/evidence/stage-b0-attribution-2026-09-19/classification.json")
    dest.write_text(json.dumps({
        "source": "stage-a-glm-profiles-2026-09-19 (frozen)",
        "total_blocking_findings_on_controls": len(out),
        "counts": counts,
        "findings": out,
    }, indent=1) + "\n")
    print("classified:", len(out), "| counts:", counts)


if __name__ == "__main__":
    main()
