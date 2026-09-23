"""Phase-19A preregistration checks.

The psd-only blocking-boundary promotion is preregistered BEFORE any
19B run exists. These tests pin the INTEGRATION_CONTRACT.json against
live reality and re-derive every frozen prediction deterministically
from the frozen corpus, so silent post-hoc edits to the prereg are
detectable. No promotion evaluator exists yet; none is executed here.
"""
import hashlib
import json
import pathlib
import sys
from collections import Counter

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.evidence_boundary_sim as boundary  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import eval.v21_contract_relations as frozen  # noqa: E402
import eval.v21_routes_replay as rr  # noqa: E402
import eval.v21_replay as v21  # noqa: E402

PREREG = REPO / "eval" / "evidence" / "v21-psd-promotion-prereg-2026-09-23"
CONTRACT = json.loads((PREREG / "INTEGRATION_CONTRACT.json").read_text())
PRED = CONTRACT["frozen_predictions"]
EVAL_19B = REPO / "eval" / "evidence" / "v21-psd-promotion-eval-2026-09-23"


def _rows():
    fixtures = {f["id"]: f
                for f in rc.load_corpus(REPO / "eval" / "fixtures")}
    rows = []
    source_records = 0
    for source, rel in boundary.SOURCES.items():
        records = [json.loads(line)
                   for line in (REPO / rel).read_text().splitlines()
                   if line.strip()]
        source_records += len(records)
        for ri, rec in enumerate(records):
            fixture = fixtures[rec["fixture"]]
            for fi, finding in enumerate(
                    (rec.get("result") or {}).get("findings", [])):
                if finding.get("severity") != "blocking":
                    continue
                sim = boundary.simulate_finding(finding, fixture)
                rows.append({
                    "source": source, "ri": ri, "fi": fi,
                    "fixture": fixture["id"],
                    "role": v21._role(finding, fixture),
                    "route": rr.route_of(finding, fixture, sim),
                    "psd": "pinned_sha_demoted_to_branch" in
                    frozen.relation_names(finding, fixture),
                    "g1": sim["g1_strict_quote"],
                    "g2": sim["g2_contract_aware"],
                })
    if source_records != CONTRACT["baseline"]["record_population"]:
        raise RuntimeError(
            "19A source population drift: expected %d records, found %d"
            % (CONTRACT["baseline"]["record_population"], source_records))
    return rows


def test_contract_pins_match_live_reality():
    assert CONTRACT["phase"] == "19A"
    assert CONTRACT["preregistered_before_any_19b_run"] is True
    subject = CONTRACT["subject"]
    assert subject["verifier_module_sha256"] == hashlib.sha256(
        (REPO / "eval" / "v21_contract_relations.py").read_bytes()
    ).hexdigest()
    assert subject["verifier_merge_sha"] == \
        "0631b0956f795ab1ee6d13f68b0c1cebe8a6d23b"
    assert CONTRACT["oracle_version"] == "117b4164e5446f50"
    assert CONTRACT["scope"]["route"] == "contract_contradiction"
    assert CONTRACT["scope"]["relations_promoted"] == [
        "pinned_sha_demoted_to_branch"]
    assert len(CONTRACT["scope"]["relations_explicitly_not_promoted"]) == 5
    assert CONTRACT["promotion_rule"]["promoted_value"] == \
        "BLOCK_EVIDENCE_BACKED"
    assert CONTRACT["promotion_rule"]["role_blind"] is True
    assert len(CONTRACT["invariants"]) == 8
    assert len(CONTRACT["halt_conditions"]) == 6


def test_19b_artifacts_exist_and_bind_to_prereg():
    """19A absence guard, superseded per reviewed transition: 19B has
    landed, so the artifacts must exist and bind to this prereg."""
    assert (REPO / "eval" / "v21_psd_promotion.py").exists()
    assert (EVAL_19B / "RESULTS-19B.md").exists()
    report = json.loads(
        (EVAL_19B / "psd-promotion-report.json").read_text())
    assert report["phase"] == "19B"
    contract_sha = hashlib.sha256(
        (PREREG / "INTEGRATION_CONTRACT.json").read_bytes()).hexdigest()
    assert report["prereg"]["contract_sha256"] == contract_sha
    # the executed rule is the preregistered rule
    import eval.v21_psd_promotion as pp
    assert report == pp.evaluate()


