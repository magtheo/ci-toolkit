"""Stage B1 execution-contract tests.

These derive the LIVE campaign contract from execute.sh itself (not
from preview.py): the exact fixture filter, the six-step frozen
schedule, the aggregate ceiling, and the authorization boundary.
They also cover the ledger's first-creation race and the B1-specific
reducer's frozen criteria.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True).stdout.strip())
EXECUTE_SH = REPO / "eval/evidence/stage-b1-glm-profiles-2026-09-20/execute.sh"
BASELINE = (REPO / "eval/evidence/stage-b1-prereg-2026-09-20"
            / "baseline-stage-a.json")

PREREGISTERED = ["C1", "C2", "C3", "C4", "C5", "C12", "C13", "C14",
                 "C16", "M2", "M3", "M4", "M12", "M13", "M16"]
FROZEN_ORDER = [("low", 0), ("high", 0), ("high", 1), ("low", 1),
                ("low", 2), ("high", 2)]


def _script():
    return EXECUTE_SH.read_text()


# ---- the LIVE script must encode the frozen matrix ------------------

def test_live_script_filters_to_preregistered_fixtures():
    text = _script()
    assert "--fixtures" in text, "live invocation must filter fixtures"
    m = re.search(r'FIXTURES="([^"]+)"', text)
    assert m, "fixture list constant not found"
    fixtures = m.group(1).split(",")
    assert fixtures == PREREGISTERED, (
        "live fixture set diverges from the preregistration")
    # every adapter invocation carries the filter
    invocations = re.findall(r"python3 eval/profile_qualification\.py(.*?)'",
                             text, re.S)
    assert invocations, "no adapter invocations found"
    for inv in invocations:
        assert '--fixtures "$FIXTURES"' in inv, inv


def test_live_script_schedule_is_the_frozen_order():
    text = _script()
    calls = [(e, int(i)) for e, i in
             re.findall(r"^run (\w+)\s+(\d)$", text, re.M)]
    assert calls == FROZEN_ORDER
    # N=3 everywhere and the aggregate ceiling is $1
    assert "--runs 3" in text
    assert "--spend-ceiling-usd 1" in text
    assert "--spend-ledger" in text


def test_live_script_authorization_boundary():
    text = _script()
    # the script must NOT grant the gate itself
    assert not re.search(r"export PM_QUALIFY_LIVE_AUTHORIZED", text), (
        "a script must never self-authorize live spend")
    # the gate must be required and must be exactly 1
    assert 'PM_QUALIFY_LIVE_AUTHORIZED:?PM_QUALIFY' in text
    assert '!= "1"' in text


# ---- ledger first-creation race -------------------------------------

WORKER_INIT = """
import sys
sys.path.insert(0, %r)
import json
from eval.spend_ledger import SpendLedger
from eval.profile_qualification import SpendGuard

path, seed = sys.argv[1], sys.argv[2]
guard = SpendGuard(1.0, 0.075, 0.25, {"C1": 4000})
led = SpendLedger(path, guard, seed_dirs=[seed])
r = led.reserve("C1", 100)              # first action after creation
amount = led.settle(r, {"prompt_tokens": 500,
                        "completion_tokens": 20,
                        "reasoning_tokens": 0})
