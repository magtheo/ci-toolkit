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

    # worst-case aggregate bound from the actual prompt sizes
    worst_total = 0.0
    for r in reviews:
        est_in = (r["prompt_chars"][0] + r["prompt_chars"][1])
        est_in = -(-est_in // 4) * pq.SpendGuard.SAFETY
        gen = 8000
        worst_total += (est_in * PRICES["in"] + gen * PRICES["out"]) / 1e6

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
                    "mechanism": "shared ledger, atomic reserve/settle"},
        "reviews": reviews,
    }
    (EV / "dry-run-preview.json").write_text(
        json.dumps(preview, indent=1) + "\n")
    print("reviews previewed:", len(reviews))
    print("oracle_version:", preview["identity"]["oracle_version"])
    print("rubric_sha256:", preview["identity"]["rubric_sha256"][:16], "…")
    print("worst-case bound for all 90: $%.4f of $1.00" % worst_total)


if __name__ == "__main__":
    main()
