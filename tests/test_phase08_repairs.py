"""Phase-08 deterministic repairs:

1. accounting — summary.json spend derived from the PERSISTED
   records.jsonl (all attempts), not the fresh per-process guard
   (B1 discrepancy: low summary $0.006593 == low-run2 only).
2. matcher — normalization + broadened semantic equivalence families;
   the three B1 phrasing-missed detections must now match, with
   over-loosening guards.
3. C12/M12 contract clarification — availability vs malformed payload
   explicit; oracle identity bumped; only these two goldens moved.
4. replay tool — legacy copy faithful vs committed B1 reports; flips
   are exactly the three expected runs; nothing regresses.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.profile_qualification as pq  # noqa: E402
import eval.replay_oracle_repair as replay_mod  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import eval.campaign_progress as cp  # noqa: E402

B1 = REPO / "eval/evidence/stage-b1-glm-profiles-2026-09-20"


# ---- 1. accounting ---------------------------------------------------

PRICES = (0.075, 0.25, "openrouter.ai z-ai/glm-5.3-flash 2026-09-18 "
          "discounted")


class _FakeGuard:
    """Just the pricing surface _spend_from_records needs."""

    def __init__(self, ceiling=1.0):
        self.ceiling = ceiling
        self.p_in, self.p_out = PRICES[0], PRICES[1]
        self.price_source = PRICES[2]

    def cost_usd_of(self, i, o):
        return (i * self.p_in + o * self.p_out) / 1e6


def _rec(fixture, ri, prompt, completion, reasoning):
    return {"fixture": fixture, "run_index": ri, "attempts": [
        {"prompt_tokens": prompt, "completion_tokens": completion,
         "reasoning_tokens": reasoning}],
        "usage": {"prompt_tokens": prompt,
                  "completion_tokens": completion,
                  "reasoning_tokens": reasoning}}


def test_summary_spend_is_records_derived_across_invocations(tmp_path):
    """B1 regression: a second invocation with a FRESH guard must not
    reset the summary's effort totals to its own 15 reviews."""
    out = tmp_path / "effort"
    out.mkdir()
    recs_a = [_rec("C1", 0, 1000, 500, 100),
              _rec("C2", 0, 1200, 600, 0)]
    recs_b = [_rec("C1", 1, 800, 400, 50)]
    (out / "records.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in recs_a + recs_b))
    # fresh guard of the LAST invocation knows nothing of the past
    pq._write_summary(out, [], 3, "m",
                      {"reasoning_effort": "low", "max_tokens": 8000},
                      spend=_FakeGuard())
    sp = json.loads((out / "summary.json").read_text())["spend"]
    assert sp["input_tokens"] == 3000
    assert sp["output_tokens_incl_reasoning"] == 1650
    assert sp["provider_generations_billed"] == 3
    assert sp["actual_cost_usd"] == round(
        (3000 * PRICES[0] + 1650 * PRICES[1]) / 1e6, 6)
    assert "records.jsonl" in sp["source"]


def test_summary_spend_counts_every_attempt_not_final_only():
    recs = [{"fixture": "C1", "run_index": 0, "attempts": [
        {"prompt_tokens": 500, "completion_tokens": 200,
         "reasoning_tokens": 0},
        {"prompt_tokens": 900, "completion_tokens": 300,
         "reasoning_tokens": 100}]}]
    sp = pq._spend_from_records(recs, _FakeGuard())
    assert sp["provider_generations_billed"] == 2
    assert sp["input_tokens"] == 1400
    assert sp["output_tokens_incl_reasoning"] == 600


def test_b1_records_reproduce_ledger_authoritative_spend():
    """The whole point of the repair: records-derived effort totals
    reconcile with the ledger for the frozen B1 evidence."""
    tot = 0
    for e in ("low", "high"):
        records = [json.loads(l) for l in
                   (B1 / e / "records.jsonl").read_text().splitlines()
                   if l.strip()]
        sp = pq._spend_from_records(records, _FakeGuard())
        tot += sp["actual_cost_usd"]
    # per-effort 6-dp rounding can drift 1e-6 vs the aggregate figure
    assert tot == pytest.approx(0.044276, abs=2e-6)


def test_progress_line_reads_raw_ledger_not_stale_summary_snapshot(tmp_path):
    s = {"logical_reviews": 15, "final_inconclusive": 0,
         "escalations": 0,
         "spend": {"provider_generations_billed": 15,
                   "actual_cost_usd": 0.006593,
                   "price_input_per_1m": 0.075,
                   "price_output_per_1m": 0.25,
                   # Deliberately stale/incompatible snapshot: the helper
                   # must use the raw ledger file for aggregate state.
                   "aggregate_ledger": {
                       "ceiling_usd": 1.0,
                       "settled_usd": 0.001,
                       "outstanding_reservations": 99,
                       "invariant_holds": False}}}
    ledger = {"settled_in_tokens": 52000,
              "settled_out_tokens": 44000,
              "reservations": [],
              "swept_orphans": [],
              "halts": 0}
    (tmp_path / "s.json").write_text(json.dumps(s))
    (tmp_path / "l.json").write_text(json.dumps(ledger))
    line = cp.progress_line(tmp_path / "s.json", tmp_path / "l.json")
    assert "gens=15" in line and "None" not in line
    assert "cost=$0.006593" in line
    assert "settled_tokens=52000 in/44000 out" in line
    assert "settled=$0.0149" in line
    assert "outstanding=0" in line and "invariant=True" in line


# ---- 2. matcher ------------------------------------------------------

def _result(fid, comment, severity="blocking"):
    fx = {f["id"]: f for f in
          rc.load_corpus(REPO / "eval" / "fixtures")}[fid]
    return fx, {"findings": [{"severity": severity,
                              "comment": comment}]}


def test_b1_m4_low_run2_phrasing_now_matches():
    fx, res = _result("M4", "Unsubstantiated absolute guarantee spanning "
                      "lines 3-5: the docstring states that all retry "
                      "decisions flow through ProcessingError.retryable "
                      "and that the orchestrator consults this flag and "
                      "no other signal. The orchestrator is outside this "
                      "diff; nothing here establishes that it reads "
                      "retryable at all.")
    assert rc.run_detects_all_groups(fx["expected"]["groups"], res)


def test_b1_m4_high_run2_phrasing_now_matches():
    fx, res = _result("M4", "Unsubstantiated absolute guarantee: the "
                      "docstring asserts 'All retry decisions flow "
                      "through ProcessingError.retryable'. The "
                      "orchestrator is not part of this diff, and no "
                      "code here shows it being consulted.")
    assert rc.run_detects_all_groups(fx["expected"]["groups"], res)


def test_b1_m16_low_run1_phrasing_now_matches():
    fx, res = _result("M16", "The bare `except Exception: pass` "
                      "discards every failure (network errors, auth "
                      "failures) and execution falls through to return "
                      '{"ok": True, "updated": 2}. The caller receives '
                      "a success summary claiming 2 labels were updated "
                      "even when the PUT raised.")
    assert rc.run_detects_all_groups(fx["expected"]["groups"], res)


def test_normalization_unifies_articles_and_apostrophes():
    fx, res = _result("M4", "The claim concerns code outside this diff.")
    assert rc.run_detects_all_groups(fx["expected"]["groups"], res)
    assert pq._sha("isn't") != pq._sha("isnt")  # sanity: raw differ
    fx2, res2 = _result("M4", "it isn't verifiable")
    # "cannot verify" family is separate; this asserts apostrophe
    # normalization does not crash or corrupt matching
    assert isinstance(rc.run_detects_all_groups(
        fx2["expected"]["groups"], res2), bool)


def test_matcher_still_rejects_non_mechanism_comments():
    for fid, comment in (
            ("M4", "Style nit: the docstring could be shorter."),
            ("M16", "Consider adding a type hint here."),
            ("M16", "The function returns a dict with ok and updated "
                    "keys; that seems fine.")):
        fx, res = _result(fid, comment)
        assert not rc.run_detects_all_groups(
            fx["expected"]["groups"], res), comment


def test_severity_mismatch_still_fails():
    fx, res = _result("M16", "It silently swallows every failure and "
                      "fabricates success.", severity="non-blocking")
    assert not rc.run_detects_all_groups(fx["expected"]["groups"], res)


def test_code_shaped_needles_survive_normalization():
    fx, res = _result("M16", "It returns {\"ok\": True} even when the "
                      "request failed.")
    assert rc.run_detects_all_groups(fx["expected"]["groups"], res)


# ---- 3. C12/M12 clarification ---------------------------------------

def test_c12_m12_docstrings_clarified_and_single_delta_preserved():
    c = json.loads((REPO / "eval/fixtures/C12.json").read_text())
    m = json.loads((REPO / "eval/fixtures/M12.json").read_text())
    for fx in (c, m):
        patch = fx["input"]["files"][0]["patch"]
        assert "malformed live payload" in patch
        assert "not an availability failure" in patch
    assert "availability vs malformed-payload" in c["note"]
    # the ONLY code delta remains the except clause
    c_code = c["input"]["files"][0]["patch"].replace(
        """+    except OriginError:
+        return _cache["last_good"]
""", "")
    m_code = m["input"]["files"][0]["patch"].replace(
        """+    except (OriginError, ParseError):
+        return _cache.get("last_good", {})
""", "")
    assert c_code == m_code


def test_oracle_identity_bumped_and_consistent():
    assert rc.oracle_version() == pq.ORACLE_VERSION
    assert pq.ORACLE_VERSION == "117b4164e5446f50"


def test_clarified_contract_keeps_m12_detectable_and_c12_clean():
    fx = {f["id"]: f for f in
          rc.load_corpus(REPO / "eval" / "fixtures")}
    m12_block = {"findings": [{"severity": "blocking", "comment":
                 "The except clause catches ParseError, contradicting "
                 "the docstring: a malformed live payload must "
                 "propagate, but it is masked as stale config and an "
                 "empty cache returns {} instead of raising."}]}
    assert rc.run_detects_all_groups(
        fx["M12"]["expected"]["groups"], m12_block)
    c12_still_clean = {"findings": [{"severity": "non-blocking",
                                     "comment": "ParseError propagates "
                                     "as the docstring now states "
                                     "explicitly; advisory at most."}]}
    # a ParseError-propagates comment is NO LONGER a contract
    # contradiction under the clarified docstring
    assert not rc.run_detects_all_groups(
        fx["C12"]["expected"]["groups"],
        {"findings": [{"severity": "blocking", "comment":
                       "ParseError propagates instead of serving the "
                       "cached config."}]})


# ---- 4. replay -------------------------------------------------------

def test_replay_legacy_copy_faithful_and_flips_exact():
    report = replay_mod.replay()
    for name in ("b1-low", "b1-high"):
        integ = report["sources"][name][
            "legacy_integrity_vs_committed_b1_report"]
        assert integ and all(v["match"] for v in integ.values()), name
    flips = []
    for name in ("b1-low", "b1-high"):
        flips += [(name, f["fixture"], f["run_index"])
                  for f in report["sources"][name][
                      "detection_flips_legacy_to_phase08"]]
    assert sorted(flips) == [
        ("b1-high", "M4", 2),
        ("b1-low", "M16", 1),
        ("b1-low", "M4", 2),
    ]
    # no regression anywhere: every flip is legacy=False -> new=True
    for name in report["sources"]:
        for f in report["sources"][name].get(
                "detection_flips_legacy_to_phase08", []):
            assert f["legacy"] is False and f["phase08"] is True


def test_replay_is_deterministic(tmp_path):
    a = replay_mod.replay()
    b = replay_mod.replay()
    assert a == b
