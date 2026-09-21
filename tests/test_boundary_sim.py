"""Phase-09 evidence-boundary simulation tests.

The simulation is deterministic, offline, and replays the FROZEN 414
Stage-A/B1 records. These tests pin its structural integrity, its
determinism, extraction honesty (no bare-token harvesting), gate
monotonicity, and a handful of evidence-pinned rows.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.evidence_boundary_sim as sim  # noqa: E402
import eval.run_corpus as rc  # noqa: E402

B1 = REPO / "eval/evidence/stage-b1-glm-profiles-2026-09-20"
SOURCES = {
    "stage-a-low": "eval/evidence/stage-a-glm-profiles-2026-09-19/low/records.jsonl",
    "stage-a-high": "eval/evidence/stage-a-glm-profiles-2026-09-19/high/records.jsonl",
    "stage-a-max": "eval/evidence/stage-a-glm-profiles-2026-09-19/max/records.jsonl",
    "b1-low": "eval/evidence/stage-b1-glm-profiles-2026-09-20/low/records.jsonl",
    "b1-high": "eval/evidence/stage-b1-glm-profiles-2026-09-20/high/records.jsonl",
}


@pytest.fixture(scope="module")
def report():
    return sim.replay()


# ---- structure -------------------------------------------------------

def test_frozen_corpus_coverage(report):
    """Every blocking finding across the frozen 414 records appears
    exactly once, with full per-finding fields."""
    expected = 0
    for rel in SOURCES.values():
        for rec in (json.loads(l) for l in
                    (REPO / rel).read_text().splitlines() if l.strip()):
            if rec.get("result"):
                expected += sum(1 for f in rec["result"]["findings"]
                                if f.get("severity") == "blocking")
    assert report["total_records"] == sim.EXPECTED_TOTAL == 414
    assert report["total_blocking_findings"] == expected == 276
    rows = [r for s in report["sources"].values()
            for r in s["findings"]]
    assert len(rows) == 276
    for r in rows:
        for field in ("fixture", "kind", "role", "effort", "run_index",
                      "cited_file", "quotes", "g1_strict_quote",
                      "g1h_harm_anchored", "g2_contract_aware",
                      "reason"):
            assert field in r, field


def test_simulation_is_deterministic():
    assert sim.replay() == sim.replay()


def test_g2_never_downgrades_what_g1_survives(report):
    for s in report["sources"].values():
        for r in s["findings"]:
            if r["g1_strict_quote"] == "BLOCK_SURVIVES":
                assert r["g2_contract_aware"] == "BLOCK_SURVIVES"


def test_every_row_role_is_sound(report):
    for s in report["sources"].values():
        for r in s["findings"]:
            if r["kind"] == "control":
                assert r["role"] == "control_blocker"
            else:
                assert r["role"] in ("true_positive_detection",
                                     "positive_extra_blocker")


# ---- extraction honesty ---------------------------------------------

def test_bare_identifiers_are_not_quotes():
    c = ("The except clause only catches OriginError and session "
         "handling is untested.")
    q = sim._quotes(c)
    assert q == []  # no backticks, no quotation marks -> no quotes


def test_quoted_spans_are_extracted():
    q = sim._quotes("The code uses `find -mtime -30` and the header "
                    "says 'judged from the PARSED DATE' plus a "
                    "\"returns {\\\"ok\\\"}\" shape.")
    norms = {x["normalized"] for x in q}
    assert "find -mtime -30" in norms
    assert "judged from parsed date" in norms  # article-normalized


def test_apostrophes_do_not_create_fake_spans():
    assert sim._quotes("The caller isn't handling this and it's "
                       "wrong.") == []


def test_harm_anchoring_is_sentence_scoped():
    q = sim._quotes("The helper builds the config. This means callers "
                    "would silently receive `last_good` garbage.")
    hit = [x for x in q if x["normalized"] == "last_good"]
    assert hit and hit[0]["harm_anchored"] is True


# ---- evidence-pinned rows -------------------------------------------

def test_c13_b1_survivor_is_the_real_keyword_in_a_harm_sentence(report):
    """The design's core problem, pinned: C13's surviving blockers
    anchor presumed harm (unseen checkout) to REAL in-diff keywords
    (pull_request_target, !head.repo.fork). Every survivor rides on an
    in-patch quote; at least one does so inside a harm sentence."""
    surv = [r for s in report["sources"].values() for r in s["findings"]
            if r["fixture"] == "C13"
            and r["g1_strict_quote"] == "BLOCK_SURVIVES"]
    assert surv, "expected the trigger-keyword survivors"
    for r in surv:
        assert any(q["in_cited_patch"] for q in r["quotes"])
    assert any(q["in_cited_patch"] and q["harm_anchored"]
               for r in surv for q in r["quotes"])


def test_pr_description_quote_does_not_count_as_in_diff(report):
    """'on origin failure serve last-good' is PR-prose, not patch
    text (post-clarification): a blocker quoting only it downgrades."""
    rows = [r for s in report["sources"].values() for r in s["findings"]
            if r["fixture"] == "M12" and r["source"] == "stage-a-low"
            and r["run_index"] == 0
            and r["role"] == "positive_extra_blocker"]
    assert rows and rows[0]["g1_strict_quote"] == "DOWNGRADE"
    assert any("on origin failure" in q["normalized"]
               for q in rows[0]["quotes"])
    assert all(not q["in_cited_patch"] for q in rows[0]["quotes"])


def test_ii_a_path_exists_but_never_rescues_on_v1_data(report):
    """The (ii-a) contract path fires (contract findings quote their
    file's documentation) but never rescues a G1-downgraded finding:
    quote-less contract findings don't operationalize it on v1
    prose."""
    assert report["summary"]["ii_a_contract_path_fired"] > 0
    assert report["summary"]["ii_a_rescued_any_g1_downgrade"] is False


def test_synthetic_contract_contradiction_survives_g2():
    """The ii-a path works as specified on a well-formed v2-style
    finding: doc-quote + contradiction + contract-ref language."""
    fx = {f["id"]: f for f in
          rc.load_corpus(REPO / "eval" / "fixtures")}
    finding = {"severity": "blocking",
               "file": "roadmap-freshness.sh",
               "comment": "The header comment promises the check is "
                          "'judged from the PARSED DATE' but the code "
                          "uses find -mtime -30 instead, contradicting "
                          "the documented contract."}
    out = sim.simulate_finding(finding, fx["M3"])
    assert out["ii_a_contract_path"] is True
    assert out["g2_contract_aware"] == "BLOCK_SURVIVES"


def test_summary_buckets_add_up(report):
    s = report["summary"]
    role_total = 0
    for role, gates in s["by_role"].items():
        totals = {v["total"] for v in gates.values()}
        assert len(totals) == 1
        role_total += totals.pop()
        for v in gates.values():
            assert v["survives"] + v["downgraded"] == v["total"]
    assert role_total == report["total_blocking_findings"] == 276

    for source, roles in s["by_source"].items():
        source_total = 0
        for role, gates in roles.items():
            totals = {v["total"] for v in gates.values()}
            assert len(totals) == 1
            source_total += totals.pop()
            for v in gates.values():
                assert v["survives"] + v["downgraded"] == v["total"]
        assert source_total == report["sources"][source]["blocking_findings"]

    # Focus fixtures are a strict subset, but every gate must preserve
    # the same per-fixture denominator.
    for gates in s["focus_fixtures"].values():
        assert len({v["total"] for v in gates.values()}) == 1
