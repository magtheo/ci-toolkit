#!/usr/bin/env python3
"""Failure-attribution audit — machine stage: population extraction.

ZERO model calls. This script derives the classification population
from frozen evidence only (#62 raw traces joined via the #64 rescore
mapping) and emits `population.jsonl`: one record per finding that
requires attribution, with full provenance. It performs NO
classification — attributions are human judgment recorded separately
in `classifications.jsonl` and validated by `build_summary.py`.

Fail-closed reconciliation before emitting anything:

  - control false blockers must total exactly 91 (haiku) / 139 (sonnet)
  - positive-side false blockers must reconcile to the #64 by-family
    totals
  - every record carries: profile, fixture id/kind/family, run index,
    (model_id, review_input_digest), finding index, raw finding text,
    plus the effective model-facing input identity for the fixture

Usage: python3 derive_population.py   (from repository root)
"""

import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
for p in (str(ROOT), str(ROOT / "eval")):
    if p not in sys.path:
        sys.path.insert(0, p)

import run_corpus as harness  # noqa: E402
import engine  # noqa: E402

RAW = HERE.parent / "raw"
PROFILES = {"haiku": "anthropic/claude-haiku-4.5",
            "sonnet": "anthropic/claude-sonnet-4.5"}

# #64 expected values (fail-closed reconciliation targets)
EXPECTED_CONTROL_FB = {"haiku": 91, "sonnet": 139}
EXPECTED_POS_BY_FAMILY = {
    "haiku": {"risk-boilerplate": 15, "speculative-consequence": 12,
              "severity-inflation": 3, "hallucinated-fact": 2,
              "unattributed": 1},
    "sonnet": {"risk-boilerplate": 21, "speculative-consequence": 12,
               "severity-inflation": 17, "hallucinated-fact": 8,
               "unattributed": 10},
}


def fail(msg):
    sys.stderr.write("FAIL-CLOSED: {0}\n".format(msg))
    sys.exit(1)


def main():
    fixtures = {f["id"]: f for f in
                harness.load_corpus(ROOT / "eval" / "fixtures")}

    traces = {}
    for prof, model in PROFILES.items():
        recs = [json.loads(l) for l in
                (RAW / "{0}-trace.jsonl".format(prof))
                .read_text().splitlines() if l]
        traces[prof] = recs

    # rebuild the #64 join: (model_id, digest) -> fixture
    digest_of = {}
    for fid, fx in fixtures.items():
        ri = harness._review_input(fx, "x")
        digest_of[engine._review_input_digest(ri)] = fid

    records = []
    ctrl_totals = collections.Counter()
    pos_fam = {p: collections.Counter() for p in PROFILES}
    for prof, recs in traces.items():
        # group runs per fixture preserving trace order = run order
        runs = collections.defaultdict(list)
        for idx, r in enumerate(recs):
            d = r["review_input_digest"]
            if d not in digest_of:
                fail("digest {0} joins to no fixture".format(d))
            if r["model_id"] != PROFILES[prof]:
                fail("model_id mismatch in {0}".format(prof))
            runs[digest_of[d]].append((idx, r))
        for fid, runlist in runs.items():
            fx = fixtures[fid]
            family = fx.get("family", "unattributed")
            for run_no, (idx, r) in enumerate(runlist):
                p1 = r["pass1_review_result"]
                for fi, f in enumerate(p1.get("findings", [])):
                    if f.get("severity") != "blocking":
                        continue
                    expected_blocking = any(
                        harness._finding_matches(e, f)
                        for e in fx["expected"]["findings"])
                    if expected_blocking:
                        continue  # true positive, not in scope
                    rec = {
                        "record_id": "{0}/{1}/r{2}/f{3}".format(
                            prof, fid, run_no, fi),
                        "layer": ("control" if fx["kind"] == "control"
                                  else "positive"),
                        "profile": prof,
                        "fixture": fid,
                        "family": family,
                        "run": run_no,
                        "trace_record_index": idx,
                        "model_id": r["model_id"],
                        "review_input_digest": d,
                        "finding_index": fi,
                        "finding": f,
                    }
                    records.append(rec)
                    if fx["kind"] == "control":
                        ctrl_totals[prof] += 1
                    else:
                        pos_fam[prof][family] += 1

    for prof in PROFILES:
        if ctrl_totals[prof] != EXPECTED_CONTROL_FB[prof]:
            fail("{0} control FBs {1} != expected {2}".format(
                prof, ctrl_totals[prof], EXPECTED_CONTROL_FB[prof]))
        got = {k: v for k, v in pos_fam[prof].items()}
        if got != EXPECTED_POS_BY_FAMILY[prof]:
            fail("{0} positive by-family {1} != expected {2}".format(
                prof, got, EXPECTED_POS_BY_FAMILY[prof]))

    out = HERE / "population.jsonl"
    with out.open("w") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    proof = {
        "reconciliation": {
            "control_false_blockers": dict(ctrl_totals),
            "expected": EXPECTED_CONTROL_FB,
            "positive_by_family": {p: dict(v) for p, v in pos_fam.items()},
            "expected_positive_by_family": EXPECTED_POS_BY_FAMILY,
            "status": "totals reconcile exactly to #64"},
        "population_size": len(records),
        "by_profile_layer": {
            "{0}/{1}".format(p, l): sum(
                1 for r in records
                if r["profile"] == p and r["layer"] == l)
            for p in PROFILES for l in ("control", "positive")},
    }
    (HERE / "population-proof.json").write_text(
        json.dumps(proof, indent=1) + "\n")
    print("wrote {0} ({1} records)".format(out, len(records)))
    print(json.dumps(proof["by_profile_layer"], indent=1))


if __name__ == "__main__":
    main()
