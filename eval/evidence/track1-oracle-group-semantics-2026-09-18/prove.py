#!/usr/bin/env python3
"""25k acceptance bundle — zero-call mechanical proofs.

Proves the eleven acceptance items of the approved #67 design against
the NEW harness (semantic groups: AND-of-groups / OR-of-alternatives)
and the FROZEN evidence corpus. No model calls, no network, no writes
outside this directory. Any violation aborts with a non-zero exit —
acceptance conditions are never weakened to pass.

Usage: python3 prove.py          (from anywhere; paths are self-anchored)
"""

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EV = ROOT / "eval" / "evidence"
FIXTURES = ROOT / "eval" / "fixtures"

sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(EV / "track1-t13-iter4-measurement-2026-09-15" /
                       "derived"))
import run_corpus as rc  # noqa: E402
import pass1_rescore as p1r  # noqa: E402  (frozen, read-only reuse)

BASE = "a32258f214ad29e52fecabf9f57b560d0b265112"
ORACLE_PRE = "cb6870c5a4c635b2"
FROZEN_HASHES = {
    "eval/evidence/track1-oracle-repair4-2026-09-07/witness-replay.json":
        "a0c099df71809bbdc9b9389b202b27cea38f1a0f7a71628df1dc9962655f4dda",
    "eval/evidence/track1-baseline3-2026-09-07/haiku-n5.json":
        "f772f465210ac4999a940d936aa9d09ad5fac79cbe4a9ad8a4caa2b62ac9dc72",
    "eval/evidence/track1-baseline3-2026-09-07/sonnet-n5.json":
        "1e8ae9203cdb7fedd3474bd4b8a58ec18504d54ecece692e68b694c932f578a5",
}
PROFILES = ("haiku", "sonnet")

R = {}


def fail(item, msg):
    print("FAIL [%s] %s" % (item, msg))
    sys.exit(1)


def ok(item, **vals):
    R[item] = dict(status="PASS", **vals)
    print("PASS [%s] %s" % (item, "; ".join(
        "%s=%s" % (k, v) for k, v in vals.items())))


def jload(path):
    return json.loads(pathlib.Path(path).read_text())


def synth_comment(alt):
    """Minimal reviewer comment satisfying one alternative exactly."""
    parts = [n for n in alt.get("comment_all", [])]
    if alt.get("comment_any"):
        parts.append(alt["comment_any"][0])
    return " ".join(parts) or "defect"


def run(assessment, comments):
    return {"assessment": assessment,
            "findings": [{"severity": "blocking", "file": "x", "line": 1,
                          "comment": c, "suggestion": None}
                         for c in comments]}


fixtures = {f["id"]: f for f in rc.load_corpus(FIXTURES)}
assert len(fixtures) == 36

# ---- item 1: #36 floor parity under the NEW harness ----------------------
floors = jload(EV / "track1-oracle-repair4-2026-09-07" /
               "witness-replay.json")["replay"]["per_positive_detections"]
item1 = {}
for prof in PROFILES:
    rep = jload(EV / "track1-baseline3-2026-09-07" / f"{prof}-n5.json")
    counts = {}
    for pf in rep["per_fixture"]:
        if pf["kind"] != "positive":
            continue
        groups = fixtures[pf["id"]]["expected"]["groups"]
        counts[pf["id"]] = sum(
            1 for r in pf["runs_detail"]
            if rc.run_detects_all_groups(groups, r))
    assert len(counts) == 18
    floors_pos = {k: v for k, v in floors[prof].items()
                  if not k.startswith("C")}
    if counts != floors_pos:
        diff = {k: (counts[k], floors[prof][k]) for k in counts
                if counts[k] != floors[prof][k]}
        fail("1-floor-parity", f"{prof} per-positive mismatch {diff}")
    item1[prof] = {"per_positive": "18/18", "aggregate":
                   "%d/90" % sum(counts.values())}
    assert sum(counts.values()) == (51 if prof == "haiku" else 66)
ok("1-floor-parity-36", haiku=item1["haiku"]["aggregate"],
   sonnet=item1["sonnet"]["aggregate"],
   per_positive="18/18 both profiles")

