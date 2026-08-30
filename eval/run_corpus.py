#!/usr/bin/env python3
"""Eval harness — replays the fixture corpus through the engine.

Offline from GitHub, live to OpenRouter. Drives the SAME engine the
production transport uses (engine.run_review); the eval never scores
rendered Markdown and never invokes the GitHub renderer.

Pass policy (plan constraints, settled 2026-08-29):
- N runs per fixture (default 3, --n);
- POSITIVE fixture passes iff every expected finding is detected in
  >= ceil((N+1)/2) runs (default N=3 -> 2 of 3);
- CONTROL fixture passes iff zero blocking findings occur across ALL
  runs (zero tolerance for false blockers);
- additionally, UNEXPECTED BLOCKING findings fail any fixture,
  positive or control alike (an always-blocking reviewer must not
  pass the corpus). Advisory noise is counted and reported, not
  gated.

Classification is MEASURED, never assumed: the harness proposes
GATING (passes policy today) or KNOWN_GAP; the recorded state lives
in eval/states.json, updated by humans citing the report, never
silently by the harness. The exit code gates only fixtures already
recorded as GATING.

Report metadata = the eval profile: toolkit SHA, rubric hash, model,
generation parameters, corpus hash, N (per the plan: a stability
number without its profile is meaningless).
"""

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import engine  # noqa: E402

DEFAULT_MODEL = "anthropic/claude-haiku-4.5"
TEMPERATURE = 0.2
MAX_TOKENS = 2000


SEVERITIES = ("blocking", "non-blocking")
ASSESSMENTS = ("CLEAR", "ISSUES_FOUND")


def _validate_fixture(f, ids):
    assert f["id"] in ids
    pair = f["paired_with"]
    assert pair in ids, "{0} paired with unknown {1}".format(f["id"], pair)
    assert f["kind"] in ("positive", "control")
    exp = f["expected"]
    assert exp["assessment"] in ASSESSMENTS, \
        "{0}: expected.assessment must be CLEAR or ISSUES_FOUND "
    "({1!r})".format(f["id"], exp.get("assessment"))
    findings = exp["findings"]
    if f["kind"] == "positive":
        # a positive with no expected finding would be auto-detected
        # by the old `or [n]` hack — inverting the fixture (a miss
        # would look like a pass). Positives MUST encode the intended
        # defect(s); misses then measure as KNOWN_GAP.
        assert findings, "{0}: positive fixture needs >= 1 expected " \
            "finding".format(f["id"])
    else:
        assert findings == [], \
            "{0}: control must expect zero findings".format(f["id"])
        assert exp["assessment"] == "CLEAR", \
            "{0}: control must expect CLEAR".format(f["id"])
    for e in findings:
        assert e["severity"] in SEVERITIES, e
        has_all = bool(e.get("comment_all"))
        has_any = bool(e.get("comment_any"))
        assert has_all or has_any, \
            "{0}: matcher needs comment_all and/or comment_any".format(
                f["id"])
        for k in ("comment_all", "comment_any"):
            for needle in e.get(k, []):
                assert isinstance(needle, str) and needle.strip(), \
                    "{0}: empty matcher needle in {1}".format(f["id"], k)


def load_corpus(fixtures_dir):
    fixtures = []
    for path in sorted(fixtures_dir.glob("*.json")):
        fixtures.append(json.loads(path.read_text()))
    ids = [f["id"] for f in fixtures]
    assert len(ids) == len(set(ids)), "duplicate fixture ids"
    for f in fixtures:
        _validate_fixture(f, set(ids))
    return fixtures


def corpus_hash(fixtures):
    blob = "".join(json.dumps(f, sort_keys=True) for f in fixtures)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _review_input(fixture, model_id):
    return {
        "schema_version": 1,
        "title": fixture["input"]["title"],
        "body": fixture["input"]["body"],
        "files": fixture["input"]["files"],
        "policy": (ROOT / "rubric.md").read_text(),
        "model": {"id": model_id, "temperature": TEMPERATURE,
                  "max_tokens": MAX_TOKENS},
    }


def _finding_matches(expected_entry, finding):
    """A finding satisfies an expected entry when:

    - severity matches, AND
    - every comment_all needle appears in the comment
      (case-insensitive) — essential concepts, AND
    - at least one comment_any needle appears — alternative
      vocabulary, one is enough.

    Sparse, mechanism-level needles only: matchers test engineering
    understanding, not phrasing."""
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


