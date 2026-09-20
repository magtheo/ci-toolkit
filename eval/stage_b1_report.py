"""Stage B1 campaign reducer — the frozen criteria of the approved
preregistration, applied to the 15-fixture matrix.

Deliberately NOT the Stage-A reducer: completeness is evaluated
against the B1 subset (not the 36-fixture corpus), the gating gates
are B1's own (zero control blockers, group-wise no-regression vs the
pinned Stage-A baseline, viability), and M4/M13 — whose baseline
detection is zero — are reported separately so a continued miss
cannot hide behind a pass.

No oracle semantics are reimplemented: per-fixture evaluation and
group counting go through eval.run_corpus's evaluate(), per_group_hits()
and run_detects_all_groups(), the same functions Stage A used.
"""

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import eval.profile_qualification as pq  # noqa: E402
import eval.run_corpus as rc  # noqa: E402

GATING_IN_MATRIX = ("C4", "C5")   # C7 is GATING but not in the B1 matrix
SEPARATE_REPORTING = ("M4", "M13")  # zero baseline detection — never gated


def b1_report(records, baseline_for_effort, fixture_ids, runs=3):
    fixtures = {f["id"]: f for f in pq.corpus() if f["id"] in fixture_ids}
    assert set(fixtures) == set(fixture_ids), "unknown fixture id"
    states = json.loads((ROOT / "eval" / "states.json").read_text())

    by_fixture = {}
    for r in records:
        if r.get("terminal_state") in (None, "TRANSPORT_FAILURE",
                                       "DRY_RUN"):
            continue
        by_fixture.setdefault(r["fixture"], {})[r["run_index"]] = \
            r["result"]

    missing = [{"fixture": fid, "present": sorted(by_fixture.get(fid, {}))}
               for fid in sorted(fixtures)
               if set(by_fixture.get(fid, {})) != set(range(runs))]
    complete = not missing

    per_fixture_eval = {}
    for fid in sorted(fixtures):
        results = [by_fixture[fid][i] for i in sorted(by_fixture.get(fid, {}))
                   if i in by_fixture.get(fid, {})]
        if results:
            per_fixture_eval[fid] = rc.evaluate(fixtures[fid], results)

    # Gate 1 — zero control blockers (subsumes GATING members C4/C5)
    control_blockers = [
        {"id": fid, "false_blockers": ev["false_blockers"],
         "assessments": ev["assessments"]}
        for fid, ev in sorted(per_fixture_eval.items())
        if fixtures[fid]["kind"] == "control" and ev["false_blockers"]]
    gating_regressions = [
        fid for fid in GATING_IN_MATRIX
        if fid in per_fixture_eval
        and states.get(fid) == "GATING"
        and not per_fixture_eval[fid]["passes_policy"]]

    # Gate 2 — group-wise detection no-regression vs the pinned
    # baseline; positives only
    detection, regressions = {}, []
    for fid in sorted(fixtures):
        if fixtures[fid]["kind"] != "positive":
            continue
        results = [by_fixture[fid][i] for i in sorted(by_fixture.get(fid, {}))
                   if i in by_fixture.get(fid, {})]
        groups = fixtures[fid]["expected"]["groups"]
        counts = rc.per_group_hits(groups, results) if results else []
        base = baseline_for_effort["per_group_detection"][fid]
        ok = all(c >= b for c, b in zip(counts, base))
        detection[fid] = {"groups_detected": counts, "baseline": base,
                          "no_regression": ok}
        if not ok:
            regressions.append(fid)

    # Gate 3 — viability
    transport = pq.reduce_records(records)
    logical = transport["logical_reviews"]
    viability = {
        "transport_failures": transport["transport_failures"],
        "final_inconclusive": transport["final_inconclusive"],
        "logical_reviews": logical,
        "inconclusive_rate_ok": (logical == 0
                                 or transport["final_inconclusive"]
                                 / logical <= 0.10),
        "no_transport_failure": transport["transport_failures"] == 0,
        "escalations": transport["escalations"],
        "post_escalation_exhaustions":
            transport["post_escalation_exhaustions"],
        "post_esc_ok": (
            transport["escalations"] == 0
            or transport["post_escalation_exhaustions"]
            / transport["escalations"] <= 0.05),
    }
    viability_ok = (viability["inconclusive_rate_ok"]
                    and viability["no_transport_failure"]
                    and viability["post_esc_ok"])

    # Separate reporting — M4/M13 (zero baseline: not gateable)
    separate = {
        fid: detection.pop(fid) for fid in SEPARATE_REPORTING
        if fid in detection}
    for fid, entry in separate.items():
        entry["zero_baseline"] = all(b == 0 for b in entry["baseline"])
        entry["note"] = ("zero baseline detection — reported "
                         "standalone; a pass here is not gateable and "
                         "a miss is a KNOWN_GAP, per preregistration")

    gating_failures = []
    if not complete:
        gating_failures.append("incomplete matrix")
    if control_blockers:
        gating_failures.append("control blockers: %s"
                               % [v["id"] for v in control_blockers])
    if gating_regressions:
        gating_failures.append("GATING regressions: %s"
                               % gating_regressions)
    if regressions:
        gating_failures.append("detection regression: %s" % regressions)
    if not viability_ok:
        gating_failures.append("viability")

    return {
        "matrix": {"fixtures": sorted(fixtures), "runs": runs},
        "completeness": {"complete": complete, "expected_reviews":
                         len(fixtures) * runs, "missing": missing},
        "controls": {"zero_control_blockers": not control_blockers,
                     "violations": control_blockers},
        "gating": {"members_in_matrix": list(GATING_IN_MATRIX),
                   "regressions": gating_regressions},
        "detection": {"per_positive": detection,
                      "regressions": regressions},
        "separate_reporting": separate,
        "viability": dict(viability, **{
            "scope_note": "per-effort view; the CAMPAIGN verdict uses "
                          "the frozen aggregate denominators (90 "
                          "reviews for INCONCLUSIVE, total escalations "
                          "for post-escalation exhaustion)"}),
        "informational": {
            "false_blockers_on_positives":
                sum(ev["false_blockers"] for fid, ev in
                    per_fixture_eval.items()
                    if fixtures[fid]["kind"] == "positive"),
            "assessment_stability": {
                k: sum(ev["assessment_stability"][k]
                       for ev in per_fixture_eval.values())
                for k in ("CLEAR", "ISSUES_FOUND", "INCONCLUSIVE")},
        },
        "verdict": "B1 PASS" if not gating_failures else "B1 FAIL",
        "gating_failures": gating_failures,
        "scope_note": "B1 PASS permits preparation of a separate B2 "
                      "preregistration only — never B2 execution or "
                      "spend",
    }