# ---- item 2: M2 remains AND ----------------------------------------------
m2 = fixtures["M2"]["expected"]["groups"]
assert len(m2) == 2 and all(len(g) == 1 for g in m2)
alt0, alt1 = m2[0][0], m2[1][0]
c0, c1 = synth_comment(alt0), synth_comment(alt1)
only0 = [run("ISSUES_FOUND", [c0])] * 3
only1 = [run("ISSUES_FOUND", [c1])] * 3
both = [run("ISSUES_FOUND", [c0, c1])] * 3
r0 = rc.evaluate(fixtures["M2"], only0)
r1 = rc.evaluate(fixtures["M2"], only1)
rb = rc.evaluate(fixtures["M2"], both)
if r0["passes_policy"] or r1["passes_policy"] or not rb["passes_policy"]:
    fail("2-m2-and", "M2 no longer behaves as AND of two groups")
ok("2-m2-and", removal="either group alone -> KNOWN_GAP",
   both="detected")

# ---- item 3: alternatives are OR (M3/M11/M12/M16) ------------------------
acc = {}
for mid in ("M3", "M11", "M12", "M16"):
    groups = fixtures[mid]["expected"]["groups"]
    assert len(groups) == 1 and len(groups[0]) == 2
    hits = []
    for alt in groups[0]:
        runs = [run("ISSUES_FOUND", [synth_comment(alt)])] * 3
        res = rc.evaluate(fixtures[mid], runs)
        if not res["passes_policy"]:
            fail("3-alternatives-or", f"{mid}: alternative rejected")
        hits.append(res["expected_detection"][0]["hits"])
    acc[mid] = hits
ok("3-alternatives-or", **acc)

# ---- item 4: control semantics + no vacuous truth ------------------------
c1_runs_clear = [run("CLEAR", [])] * 3
if not rc.evaluate(fixtures["C1"], c1_runs_clear)["passes_policy"]:
    fail("4-controls", "clean control must pass")
blk = [run("ISSUES_FOUND", ["unrelated blocking claim"])] * 3
r = rc.evaluate(fixtures["C1"], blk)
if r["passes_policy"] or r["false_blockers"] != 3:
    fail("4-controls", "control blocker must remain a false blocker")

with tempfile.TemporaryDirectory() as td:
    d = pathlib.Path(td)

    def expect_reject(name, doc, match):
        (d / "X1.json").write_text(json.dumps(doc))
        try:
            rc.load_corpus(d)
        except AssertionError as e:
            if match not in str(e):
                fail("4-controls", f"{name}: wrong loader error: {e}")
            return
        fail("4-controls", f"{name}: loader accepted invalid fixture")
        d.joinpath("X1.json").unlink()

    bad_alt = [{"severity": "blocking", "comment_any": ["x"]}]
    expect_reject("groups-on-control",
                  {"id": "X1", "kind": "control", "paired_with": "X1",
                   "expected": {"assessment": "CLEAR", "groups": [bad_alt]}},
                  "groups ==")
    expect_reject("zero-groups-positive",
                  {"id": "X1", "kind": "positive", "paired_with": "X1",
                   "expected": {"assessment": "ISSUES_FOUND", "groups": []}},
                  ">= 1 required")
    expect_reject("old-schema",
                  {"id": "X1", "kind": "positive", "paired_with": "X1",
                   "expected": {"assessment": "ISSUES_FOUND",
                                "findings": bad_alt}},
                  "old expected.findings")
    expect_reject("mixed-schema",
                  {"id": "X1", "kind": "positive", "paired_with": "X1",
                   "expected": {"assessment": "ISSUES_FOUND",
                                "findings": [], "groups": [bad_alt]}},
                  "old expected.findings")
    expect_reject("empty-alternatives",
                  {"id": "X1", "kind": "positive", "paired_with": "X1",
                   "expected": {"assessment": "ISSUES_FOUND",
                                "groups": [[]]}},
                  "non-empty alternatives")

if rc.groups_reach_threshold([], 2) is not False \
   or rc.run_detects_all_groups([], run("CLEAR", [])) is not False:
    fail("4-controls", "empty groups must never positively detect")
ok("4-controls", clean="passes", blocker="false blocker",
   loader="5 rejections verified", vacuous="all([]) guarded")

# ---- items 5/6/8: #62 pass-1 replay through the NEW harness ---------------
traces = p1r.load_traces()
fixtures_list = rc.load_corpus(FIXTURES)
digest_of = {
    fx["id"]: p1r.current_engine._review_input_digest(
        rc._review_input(fx, "x"))
    for fx in fixtures_list}