def evaluate(fixture, results):
    """results: list of ReviewResult dicts (one per run)."""
    n = len(results)
    expected_assessment = fixture["expected"]["assessment"]
    expected = fixture["expected"]["findings"]
    threshold = (n + 2) // 2  # ceil((n+1)/2): N=3 -> 2

    per_expected = []
    for entry in expected:
        hits = sum(
            1 for r in results
            if any(_finding_matches(entry, f) for f in r.get("findings", [])))
        per_expected.append({"entry": entry, "hits": hits})
    detected_ok = all(p["hits"] >= threshold for p in per_expected)

    # expected assessment is ENFORCED, not just recorded: a control
    # answered INCONCLUSIVE on every run is a reviewer that cannot
    # review clean code — it must not pass the clean control.
    assessment_stability = {
        a: sum(1 for r in results if r["assessment"] == a)
        for a in ("CLEAR", "ISSUES_FOUND", "INCONCLUSIVE")}

    false_blockers = []
    noise = 0
    for idx, r in enumerate(results):
        for f in r.get("findings", []):
            expected_blocking = any(
                _finding_matches(e, f) for e in expected)
            if f.get("severity") == "blocking" and not expected_blocking:
                false_blockers.append(idx)
            elif f.get("severity") != "blocking" and not expected_blocking:
                noise += 1

    if fixture["kind"] == "positive":
        assessment_ok = assessment_stability[expected_assessment] >= threshold
        passes = detected_ok and assessment_ok and not false_blockers
    else:  # control: every run CLEAR, zero blocking findings
        passes = (assessment_stability["CLEAR"] == n
                  and not false_blockers)
    return {
        "id": fixture["id"], "kind": fixture["kind"], "runs": n,
        "assessments": [r["assessment"] for r in results],
        "assessment_stability": assessment_stability,
        "expected_detection": per_expected,
        "false_blockers": len(false_blockers),
        "advisory_noise": noise,
        "passes_policy": passes,
        "proposal": "GATING-capable" if passes else "KNOWN_GAP",
    }


def run_corpus(fixtures, model_id, n, run_once):
    results = []
    spend = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}
    for fixture in fixtures:
        runs = []
        for _ in range(n):
            r = run_once(fixture)
            runs.append(r)
            spend["calls"] += 1
            u = r.get("usage") or {}
            spend["prompt_tokens"] += u.get("prompt_tokens", 0)
            spend["completion_tokens"] += u.get("completion_tokens", 0)
        results.append(evaluate(fixture, runs))
    return results, spend


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fixtures", default=str(ROOT / "eval" / "fixtures"))
    ap.add_argument("--model", default=os.environ.get("AI_REVIEW_MODEL",
                                                      DEFAULT_MODEL))
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--only", help="comma-separated fixture ids")
    ap.add_argument("--out", help="write the full report JSON here")
    args = ap.parse_args(argv)

    fixtures = load_corpus(pathlib.Path(args.fixtures))
    if args.only:
        keep = {s.strip() for s in args.only.split(",")}
        fixtures = [f for f in fixtures if f["id"] in keep]

    def run_once(fixture):
        return engine.run_review(_review_input(fixture, args.model))

    print("corpus: {0} fixtures ({1} positive / {2} control), N={3}, "
          "model={4}".format(
              len(fixtures),
              sum(1 for f in fixtures if f["kind"] == "positive"),
              sum(1 for f in fixtures if f["kind"] == "control"),
              args.n, args.model), file=sys.stderr)

    per_fixture, spend = run_corpus(fixtures, args.model, args.n, run_once)

    states_path = ROOT / "eval" / "states.json"
    states = json.loads(states_path.read_text()) if states_path.exists() else {}

    gating_violations = [r["id"] for r in per_fixture
                         if states.get(r["id"]) == "GATING"
                         and not r["passes_policy"]]

    profile = {
        "toolkit_sha": os.popen("git -C {0} rev-parse HEAD"
                                .format(ROOT)).read().strip() or "unknown",
        "rubric_hash": hashlib.sha256(
            (ROOT / "rubric.md").read_bytes()).hexdigest()[:16],
        "corpus_hash": corpus_hash(fixtures),
        "model": args.model,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "n": args.n,
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    report = {"profile": profile, "per_fixture": per_fixture,
              "spend": spend,
              "gating_violations": gating_violations,
              "states_in_force": states}

    for r in per_fixture:
        print("{0:4s} {1:9s} detect={2} false-blockers={3} noise={4} "
              "-> {5}{6}".format(
                  r["id"], r["kind"],
                  ",".join(str(h["hits"]) for h in r["expected_detection"])
                  or "-",
                  r["false_blockers"], r["advisory_noise"],
                  r["proposal"],
                  "  [GATING VIOLATION]" if r["id"] in gating_violations
                  else ""))
    print("spend: {0} calls, {1} prompt tok, {2} completion tok".format(
        spend["calls"], spend["prompt_tokens"], spend["completion_tokens"]),
        file=sys.stderr)

    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
        print("report: {0}".format(args.out), file=sys.stderr)
    if gating_violations:
        print("GATING VIOLATIONS: {0}".format(", ".join(gating_violations)),
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
