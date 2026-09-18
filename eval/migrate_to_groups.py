#!/usr/bin/env python3
"""Deterministic migration: expected.findings[] -> expected.groups[].

Implements the approved #67 cardinality mapping EXPLICITLY — no
inference, no heuristics. Fails closed if any fixture deviates.

Approved mapping (plans/oracle-group-semantics-design.md, rev 3):

    18 controls          -> groups: []                (0 groups)
    M2                   -> 2 groups x 1 alternative  (entries AND)
    M3/M11/M12/M16       -> 1 group  x 2 alternatives (entries OR:
                            repair-4/5 phrasing-family extensions of
                            ONE defect — the audit's OR intent)
    remaining 13 positive-> 1 group  x 1 alternative

Needles (severity / comment_all / comment_any) are preserved exactly;
only structure changes. Run modes:

    migrate_to_groups.py            # migrate fixtures in place
    migrate_to_groups.py --check    # verify migrated state, no writes
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "eval" / "fixtures"

# Approved cardinality table: fixture id -> (n_groups, n_alternatives).
# Every positive must appear; controls are implied ([]).
APPROVED = {
    "M2": (2, 1),
    "M3": (1, 2), "M11": (1, 2), "M12": (1, 2), "M16": (1, 2),
}


def approved_shape(fixture_id, kind, n_findings):
    """Return the approved groups structure, or raise on deviation."""
    if kind == "control":
        if n_findings != 0:
            raise SystemExit("%s: control has %d findings, expected 0"
                             % (fixture_id, n_findings))
        return []
    if fixture_id in APPROVED:
        n_groups, n_alts = APPROVED[fixture_id]
        if n_findings != n_groups * n_alts:
            raise SystemExit(
                "%s: %d findings, approved cardinality %dx%d"
                % (fixture_id, n_findings, n_groups, n_alts))
        entries = list(range(n_findings))
        if n_groups == 2:              # M2: AND — one entry per group
            return [[e] for e in entries]
        return [entries]               # M3/M11/M12/M16: OR — shared group
    if n_findings != 1:
        raise SystemExit(
            "%s: positive outside the approved table must have exactly "
            "1 finding, has %d" % (fixture_id, n_findings))
    return [[0]]


def migrate(check_only=False):
    totals = {"controls": 0, "M2": 0, "family": 0, "single": 0}
    for path in sorted(FIXTURES.glob("*.json")):
        doc = json.loads(path.read_text())
        exp = doc["expected"]
        if "groups" in exp:
            if "findings" in exp:
                raise SystemExit("%s: mixed schema (findings+groups)"
                                 % path.name)
            shape = [[alts for alts in g] for g in exp["groups"]]
            kind = doc["kind"]
        else:
            if "findings" not in exp:
                raise SystemExit("%s: neither findings nor groups"
                                 % path.name)
            kind = doc["kind"]
            shape = approved_shape(doc["id"], kind,
                                   len(exp["findings"]))
            if check_only:
                raise SystemExit("%s: not migrated (old schema)"
                                 % path.name)
            new_exp = {k: v for k, v in exp.items() if k != "findings"}
            new_exp["groups"] = [
                [exp["findings"][i] for i in group] for group in shape]
            doc["expected"] = new_exp
            path.write_text(json.dumps(doc, indent=2) + "\n")
        # record shape class for the cardinality report
        if kind == "control":
            assert shape == []
            totals["controls"] += 1
        elif doc["id"] == "M2":
            totals["M2"] += 1
        elif doc["id"] in APPROVED:
            totals["family"] += 1
        else:
            totals["single"] += 1
        n_groups = len(shape)
        n_alts = {len(g) for g in shape} or {0}
        assert len(n_alts) == 1, "%s: ragged groups" % path.name
        print("%-8s %-8s %dx%d" % (path.stem, kind, n_groups,
                                   n_alts.copy().pop()))
    assert totals == {"controls": 18, "M2": 1, "family": 4, "single": 13}, \
        "cardinality mismatch: %s" % totals
    print("cardinality OK: 18 controls -> [], M2 -> 2x1, "
          "M3/M11/M12/M16 -> 1x2, 13 positives -> 1x1 (36 fixtures)")
    return totals


if __name__ == "__main__":
    migrate(check_only="--check" in sys.argv)