by_digest = {v: k for k, v in digest_of.items()}
p1 = jload(EV / "track1-t13-iter4-measurement-2026-09-15" / "derived" /
           "pass1-rescore.json")
recomputed = {}
control_fb = {}
for prof in PROFILES:
    per_fx = {}
    for rec in traces[prof]:
        per_fx.setdefault(by_digest[rec["review_input_digest"]],
                          []).append(rec["pass1_review_result"])
    det, fb = {}, 0
    for fid, runs in per_fx.items():
        fx = fixtures[fid]
        if fx["kind"] == "positive":
            groups = fx["expected"]["groups"]
            det[fid] = sum(1 for r in runs
                           if rc.run_detects_all_groups(groups, r))
        else:
            res = rc.evaluate(fx, runs)
            fb += res["false_blockers"]
    recomputed[prof] = det
    control_fb[prof] = fb

tot = {p: sum(recomputed[p].values()) for p in PROFILES}
if tot != {"haiku": 51, "sonnet": 65}:
    fail("5-pass1-replay", f"totals {tot} != haiku 51/90 sonnet 65/90")
ok("5-pass1-replay", haiku="51/90", sonnet="65/90")

viol = {}
for prof in PROFILES:
    v = {fid: (recomputed[prof][fid], floors[prof][fid])
         for fid in recomputed[prof]
         if recomputed[prof][fid] < floors[prof][fid]}
    viol[prof] = v
if viol["haiku"] or viol["sonnet"] != {"M13": (0, 1)}:
    fail("6-residual", f"violations {viol}")
ok("6-residual", haiku="none", sonnet="M13 only (0 < 1)")

fa = jload(EV / "track1-t13-iter4-measurement-2026-09-15" /
           "failure-attribution" / "failure-attribution-summary.json")
rec = fa["reconciliation"]
if rec["control_false_blockers"] != {"haiku": 91, "sonnet": 139} \
   or rec["expected"] != {"haiku": 91, "sonnet": 139} \
   or rec["status"] != "RECONCILED":
    fail("8-fb-attribution", "frozen attribution totals unexpected")
if control_fb != {"haiku": 91, "sonnet": 139}:
    fail("8-fb-attribution",
         f"recomputed control FBs {control_fb} != 91/139")
ok("8-fb-attribution", haiku=91, sonnet=139,
   families="attribution totals unchanged (RECONCILED)",
   recomputed="via new harness: match")

# ---- item 7: #62 historical REVERT unchanged ------------------------------
ca = jload(EV / "track1-t13-iter4-measurement-2026-09-15" / "derived" /
           "campaign-analysis.json")
if ca["verdict"] != "REVERT":
    fail("7-revert", f"campaign verdict {ca['verdict']!r} != REVERT")
ok("7-revert", verdict="REVERT (unchanged, never rewritten)")

# ---- item 10: witness soundness -------------------------------------------
w35 = jload(EV / "track1-oracle-repair3-2026-09-06" /
            "m16-witnesses.json")["witnesses"]
groups16 = fixtures["M16"]["expected"]["groups"]
g = sum(1 for w in w35 if w["ruling"] == "genuine_expected_expression"
        and rc.matches_any_alternative(
            groups16, {"severity": "blocking", "comment": w["comment"]}))
n = sum(1 for w in w35 if w["ruling"] == "not_expected_expression"
        and not rc.matches_any_alternative(
            groups16, {"severity": "blocking", "comment": w["comment"]}))
if (g, n) != (16, 11):
    fail("10-witnesses", f"#35 16/11 -> {g}/{n}")

r4 = jload(EV / "track1-oracle-repair4-2026-09-07" / "witness-replay.json")
ev36 = EV / "track1-baseline3-2026-09-07"
raw36, code36 = {}, []
for prof in PROFILES:
    rep = jload(ev36 / f"{prof}-n5.json")
    for pf in rep["per_fixture"]:
        for i, rd in enumerate(pf["runs_detail"]):
            for j, f in enumerate(rd.get("findings", [])):
                if f.get("severity") == "blocking":
                    raw36[(prof, pf["id"], i, j)] = " ".join(
                        (f.get("comment") or "").split())
for line in (ev36 / "narrative-coding.jsonl").read_text().splitlines():
    code36.append(json.loads(line))
ee36 = {(c["profile"], c["fixture"], c["run"], c["finding"])
        for c in code36 if c["class"] == "expected-expression"}