def combine_campaign(report_low, report_high):
    """Final B1 verdict over the WHOLE campaign.

    Per-fixture gates (completeness, control blockers, GATING,
    detection no-regression) are conjunctive across both efforts.
    Viability uses the frozen AGGREGATE denominators — 90 reviews for
    the INCONCLUSIVE rate, total escalations for post-escalation
    exhaustion — so an unevenly distributed failure cannot fail one
    effort's local view while the campaign as a whole is inside its
    preregistered bounds (and vice versa)."""
    viability = {}
    for k in ("logical_reviews", "final_inconclusive",
              "transport_failures", "escalations",
              "post_escalation_exhaustions"):
        viability[k] = (report_low["viability"][k]
                        + report_high["viability"][k])
    total = viability["logical_reviews"]
    viability["inconclusive_rate_ok"] = (
        total == 0 or viability["final_inconclusive"] / total <= 0.10)
    viability["no_transport_failure"] = \
        viability["transport_failures"] == 0
    viability["post_esc_ok"] = (
        viability["escalations"] == 0
        or viability["post_escalation_exhaustions"]
        / viability["escalations"] <= 0.05)
    viability["scope_note"] = ("AGGREGATE campaign denominators: %d "
                              "reviews, %d escalations"
                              % (total, viability["escalations"]))
    viability_ok = (viability["inconclusive_rate_ok"]
                    and viability["no_transport_failure"]
                    and viability["post_esc_ok"])

    failures = []
    for name, rep in (("low", report_low), ("high", report_high)):
        failures += ["%s: %s" % (name, f)
                     for f in rep.get("gating_failures", [])
                     if f != "viability"]
    if not viability_ok:
        failures.append("viability (aggregate)")

    verdict = "B1 PASS" if not failures else "B1 FAIL"
    return {
        "campaign": "stage-b1-glm-profiles-2026-09-20",
        "viability": viability,
        "per_effort_verdicts": {"low": report_low.get("verdict"),
                                "high": report_high.get("verdict")},
        "detection": {
            "low": report_low.get("detection", {}),
            "high": report_high.get("detection", {}),
        },
        "separate_reporting": {
            "low": report_low.get("separate_reporting", {}),
            "high": report_high.get("separate_reporting", {}),
        },
        "verdict": verdict,
        "gating_failures": failures,
        "scope_note": "B1 PASS permits preparation of a separate B2 "
                      "preregistration only — never B2 execution or "
                      "spend. M4/M13 are reported standalone (zero "
                      "baseline) and do not gate.",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--records")
    ap.add_argument("--baseline",
                    help="baseline-stage-a.json from the approved "
                         "preregistration package")
    ap.add_argument("--effort", choices=("low", "high"))
    ap.add_argument("--fixtures",
                    help="comma-separated B1 fixture ids")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--spend-summary", default=None,
                    help="summary.json whose spend.aggregate_ledger is "
                         "copied into the report")
    ap.add_argument("--combine-low", default=None,
                    help="b1-report-low.json — with --combine-high, "
                         "produces the aggregate CAMPAIGN verdict "
                         "instead of a per-effort report")
    ap.add_argument("--combine-high", default=None,
                    help="b1-report-high.json")
    args = ap.parse_args()

    if args.combine_low or args.combine_high:
        if not (args.combine_low and args.combine_high):
            raise SystemExit("--combine-low and --combine-high go "
                             "together")
        low = json.loads(pathlib.Path(args.combine_low).read_text())
        high = json.loads(pathlib.Path(args.combine_high).read_text())
        print(json.dumps(combine_campaign(low, high), indent=1))
        return

    required = ("records", "baseline", "effort", "fixtures")
    missing = ["--" + key for key in required
               if getattr(args, key) is None]
    if missing:
        ap.error("per-effort report requires " + ", ".join(missing))

    records = [json.loads(l) for l in
               pathlib.Path(args.records).read_text().splitlines()
               if l.strip()]
    baseline = json.loads(pathlib.Path(args.baseline).read_text())
    report = b1_report(records, baseline["baseline"][args.effort],
                       [x.strip() for x in args.fixtures.split(",")],
                       runs=args.runs)
    report["effort"] = args.effort
    if args.spend_summary:
        sp = json.loads(pathlib.Path(args.spend_summary).read_text())
        report["spend"] = sp.get("spend")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
