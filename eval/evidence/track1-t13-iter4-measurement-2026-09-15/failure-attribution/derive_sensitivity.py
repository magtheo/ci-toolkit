"""Derive the run-level entry-detection matrix for the #64
floor-violation fixtures from committed frozen artifacts ONLY:

  - raw #62 pass-1 traces (raw/{haiku,sonnet}-trace.jsonl)
  - the fixture corpus (eval/fixtures/)
  - the #64 join + detection logic ((model_id, digest) join via
    engine._review_input_digest; per-run per-entry match via
    harness._finding_matches; run detects iff ALL entries detected —
    the Deviation-6 convention used by pass1_rescore.py)
  - the frozen #64 rescore (derived/pass1-rescore.json) supplies the
    affected-fixture list (floor violations per profile) and the
    retrospective detection counts the matrix must reproduce.

Zero model calls. No network. Works from a clean checkout.

Fail-closed: the derivation aborts unless the reconstructed matrix
reproduces the #64 retrospective detection counts exactly.

Outputs sensitivity-matrix.json (committed derived artifact). With
--check, verifies the committed file is byte-equal to the
reconstruction instead of writing it.

Usage: python3 derive_sensitivity.py [--check]
       (run from the repository root or anywhere; paths are resolved
       relative to this file)
"""

import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
RAW = HERE.parent.parent / "raw"
RESORE = HERE.parent.parent / "derived" / "pass1-rescore.json"
ROOT = HERE.parents[4]
for p in (str(ROOT), str(ROOT / "eval")):
    if p not in sys.path:
        sys.path.insert(0, p)

import run_corpus as harness  # noqa: E402
import engine as current_engine  # noqa: E402

PROFILES = {"haiku": "anthropic/claude-haiku-4.5",
            "sonnet": "anthropic/claude-sonnet-4.5"}
N_RUNS = 5


def fail(msg):
    sys.stderr.write("FAIL-CLOSED: {0}\n".format(msg))
    sys.exit(1)


def load_rescore():
    if not RESORE.exists():
        fail("frozen #64 rescore not found: {0}".format(RESORE))
    return json.loads(RESORE.read_text())


def load_traces():
    traces = {}
    for prof, model_id in PROFILES.items():
        path = RAW / "{0}-trace.jsonl".format(prof)
        if not path.exists():
            fail("frozen traces not found: {0}".format(path))
        records = [json.loads(l) for l in
                   path.read_text().splitlines() if l]
        for r in records:
            if r["model_id"] != model_id:
                fail("unexpected model_id {0!r} in {1}".format(
                    r["model_id"], path.name))
        traces[prof] = records
    return traces


def build_matrix():
    rescore = load_rescore()
    fixtures = harness.load_corpus(ROOT / "eval" / "fixtures")
    by_id = {fx["id"]: fx for fx in fixtures}

    # affected fixtures: exactly the #64 floor violations, per profile
    affected = {}
    for prof in PROFILES:
        viol = rescore["adjudication"]["profiles"][prof]["floor_violations"]
        affected[prof] = sorted(viol)
        if not affected[prof]:
            fail("{0}: no floor violations in frozen rescore; "
                 "matrix scope is empty".format(prof))

    # digest -> fixture (model-independent; same join as #64 join_proof)
    digest_by_id = {}
    for fx in fixtures:
        ri = harness._review_input(fx, "x")
        d = current_engine._review_input_digest(ri)
        if d in digest_by_id:
            fail("digest collision on {0}".format(fx["id"]))
        digest_by_id[fx["id"]] = d

    fixture_of = {}
    traces = load_traces()
    for prof, records in traces.items():
        groups = collections.defaultdict(list)
        for r in records:
            d = r["review_input_digest"]
            if d not in digest_by_id.values():
                fail("{0}: digest {1} joins to no fixture".format(
                    prof, d))
            fid = next(k for k, v in digest_by_id.items() if v == d)
            groups[fid].append(r)
        for fid, recs in groups.items():
            if len(recs) != N_RUNS:
                fail("{0}/{1}: expected N={2} runs, got {3}".format(
                    prof, fid, N_RUNS, len(recs)))
            fixture_of[(prof, fid)] = recs
        for fx in fixtures:
            if (prof, fx["id"]) not in fixture_of:
                fail("{0}: fixture {1} missing from traces".format(
                    prof, fx["id"]))

    matrix = {}
    for prof, fids in affected.items():
        for fid in fids:
            fx = by_id[fid]
            expected = [
                {"severity": e["severity"],
                 "comment_all": list(e.get("comment_all", [])),
                 "comment_any": list(e.get("comment_any", []))}
                for e in fx["expected"]["findings"]]
            if not expected:
                fail("{0}/{1}: no expected findings".format(prof, fid))
            recs = fixture_of[(prof, fid)]
            runs = []
            detected_runs = 0
            for i, r in enumerate(recs):
                res = r["pass1_review_result"]
                findings = res.get("findings", [])
                entries = []
                for ei, e in enumerate(fx["expected"]["findings"]):
                    det = any(harness._finding_matches(e, f)
                              for f in findings)
                    entries.append({"entry": ei, "detected": det})
                if all(e["detected"] for e in entries):
                    detected_runs += 1
                runs.append({
                    "run": i,
                    "assessment": res["assessment"],
                    "findings": [f.get("comment", "") for f in findings],
                    "entries": entries})
            # fail closed unless the matrix reproduces the #64
            # retrospective count for this fixture
            retro = rescore["adjudication"]["profiles"][
                prof]["floor_violations"][fid]["retrospective"]
            if detected_runs != retro:
                fail("{0}/{1}: reconstructed detection {2} != #64 "
                     "retrospective {3}".format(
                         prof, fid, detected_runs, retro))
            matrix["{0}/{1}".format(prof, fid)] = {
                "expected": expected, "runs": runs}

    n_runs = sum(len(v["runs"]) for v in matrix.values())
    if len(matrix) != 8 or n_runs != 8 * N_RUNS:
        fail("matrix scope {0} fixtures / {1} runs unexpected".format(
            len(matrix), n_runs))
    return matrix, affected


def canon(obj):
    return json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=False)


def main():
    check = "--check" in sys.argv[1:]
    matrix, _ = build_matrix()
    out = HERE.parent / "sensitivity-matrix.json"
    if check:
        if not out.exists():
            fail("committed matrix missing: {0}".format(out))
        if canon(matrix) + "\n" != out.read_text():
            fail("committed sensitivity-matrix.json does NOT "
                 "byte-reconstruct from frozen inputs")
        print("OK: committed matrix byte-reconstructs from frozen "
              "inputs ({0} fixtures)".format(len(matrix)))
    else:
        out.write_text(canon(matrix) + "\n")
        print("wrote {0} ({1} fixtures)".format(out, len(matrix)))


if __name__ == "__main__":
    main()