gap36 = {(c["profile"], c["fixture"], c["run"], c["finding"])
         for c in code36 if c["class"] == "defect-expression-unmatched"}
fb36 = {(c["profile"], c["fixture"], c["run"], c["finding"])
        for c in code36 if c["class"] == "false-blocker"}
adj36 = {(w["profile"], w["fixture"], w["run"], w["finding"])
         for w in r4["genuine"]}
matched36 = {ptr for ptr, text in raw36.items()
             if rc.matches_any_alternative(
                 fixtures[ptr[1]]["expected"]["groups"],
                 {"severity": "blocking", "comment": text})}
if not (len(raw36) == 538 and matched36 == ee36 | gap36 | adj36
        and len(matched36) == 214 and len(gap36 | adj36) == 3
        and not (matched36 & fb36) and len(fb36) == 324):
    fail("10-witnesses", f"#36 counts broken: matched={len(matched36)}")

r5 = jload(EV / "track1-oracle-repair5-2026-09-08" / "witness-replay.json")
E40 = EV / "track1-t13-iter1-measurement-2026-09-08"
raw40, code40 = {}, []
for prof in PROFILES:
    rep = jload(E40 / f"{prof}-n5.json")
    for pf in rep["per_fixture"]:
        for i, rd in enumerate(pf["runs_detail"]):
            for j, f in enumerate(rd.get("findings", [])):
                if f.get("severity") == "blocking":
                    raw40[(prof, pf["id"], i, j)] = " ".join(
                        (f.get("comment") or "").split())
for line in (E40 / "narrative-coding.jsonl").read_text().splitlines():
    code40.append(json.loads(line))
ee40 = {(c["profile"], c["fixture"], c["run"], c["finding"])
        for c in code40 if c["class"] == "expected-expression"}
fb40 = {(c["profile"], c["fixture"], c["run"], c["finding"])
        for c in code40 if c["class"] == "false-blocker"}
adj40 = {(w["profile"], w["fixture"], w["run"], w["finding"])
         for w in r5["adjudicated_flips_on_#40"]}
matched40 = {ptr for ptr, text in raw40.items()
             if rc.matches_any_alternative(
                 fixtures[ptr[1]]["expected"]["groups"],
                 {"severity": "blocking", "comment": text})}
if not (len(raw40) == 469 and matched40 == ee40 | adj40
        and len(matched40) == 197 and len(fb40 - matched40) == 272
        and adj40 <= matched40):
    fail("10-witnesses", f"#40 counts broken: matched={len(matched40)}")
ok("10-witnesses", w35="16 genuine/11 rejected",
   w36="214 matched (211+3), 324/324 FBs rejected",
   w40="197 matched, 272/273 FBs rejected")

# ---- item 9: oracle_version moved, floor VALUES unchanged -----------------
new_oracle = rc.oracle_version()
if new_oracle == ORACLE_PRE:
    fail("9-oracle-version", "oracle_version did not move")
ok("9-oracle-version", old=ORACLE_PRE, new=new_oracle,
   floor_values="unchanged (frozen witness-replay.json, hash-pinned)")

# ---- item 11: frozen evidence immutability --------------------------------
for rel, want in FROZEN_HASHES.items():
    got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    if got != want:
        fail("11-immutability", f"{rel} changed")
changed = subprocess.run(
    ["git", "diff", "--name-only", BASE + "..HEAD"],
    cwd=ROOT, capture_output=True, text=True).stdout.split()
allowed = (["eval/run_corpus.py", "eval/migrate_to_groups.py"]
           + [p for p in changed if p.startswith("eval/fixtures/")]
           + [p for p in changed if p.startswith("tests/")]
           + [p for p in changed
              if p.startswith("eval/evidence/track1-oracle-group-"
                              "semantics-2026-09-18/")])
disallowed = [p for p in changed if p not in allowed]
if disallowed:
    fail("11-immutability", f"unexpected changes: {disallowed}")
ok("11-immutability", frozen_hashes="3/3 byte-identical",
   diff_scope="fixtures + harness + migration + tests + this bundle only")

# ---- report ----------------------------------------------------------------
R["oracle_version"] = {"old": ORACLE_PRE, "new": new_oracle}
R["base"] = BASE
out = HERE / "acceptance.json"
out.write_text(json.dumps(R, indent=2, sort_keys=True) + "\n")
print("\nALL 11 ACCEPTANCE ITEMS PASS ->", out)