open(sys.argv[3], "w").write(json.dumps(amount))
""" % str(REPO)


def test_concurrent_first_creation_never_loses_state(tmp_path):
    seed = tmp_path / "seed"
    seed.mkdir()
    rec = {"attempts": [{"usage": {"prompt_tokens": 777,
                                   "completion_tokens": 11,
                                   "reasoning_tokens": 0}}]}
    (seed / "records.jsonl").write_text(json.dumps(rec) + "\n")
    ledger = tmp_path / "race.json"
    outpaths = [tmp_path / ("out-%d" % i) for i in range(6)]
    procs = [subprocess.Popen(
        [sys.executable, "-c", WORKER_INIT, str(ledger), str(seed),
         str(op)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True) for i, op in enumerate(outpaths)]
    for p in procs:
        out, err = p.communicate(timeout=60)
        assert p.returncode == 0, err
    amounts = [json.loads(op.read_text()) for op in outpaths]
    led_state = json.loads(ledger.read_text())
    expected_seed = (777 * 0.075 + 11 * 0.25) / 1e6
    # the seed survived the creation race exactly once
    assert led_state["settled_in_tokens"] == 777 + 6 * 500
    assert led_state["settled_out_tokens"] == 11 + 6 * 20
    assert led_state["reservations"] == []
    assert abs(sum(amounts)
               - (sum(amounts) + expected_seed)
               + expected_seed) >= 0        # sanity no-op
    settled_usd = led_state and None
    guard = __import__("eval.profile_qualification",
                       fromlist=["SpendGuard"]).SpendGuard(
        1.0, 0.075, 0.25, {"C1": 4000})
    computed = guard.cost_usd_of(led_state["settled_in_tokens"],
                                 led_state["settled_out_tokens"])
    assert computed == pytest.approx(expected_seed + sum(amounts),
                                     abs=1e-9)


# ---- the B1 reducer --------------------------------------------------

def _rec(fid, run_index, result):
    return {"fixture": fid, "run_index": run_index,
            "terminal_state": "OK_CONTENT", "result": result,
            "attempts": [], "http_retries": 0,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0,
                      "reasoning_tokens": 0},
            "wall_s": 1.0}


def _clear(fid):
    return {"schema_version": 1, "assessment": "CLEAR", "summary": "",
            "findings": [], "good": []}


def _block(fid, comment):
    return {"schema_version": 1, "assessment": "ISSUES_FOUND",
            "summary": "", "good": [],
            "findings": [{"file": "x", "line": 1,
                          "severity": "blocking", "comment": comment,
                          "suggestion": None}]}


def _detect_result(fid):
    """ISSUES_FOUND whose comments satisfy every expected group of
    the fixture (comment_all words + one comment_any word per group),
    blocking severity — the maximal-detection reviewer response."""
    import eval.run_corpus as rc
    matches = [f for f in __import__("eval.profile_qualification",
                                     fromlist=["corpus"]).corpus()
               if f["id"] == fid]
    assert matches, fid
    groups = matches[0]["expected"]["groups"]
    comments = []
    for g in groups:
        alt = g["alternatives"][0]
        words = list(alt.get("comment_all", []))
        any_words = alt.get("comment_any", [])
        if any_words:
            words.append(any_words[0])
        comments.append(" ".join(words) or "blocking defect")
    comment = " | ".join("%d: %s" % (i, c)
                         for i, c in enumerate(comments))
    return _block(fid, comment)


def _records_all_clear(fixture_ids, runs=3):
    return [_rec(fid, ri, _clear(fid))
            for fid in sorted(fixture_ids) for ri in range(runs)]


def _records_at_baseline(fixture_ids, runs=3):
    """Controls CLEAR, positives fully detecting — the no-regression
    reference scenario."""
    import eval.profile_qualification as pq
    kinds = {f["id"]: f["kind"] for f in pq.corpus()}
    out = []
    for fid in sorted(fixture_ids):
        result = (_detect_result(fid) if kinds[fid] == "positive"
                  else _clear(fid))
        out.extend(_rec(fid, ri, result) for ri in range(runs))
    return out


def test_b1_report_completeness_is_subset_aware(tmp_path):
    from eval.stage_b1_report import b1_report
    base = json.loads(BASELINE.read_text())["baseline"]["low"]
    # only 2 of 3 runs for one fixture: INCOMPLETE vs the 15x3 matrix
    records = _records_all_clear(PREREGISTERED)
    records = [r for r in records
               if not (r["fixture"] == "C1" and r["run_index"] == 2)]
    rep = b1_report(records, base, PREREGISTERED)
    assert rep["completeness"]["complete"] is False
    assert rep["completeness"]["expected_reviews"] == 45
    assert rep["completeness"]["missing"][0]["fixture"] == "C1"
    assert rep["verdict"] == "B1 FAIL"
    # and a FULL subset run is complete even though the corpus has 36
    rep = b1_report(_records_at_baseline(PREREGISTERED), base,
                    PREREGISTERED)
    assert rep["completeness"]["complete"] is True
    assert rep["verdict"] == "B1 PASS"


def test_b1_report_zero_control_blocker_gate(tmp_path):
    from eval.stage_b1_report import b1_report
    base = json.loads(BASELINE.read_text())["baseline"]["low"]
    records = _records_at_baseline(PREREGISTERED)
    for r in records:
        if r["fixture"] == "C3":
            r["result"] = _block("C3", "invented problem")
    rep = b1_report(records, base, PREREGISTERED)
    assert rep["controls"]["zero_control_blockers"] is False
    assert rep["controls"]["violations"][0]["id"] == "C3"
    assert rep["verdict"] == "B1 FAIL"
    assert any("control blockers" in f for f in rep["gating_failures"])


def test_b1_report_detection_regression_gate(tmp_path):
    from eval.stage_b1_report import b1_report
    base = json.loads(BASELINE.read_text())["baseline"]["low"]
    records = _records_at_baseline(PREREGISTERED)
    for r in records:
        if r["fixture"] == "M12":     # baseline is [3]: must detect 3/3
            r["result"] = _clear("M12")
    rep = b1_report(records, base, PREREGISTERED)
    entry = rep["detection"]["per_positive"]["M12"]
    assert entry["groups_detected"] == [0] and entry["baseline"] == [3]
    assert entry["no_regression"] is False
    assert rep["verdict"] == "B1 FAIL"
    assert "detection regression: ['M12']" in rep["gating_failures"]


def test_b1_report_m4_m13_reported_separately_not_gated(tmp_path):
    from eval.stage_b1_report import b1_report
    base = json.loads(BASELINE.read_text())["baseline"]["low"]
    records = _records_at_baseline(PREREGISTERED)
    for r in records:
        if r["fixture"] in ("M4", "M13"):   # missed: zero-baseline pair
            r["result"] = _clear(r["fixture"])
    rep = b1_report(records, base, PREREGISTERED)
    # M4/M13 missed everywhere (CLEAR positives) yet the verdict is a
    # PASS: their baseline is zero, they are reported standalone
    assert rep["verdict"] == "B1 PASS"
    for fid in ("M4", "M13"):
        assert fid not in rep["detection"]["per_positive"]
        entry = rep["separate_reporting"][fid]
        assert entry["zero_baseline"] is True
        assert entry["groups_detected"] == [0]
        assert "not gateable" in entry["note"]


def test_b1_report_m13_detection_gain_reported(tmp_path):
    from eval.stage_b1_report import b1_report
    base = json.loads(BASELINE.read_text())["baseline"]["low"]
    records = _records_at_baseline(PREREGISTERED)
    for r in records:
        if r["fixture"] == "M13":
            r["result"] = _detect_result("M13")
    rep = b1_report(records, base, PREREGISTERED)
    entry = rep["separate_reporting"]["M13"]
    assert entry["groups_detected"][0] == 3      # improvement, reported
    assert rep["verdict"] == "B1 PASS"           # and never gated


def test_b1_report_viability_gates(tmp_path):
    from eval.stage_b1_report import b1_report
    base = json.loads(BASELINE.read_text())["baseline"]["low"]
    records = _records_at_baseline(PREREGISTERED)
    bad = dict(_rec("C1", 0, _clear("C1")))
    bad["terminal_state"] = "TRANSPORT_FAILURE"
    bad["result"] = None
    records.append(bad)
    rep = b1_report(records, base, PREREGISTERED)
    assert rep["viability"]["no_transport_failure"] is False
    assert rep["verdict"] == "B1 FAIL"
    assert "viability" in rep["gating_failures"]


# ---- the combined campaign verdict (aggregate denominators) ---------

def _inconclusive(fid, run_index):
    import eval.profile_qualification as pq
    rec = _rec(fid, run_index, pq._inconclusive_result())
    return rec


def test_campaign_verdict_uses_aggregate_inconclusive_denominator():
    from eval.stage_b1_report import b1_report, combine_campaign
    base_low = json.loads(BASELINE.read_text())["baseline"]["low"]
    base_high = json.loads(BASELINE.read_text())["baseline"]["high"]
    # low: 5 of 45 INCONCLUSIVE (11.1% — fails the LOCAL view);
    # high: 0. Aggregate: 5/90 = 5.6% <= 10% -> campaign viable.
    records_low = _records_at_baseline(PREREGISTERED)
    inconclusive = 0
    for r in records_low:
        if r["fixture"].startswith("C") and inconclusive < 5:
            r["result"] = {"schema_version": 1,
                           "assessment": "INCONCLUSIVE", "summary": "",
                           "findings": [], "good": []}
            inconclusive += 1
    assert inconclusive == 5
    low = b1_report(records_low, base_low, PREREGISTERED)
    high = b1_report(_records_at_baseline(PREREGISTERED), base_high,
                     PREREGISTERED)
    # the low-effort LOCAL view flags the local rate — preserved
    assert low["viability"]["inconclusive_rate_ok"] is False
    assert low["verdict"] == "B1 FAIL"
    combined = combine_campaign(low, high)
    assert combined["viability"]["logical_reviews"] == 90
    assert combined["viability"]["final_inconclusive"] == 5
    assert combined["viability"]["inconclusive_rate_ok"] is True
    assert combined["verdict"] == "B1 PASS"
    assert combined["gating_failures"] == []
    assert "AGGREGATE" in combined["viability"]["scope_note"]


def test_campaign_verdict_fails_on_aggregate_breach():
    from eval.stage_b1_report import b1_report, combine_campaign
    base_low = json.loads(BASELINE.read_text())["baseline"]["low"]
    base_high = json.loads(BASELINE.read_text())["baseline"]["high"]
    # 5 INCONCLUSIVE per effort = 10/90 = 11.1% > 10%: aggregate FAIL
    records = {}
    for effort, base in (("low", base_low), ("high", base_high)):
        recs = _records_at_baseline(PREREGISTERED)
        n = 0
        for r in recs:
            if r["fixture"].startswith("C") and n < 5:
                r["result"] = {"schema_version": 1,
                               "assessment": "INCONCLUSIVE",
                               "summary": "", "findings": [],
                               "good": []}
                n += 1
        records[effort] = b1_report(recs, base, PREREGISTERED)
    combined = combine_campaign(records["low"], records["high"])
    assert combined["viability"]["final_inconclusive"] == 10
    assert combined["viability"]["inconclusive_rate_ok"] is False
    assert combined["verdict"] == "B1 FAIL"
    assert "viability (aggregate)" in combined["gating_failures"]


def test_campaign_verdict_preserves_per_effort_detection_detail():
    from eval.stage_b1_report import b1_report, combine_campaign
    base_low = json.loads(BASELINE.read_text())["baseline"]["low"]
    base_high = json.loads(BASELINE.read_text())["baseline"]["high"]
    low = b1_report(_records_at_baseline(PREREGISTERED), base_low,
                    PREREGISTERED)
    high = b1_report(_records_at_baseline(PREREGISTERED), base_high,
                     PREREGISTERED)
    combined = combine_campaign(low, high)
    assert combined["verdict"] == "B1 PASS"
    # M4/M13 remain standalone in the campaign verdict, both efforts
    for effort in ("low", "high"):
        for fid in ("M4", "M13"):
            entry = combined["separate_reporting"][effort][fid]
            assert entry["zero_baseline"] is True
        assert "M4" not in combined["detection"][effort]["per_positive"]


def test_campaign_verdict_conjoins_per_effort_fixture_gates():
    from eval.stage_b1_report import b1_report, combine_campaign
    base_low = json.loads(BASELINE.read_text())["baseline"]["low"]
    base_high = json.loads(BASELINE.read_text())["baseline"]["high"]
    low = b1_report(_records_at_baseline(PREREGISTERED), base_low,
                    PREREGISTERED)
    recs_high = _records_at_baseline(PREREGISTERED)
    for r in recs_high:
        if r["fixture"] == "C2":
            r["result"] = _block("C2", "speculation")
    high = b1_report(recs_high, base_high, PREREGISTERED)
    combined = combine_campaign(low, high)
    assert combined["verdict"] == "B1 FAIL"
    assert "high: control blockers: ['C2']" in combined["gating_failures"]

def test_campaign_combine_cli_accepts_only_combine_flags(tmp_path):
    """Exercise the exact post-campaign CLI, not only combine_campaign()."""
    from eval.stage_b1_report import b1_report
    baseline = json.loads(BASELINE.read_text())["baseline"]
    low = b1_report(_records_at_baseline(PREREGISTERED),
                    baseline["low"], PREREGISTERED)
    high = b1_report(_records_at_baseline(PREREGISTERED),
                     baseline["high"], PREREGISTERED)
    low_path, high_path = tmp_path / "low.json", tmp_path / "high.json"
    low_path.write_text(json.dumps(low))
    high_path.write_text(json.dumps(high))
    result = subprocess.run(
        [sys.executable, str(REPO / "eval/stage_b1_report.py"),
         "--combine-low", str(low_path),
         "--combine-high", str(high_path)],
        capture_output=True, text=True, cwd=REPO)
    assert result.returncode == 0, result.stderr
    combined = json.loads(result.stdout)
    assert combined["verdict"] == "B1 PASS"
    assert combined["viability"]["logical_reviews"] == 90


def test_b1_per_effort_cli_still_requires_all_inputs():
    """Optional argparse flags must not weaken the per-effort contract."""
    result = subprocess.run(
        [sys.executable, str(REPO / "eval/stage_b1_report.py"),
         "--effort", "low"],
        capture_output=True, text=True, cwd=REPO)
    assert result.returncode != 0
    assert "per-effort report requires" in result.stderr
    assert "--records" in result.stderr
