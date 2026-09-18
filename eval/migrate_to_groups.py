#!/usr/bin/env python3
"""Deterministic migration: expected.findings[] -> expected.groups[].alternatives[].

Implements the approved #67 cardinality mapping EXPLICITLY — no
inference, no heuristics. Fails closed if any fixture deviates.

Approved mapping (plans/oracle-group-semantics-design.md, rev 3):

    18 controls          -> groups: []                         (0 groups)
    M2                   -> 2 groups x 1 alternative           (entries AND)
    M3/M11/M12/M16       -> 1 group  x 2 alternatives          (entries OR:
                            repair-4/5 phrasing-family extensions of
                            ONE defect — the audit's OR intent)
    remaining 13 positive-> 1 group  x 1 alternative

Schema: a group is an OBJECT {"alternatives": [entry, ...]} — the
approved contract, not a bare list; leaves room for future group-level
metadata without another migration. Needles (severity / comment_all /
comment_any) are preserved exactly; only structure changes.

Modes:
    migrate_to_groups.py            # migrate fixtures in place
    migrate_to_groups.py --check    # verify migrated state, no writes;
                                    # enforces the EXACT approved layout
                                    # per fixture (not just totals)
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


def approved_layout(fixture_id, kind, n_findings):
    """Approved group layout as a list of index lists, or raise."""
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


def read_groups_object(exp, name):
    """Validate + extract the migrated object schema; fail closed."""
    groups = exp.get("groups")
    assert isinstance(groups, list), "%s: groups must be a list" % name
    out = []
    for gi, g in enumerate(groups):
        assert isinstance(g, dict), \
            "%s: group %d must be an object with 'alternatives'" % (name, gi)
        alts = g.get("alternatives")
        assert isinstance(alts, list) and alts, \
            "%s: group %d must carry a non-empty alternatives list" % (
                name, gi)
        out.append(alts)
    return out


def migrate(check_only=False):
    totals = {"controls": 0, "M2": 0, "family": 0, "single": 0}
    for path in sorted(FIXTURES.glob("*.json")):
        doc = json.loads(path.read_text())
        exp = doc["expected"]
        name = path.name
        if "groups" in exp:
            if "findings" in exp:
                raise SystemExit("%s: mixed schema (findings+groups)" % name)
            alts_per_group = read_groups_object(exp, name)
            kind = doc["kind"]
            if check_only:
                want = approved_layout(doc["id"], kind,
                                       sum(len(a) for a in alts_per_group))
                got_sizes = [len(a) for a in alts_per_group]
                want_sizes = [len(g) for g in want]
                if got_sizes != want_sizes:
                    raise SystemExit(
                        "%s: layout %s deviates from approved %s"
                        % (name, got_sizes, want_sizes))
            elif any(not isinstance(g, dict) for g in exp["groups"]):
                raise SystemExit(
                    "%s: non-object group (approved schema is "
                    "groups[].alternatives[])" % name)
        else:
            if "findings" not in exp:
                raise SystemExit("%s: neither findings nor groups" % name)
            kind = doc["kind"]
            shape = approved_layout(doc["id"], kind, len(exp["findings"]))
            if check_only:
                raise SystemExit("%s: not migrated (old schema)" % name)
            new_exp = {k: v for k, v in exp.items() if k != "findings"}
            new_exp["groups"] = [
                {"alternatives": [exp["findings"][i] for i in group]}
                for group in shape]
            doc["expected"] = new_exp
            path.write_text(json.dumps(doc, indent=2) + "\n")
            alts_per_group = [[exp["findings"][i] for i in group]
                              for group in shape]
        # record shape class for the cardinality report
        if kind == "control":
            assert alts_per_group == []
            totals["controls"] += 1
        elif doc["id"] == "M2":
            totals["M2"] += 1
        elif doc["id"] in APPROVED:
            totals["family"] += 1
        else:
            totals["single"] += 1
        sizes = [len(a) for a in alts_per_group]
        print("%-8s %-8s groups=%d alternatives=%s"
              % (path.stem, kind, len(sizes), sizes))
    assert totals == {"controls": 18, "M2": 1, "family": 4, "single": 13}, \
        "cardinality mismatch: %s" % totals
    print("cardinality OK: 18 controls -> [], M2 -> 2 groups x 1 alt, "
          "M3/M11/M12/M16 -> 1 group x 2 alts, 13 positives -> 1x1 "
          "(36 fixtures, groups[].alternatives[] object schema)")
    return totals


if __name__ == "__main__":
    migrate(check_only="--check" in sys.argv)
