"""Oracle-validity replay — zero-call comparator for expected-entry
semantics (diagnostic ONLY; authoritative oracle untouched).

Question: for fixtures whose repair work added expected.findings[]
entries as ALTERNATIVE PHRASINGS of one underlying defect (M3, M11,
M12, M16 — see ORACLE-VALIDITY.md), how much of the measured
sensitivity loss is an artifact of the harness's all-entries (AND)
interpretation?

Candidate semantics scored:

  S0 (current)  : a run detects iff ALL expected entries match —
                  every entry independently required (run-level
                  Deviation-6 convention; fixture-level analogue of
                  harness.evaluate()).
  S1 (intended) : a run detects iff ANY expected entry matches —
                  entries are alternative acceptable descriptions of
                  one semantic defect.

Replayed populations (frozen, committed, zero model calls):

  #36  eval/evidence/track1-baseline3-2026-09-07/{haiku,sonnet}-n5.json
      (the Deviation-6 floor source run; subject 4b07246)
  #62  eval/evidence/track1-t13-iter4-measurement-2026-09-15/raw/
      {haiku,sonnet}-trace.jsonl (pass-1 records; joined via
      (model_id, digest) exactly as pass1_rescore.py did)

Built-in fail-closed validity: before any candidate-semantics number
is produced, (a) the S0/AND recomputation of #62 must reproduce #64's
retrospective headline (36/90 and 47/90 — computed by
pass1_rescore.py under the all-entries convention), and (b) exactly
one of the two candidate semantics must reproduce the frozen
normative floors (repair-4 witness-replay.json
per_positive_detections, aggregates 51/90 and 66/90) from the #36 raw
reports — ambiguity between them aborts. NOTE: the opening revision
of this docstring assumed S0 would be that semantics; the parity
check DISCOVERED instead that the frozen floors equal the S1/OR
rescore (the repairs' original entries were byte-preserved, so the
added alternative entries can only add matches). The implementation
always discovered the truth; only this prose had to catch up.

Usage: python3 semantic_replay.py   (writes oracle-validity-replay.json)
"""

import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[3]
for p in (str(ROOT), str(ROOT / "eval")):
    if p not in sys.path:
        sys.path.insert(0, p)

import run_corpus as harness  # noqa: E402
import engine as current_engine  # noqa: E402

EVID = ROOT / "eval" / "evidence"
BASE36 = EVID / "track1-baseline3-2026-09-07"
ITER4 = EVID / "track1-t13-iter4-measurement-2026-09-15"
FLOORS = (EVID / "track1-oracle-repair4-2026-09-07" / "witness-replay.json")
PROFILES = {"haiku": "anthropic/claude-haiku-4.5",
            "sonnet": "anthropic/claude-sonnet-4.5"}
N_RUNS = 5


def fail(msg):
    sys.stderr.write("FAIL-CLOSED: {0}\n".format(msg))
    sys.exit(1)


def load_fixtures():
    fxs = harness.load_corpus(ROOT / "eval" / "fixtures")
    pos = [fx for fx in fxs if fx["kind"] == "positive" and
           fx["expected"]["findings"]]
    if len(pos) != 18:
        fail("expected 18 positives with required findings, got {0}"
             .format(len(pos)))
    return {fx["id"]: fx for fx in fxs}, pos


def load_36():
    out = {}
    for prof in PROFILES:
        n5 = json.loads((BASE36 / "{0}-n5.json".format(prof))
                        .read_text())
        by_id = {}
        for fx in n5["per_fixture"]:
            runs = []
            for r in fx["runs_detail"]:
                runs.append({"assessment": r["assessment"],
                             "findings": r.get("findings", [])})
            if len(runs) != N_RUNS:
                fail("#36 {0}/{1}: {2} runs".format(prof, fx["id"],
                                                    len(runs)))
            by_id[fx["id"]] = runs
        out[prof] = by_id
    return out


def load_62(fixtures_by_id):
    digest_by_id = {}
    for fid, fx in fixtures_by_id.items():
        ri = harness._review_input(fx, "x")
        digest_by_id[fid] = current_engine._review_input_digest(ri)
    if len(set(digest_by_id.values())) != len(digest_by_id):
        fail("digest collision across fixtures")
    digest_lookup = {v: k for k, v in digest_by_id.items()}
    out = {}
    for prof, model_id in PROFILES.items():
        path = ITER4 / "raw" / "{0}-trace.jsonl".format(prof)
        records = [json.loads(l) for l in
                   path.read_text().splitlines() if l]
        groups = collections.defaultdict(list)
        for r in records:
            if r["model_id"] != model_id:
                fail("unexpected model_id in {0}".format(path.name))
            fid = digest_lookup.get(r["review_input_digest"])
            if fid is None:
                fail("{0}: digest joins to no fixture".format(prof))
            groups[fid].append(r["pass1_review_result"])
        if len(groups) != len(fixtures_by_id):
            fail("{0}: joined {1} fixtures".format(prof, len(groups)))
        by_id = {}
        for fid, results in groups.items():
            if len(results) != N_RUNS:
                fail("{0}/{1}: {2} runs".format(prof, fid,
                                                len(results)))
            by_id[fid] = results
        out[prof] = by_id
    return out