def test_baseline_aggregates_match_frozen_predictions():
    rows = _rows()
    assert CONTRACT["baseline"]["record_population"] == 414
    assert len(rows) == CONTRACT["baseline"]["population"] == 276
    split = Counter(r["g2"] for r in rows)
    assert dict(split) == CONTRACT["baseline"]["aggregate"]
    for role, expected in CONTRACT["baseline"]["by_role"].items():
        assert dict(Counter(r["g2"] for r in rows
                            if r["role"] == role)) == expected
    contract_route = dict(Counter(r["g2"] for r in rows
                                  if r["route"] == "contract_contradiction"))
    assert contract_route == CONTRACT["baseline"]["contract_route"]


def test_psd_fired_landscape_matches_frozen_predictions():
    rows = _rows()
    fired = [r for r in rows if r["psd"]]
    assert len(fired) == PRED["psd_fires_on"] == 24
    assert dict(Counter(r["role"] for r in fired)) == {
        k: v for k, v in PRED["psd_fired_roles"].items() if v}
    for zero_role in ("control_blocker", "positive_extra_blocker"):
        assert PRED["psd_fired_roles"][zero_role] == 0
        assert not any(r["role"] == zero_role for r in fired)
    assert dict(Counter(r["fixture"] for r in fired)) == \
        PRED["psd_fired_fixtures"]
    assert dict(Counter(r["g2"] for r in fired)) == \
        PRED["psd_fired_baseline_split"]
    downgraded = [r for r in fired if r["g2"] == "DOWNGRADE"]
    assert dict(Counter(r["route"] for r in downgraded)) == \
        PRED["downgraded_psd_fired_by_route"]
    assert set(PRED["downgraded_psd_fired_by_route"]) == {
        "contract_contradiction", "external_fact",
        "unwitnessed_behavior"}
    # the contract-route downgraded fired row is the only eligible one
    eligible = [r for r in downgraded
                if r["route"] == "contract_contradiction"]
    assert len(eligible) == 1


def test_promotion_set_identity_matches_frozen_prediction():
    rows = _rows()
    expected = PRED["promotion_set"]
    assert len(expected) == 1
    eligible = [r for r in rows
                if r["route"] == "contract_contradiction"
                and r["psd"] and r["g2"] == "DOWNGRADE"]
    assert len(eligible) == 1
    row = eligible[0]
    want = expected[0]
    assert (row["source"], row["ri"], row["fi"], row["fixture"],
            row["route"], row["role"], row["g1"], row["g2"]) == (
        want["source"], want["record_index"], want["finding_index"],
        want["fixture"], want["route"], want["role"],
        want["g1_strict_quote"], want["g2_contract_aware"])
    record = [json.loads(line)
              for line in (REPO / boundary.SOURCES[row["source"]])
              .read_text().splitlines() if line.strip()][row["ri"]]
    finding = record["result"]["findings"][row["fi"]]
    assert finding.get("file") == want["finding_file"]
    assert record["fixture"] == "M2"


def test_protocol_freezes_scope_halt_and_limitation():
    protocol = (PREREG / "PROTOCOL.md").read_text()
    assert "preregistration only" in protocol
    assert "without changing the behavior of any other claim route" \
        in protocol
    assert "`BLOCK_EVIDENCE_BACKED` iff" in protocol
    assert "predicted promotion set: exactly 1 row" in protocol
    assert "downgrades on non-contract routes" in protocol
    assert "never silently reconciled" in protocol
    assert "not a GATING-registry promotion" in protocol
    assert "bb0ebdeeb7fc80395626bf10d3" in protocol
    assert "117b4164e5446f50" in protocol
    base = CONTRACT["baseline"]
    psd = CONTRACT["frozen_predictions"]
    assert f"population: **{base['population']}** blocking rows" in protocol
    assert (
        f"**{base['aggregate']['BLOCK_SURVIVES']} `BLOCK_SURVIVES` / "
        f"{base['aggregate']['DOWNGRADE']} `DOWNGRADE`**"
    ) in protocol
    assert (
        f"**{psd['psd_fires_on']}** rows"
    ) in protocol
    contract_downgrades = psd["downgraded_psd_fired_by_route"]
    assert (
        f"**{contract_downgrades['contract_contradiction']}** on"
    ) in protocol
    assert (
        f"{contract_downgrades['external_fact']} on `external_fact`, "
        f"{contract_downgrades['unwitnessed_behavior']} on"
    ) in protocol
    assert (
        f"**predicted promotion set: exactly "
        f"{len(psd['promotion_set'])} row**"
    ) in protocol
    assert "27 baseline control blockers" in protocol
