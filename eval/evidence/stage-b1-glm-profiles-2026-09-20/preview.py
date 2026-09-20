#!/usr/bin/env python3
"""Offline dry-run preview of the complete Stage B1 campaign.

Enumerates all 90 planned logical reviews (15 fixtures x N=3 x
{low, high}) in the frozen order, constructing each initial request
through the real engine/transport stack — no provider call is made
(dry-run post_payload is None). Produces dry-run-preview.json with
the identity pins and the worst-case aggregate cost bound.

The preview records live under dry-run/ and are NOT the live
evidence directories; live invocation refuses nothing from them
because it never reads them (separate directories per effort).
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import eval.profile_qualification as pq  # noqa: E402
import eval.run_corpus as rc  # noqa: E402

EV = ROOT / "eval/evidence/stage-b1-glm-profiles-2026-09-20"
DRY = EV / "dry-run"
ORDER = [("low", 0), ("high", 0), ("high", 1), ("low", 1),
         ("low", 2), ("high", 2)]
MODEL = "z-ai/glm-5.3-flash"
FIXTURES = ["C1", "C2", "C3", "C4", "C5", "C12", "C13", "C14", "C16",
            "M2", "M3", "M4", "M12", "M13", "M16"]
PRICES = {"in": 0.075, "out": 0.25}


def main():
    engine = pq.load_subject_engine()
    all_fixtures = pq.corpus()
    by_id = {f["id"]: f for f in all_fixtures}
    assert set(FIXTURES) <= set(by_id), "fixture missing from corpus"

    guard = pq.SpendGuard(1.0, PRICES["in"], PRICES["out"], {})
    reviews = []
    for effort, ri in ORDER:
        profile, overrides = pq.measurement_profile(MODEL, effort, None)
        out = DRY / ("%s-%d" % (effort, ri))
        for fid in FIXTURES:
            rec = pq.logical_review(
                engine, by_id[fid], ri, MODEL, profile, overrides,
                None, lambda r: None)
            reviews.append({
                "effort": effort, "run_index": ri, "fixture": fid,
                "prompt_sha256": rec["prompt_sha256"],
                "request_sha256": rec["request_sha256"],
                "prompt_chars": rec["prompt_chars"],
                "escalation_planned": rec["escalation_planned"],
            })

    # worst-case aggregate bound from the actual prompt sizes,
    # INCLUDING the planned escalation generation (initial 8000 +
    # up to one 16000-token escalation per review) — informational
    # only; the ceiling is enforced per request by the ledger
    worst_total = 0.0
    worst_initial_only = 0.0
    for r in reviews:
        chars = r["prompt_chars"][0] + r["prompt_chars"][1]
        est_in = -(-chars // 4) * pq.SpendGuard.SAFETY
        initial = (est_in * PRICES["in"] + 8000 * PRICES["out"]) / 1e6
        worst_initial_only += initial
        if r["escalation_planned"]:
            worst_total += initial + (est_in * PRICES["in"]
                                      + 16000 * PRICES["out"]) / 1e6
        else:
            worst_total += initial

    preview = {
        "status": "DRY_RUN_PREVIEW — no provider request was made",
        "matrix": {"fixtures": FIXTURES, "n_runs": 3,
                   "efforts": ["low", "high"],
                   "logical_reviews": len(reviews)},
        "frozen_order": ["%s-%d" % (e, i) for e, i in ORDER],
        "identity": {
            "oracle_version": rc.oracle_version(),
            "rubric_sha256": hashlib.sha256(
                (ROOT / "rubric.md").read_bytes()).hexdigest(),
            "subject_content_ref": pq.subject_content_ref(),
            "transport_content_ref": pq.transport_content_ref(),
            "oracle_checkout_sha": pq.ORACLE_CHECKOUT_SHA,
            "transport_sha": pq.TRANSPORT_SHA,
        },
        "ceiling": {"aggregate_usd": 1.0,
                    "worst_case_all_90_usd": round(worst_total, 4),
                    "worst_case_initial_8000_only_usd":
                        round(worst_initial_only, 4),
                    "cost_model": "worst case includes the initial "
                                  "8000-token generation PLUS one "
                                  "16000-token escalation per review "
                                  "where planned; enforcement is "
                                  "per-request via the ledger, this "
                                  "projection is informational",
                    "mechanism": "shared ledger, atomic reserve/settle"},
        "reviews": reviews,
    }
    (EV / "dry-run-preview.json").write_text(
        json.dumps(preview, indent=1) + "\n")
    print("reviews previewed:", len(reviews))
    print("oracle_version:", preview["identity"]["oracle_version"])
    print("rubric_sha256:", preview["identity"]["rubric_sha256"][:16], "…")
    print("worst-case bound, all 90 WITH escalations: $%.4f of $1.00"
          % worst_total)
    print("worst-case bound, initial 8000 only: $%.4f (context)"
          % worst_initial_only)


if __name__ == "__main__":
    main()