def entry_matrix(fx, results):
    """per run: list of per-entry match booleans (harness matcher)."""
    expected = fx["expected"]["findings"]
    return [[any(harness._finding_matches(e, f)
                 for f in r.get("findings", []))
             for e in expected] for r in results]


def score(entry_rows, semantics):
    """run-level detections under S0 (all) / S1 (any)."""
    if semantics == "S0":
        return sum(1 for row in entry_rows if all(row))
    return sum(1 for row in entry_rows if any(row))


def fixture_level(entry_rows, threshold, semantics):
    """harness.evaluate() analogue: per-entry majority, then
    all-entries (S0) / any-entry (S1)."""
    n_entries = len(entry_rows[0])
    hits = [sum(1 for row in entry_rows if row[i])
            for i in range(n_entries)]
    ok = [h >= threshold for h in hits]
    return all(ok) if semantics == "S0" else any(ok)


def main():
    fixtures_by_id, positives = load_fixtures()
    pop36 = load_36()
    pop62 = load_62(fixtures_by_id)
    threshold = (N_RUNS + 2) // 2

    out = {
        "_meta": {
            "kind": "DIAGNOSTIC oracle-validity replay; zero model "
                    "calls; authoritative oracle untouched; #64 not "
                    "rewritten",
            "question": "how much of the measured sensitivity loss "
                        "is oracle entry-semantics representation vs "
                        "reviewer behavior",
            "S0": "run detects iff ALL expected entries match "
                  "(current harness + Deviation-6 convention)",
            "S1": "run detects iff ANY expected entry matches "
                  "(entries as alternative phrasings of one defect)",
            "populations": {
                "36": str(BASE36.relative_to(ROOT)),
                "62": str((ITER4 / "raw").relative_to(ROOT)),
                "floors": str(FLOORS.relative_to(ROOT))},
        },
        "parity": {},
        "per_fixture": {},
        "aggregates": {},
    }

    # ---------- 1. parity: which semantics do the frozen numbers use? ----------
    floors_doc = json.loads(FLOORS.read_text())
    normative = floors_doc["replay"]["per_positive_detections"]
    agg = {"36": {}, "62": {}}
    for src, pop in (("36", pop36), ("62", pop62)):
        for prof in PROFILES:
            per = {"S0": {}, "S1": {}}
            for fx in positives:
                rows = entry_matrix(fx, pop[prof][fx["id"]])
                per["S0"][fx["id"]] = score(rows, "S0")
                per["S1"][fx["id"]] = score(rows, "S1")
            agg[src][prof] = {
                "S0": sum(per["S0"].values()),
                "S1": sum(per["S1"].values()),
                "per_fixture": per}
    # the normative floors were frozen from #36 — which convention
    # reproduces them exactly, per-positive?
    matches = {}
    for sem in ("S0", "S1"):
        matches[sem] = all(
            agg["36"][prof]["per_fixture"][sem][fx["id"]] ==
            normative[prof][fx["id"]]
            for prof in PROFILES for fx in positives)
    if matches["S0"] == matches["S1"]:
        fail("normative floors are ambiguous between semantics: "
             "S0={0} S1={1}".format(matches["S0"], matches["S1"]))
    floor_sem = "S0" if matches["S0"] else "S1"
    if agg["36"]["haiku"][floor_sem] != 51 or \
       agg["36"]["sonnet"][floor_sem] != 66:
        fail("#36 {0} aggregates {1}/{2} != frozen 51/66".format(
            floor_sem, agg["36"]["haiku"][floor_sem],
            agg["36"]["sonnet"][floor_sem]))
    # the #64 retrospective headline was computed with the run-level
    # all-entries convention (pass1_rescore.fixture_level_detection)
    retro_and = {"haiku": 36, "sonnet": 47}
    for prof in PROFILES:
        if agg["62"][prof]["S0"] != retro_and[prof]:
            fail("#62 S0 {0} != #64 retrospective {1}".format(
                agg["62"][prof]["S0"], retro_and[prof]))
    out["parity"] = {
        "normative_floors_semantics": floor_sem,
        "normative_floors_per_positive_reproduced": True,
        "floors_aggregate_reproduced": "51/90, 66/90",
        "62_S0_matches_64_retrospective": "36/90, 47/90 (AND "
                                          "convention, as computed "
                                          "by pass1_rescore)",
        "finding": "the frozen Deviation-6 floors equal the OR-semantics "
                   "rescore of #36 (original entries were byte-preserved "
                   "by the repairs, so every originally-counted run "
                   "still counts; added alternative entries can only "
                   "add matches) — while #64's retrospective applied "
                   "the stricter AND convention against those floors",
    }

    # ---------- 2. per-fixture S0 vs S1 ----------
    for prof in PROFILES:
        for fx in positives:
            fid = fx["id"]
            rows36 = entry_matrix(fx, pop36[prof][fid])
            rows62 = entry_matrix(fx, pop62[prof][fid])
            rec = {
                "n_entries": len(fx["expected"]["findings"]),
                "36": {"S0": score(rows36, "S0"),
                       "S1": score(rows36, "S1"),
                       "S0_fixture_level": fixture_level(
                           rows36, threshold, "S0"),
                       "S1_fixture_level": fixture_level(
                           rows36, threshold, "S1")},
                "62": {"S0": score(rows62, "S0"),
                       "S1": score(rows62, "S1"),
                       "S0_fixture_level": fixture_level(
                           rows62, threshold, "S0"),
                       "S1_fixture_level": fixture_level(
                           rows62, threshold, "S1")},
                "62_runs_entry_matches": rows62,
            }
            out["per_fixture"]["{0}/{1}".format(prof, fid)] = rec

    # ---------- 3. aggregates, floors, violations ----------
    for src in ("36", "62"):
        for prof in PROFILES:
            agg[src][prof]["S1"] = sum(
                v[src]["S1"] for k, v in out["per_fixture"].items()
                if k.startswith(prof + "/"))
    for prof in PROFILES:
        viol0, viol1 = [], []
        mixed = []
        for fx in positives:
            fid = fx["id"]
            f_norm = normative[prof][fid]      # = floors under floor_sem
            f0 = agg["36"][prof]["per_fixture"]["S0"][fid]
            f1 = agg["36"][prof]["per_fixture"]["S1"][fid]
            r0 = agg["62"][prof]["per_fixture"]["S0"][fid]
            r1 = agg["62"][prof]["per_fixture"]["S1"][fid]
            if r0 < f0:
                viol0.append("{0}: retrospective {1} < floor {2}"
                             .format(fid, r0, f0))
            if r1 < f1:
                viol1.append("{0}: retrospective {1} < floor {2}"
                             .format(fid, r1, f1))
            # #64's comparison as recorded: AND-retrospective vs
            # normative (=OR) floors — the convention mix
            if r0 < f_norm:
                mixed.append("{0}: AND-retrospective {1} < OR-floor {2}"
                             .format(fid, r0, f_norm))
        out["aggregates"][prof] = {
            "floors": {"S0": {fx["id"]: agg["36"][prof]["per_fixture"]["S0"][fx["id"]] for fx in positives},
                       "S1": {fx["id"]: agg["36"][prof]["per_fixture"]["S1"][fx["id"]] for fx in positives},
                       "normative_frozen": {fx["id"]: normative[prof][fx["id"]] for fx in positives},
                       "normative_equals": floor_sem,
                       "aggregate": {"S0": agg["36"][prof]["S0"],
                                     "S1": agg["36"][prof]["S1"]}},
            "retrospective": {"aggregate": {"S0": agg["62"][prof]["S0"],
                                            "S1": agg["62"][prof]["S1"]}},
            "violations_same_convention_AND": viol0,
            "violations_same_convention_OR": viol1,
            "violations_as_recorded_in_64_mixed": mixed,
            "headline": {
                "36": "{0}/90 (AND) vs {1}/90 (OR)".format(
                    agg["36"][prof]["S0"], agg["36"][prof]["S1"]),
                "62": "{0}/90 (AND) vs {1}/90 (OR)".format(
                    agg["62"][prof]["S0"], agg["62"][prof]["S1"])},
        }

    path = HERE.parent / "oracle-validity-replay.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("wrote {0}".format(path))
    print("normative floors semantics:", floor_sem)
    for prof in PROFILES:
        a = out["aggregates"][prof]
        print("{0}: floors AND {1}/90 | OR {2}/90 | retrospective AND "
              "{3}/90 | OR {4}/90 | violations AND {5} OR {6} | "
              "as-recorded-in-#64 {7}".format(
                  prof,
                  a["floors"]["aggregate"]["S0"],
                  a["floors"]["aggregate"]["S1"],
                  a["retrospective"]["aggregate"]["S0"],
                  a["retrospective"]["aggregate"]["S1"],
                  len(a["violations_same_convention_AND"]),
                  len(a["violations_same_convention_OR"]),
                  len(a["violations_as_recorded_in_64_mixed"])))


if __name__ == "__main__":
    main()
