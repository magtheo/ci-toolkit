#!/usr/bin/env python3
"""Qualification-record verification (consumer side, secretless).

Enforces the deployment invariant mechanically:

    a reviewer can only be newly deployed if it passes the CURRENT
    GATING oracle — a PASS against an oracle that is no longer
    current does not authorize a new pin promotion.

Checks, all of which must hold:
1. the record's subject_sha matches the SHA a pin-bump PR proposes;
2. result is PASS (not forced-red, which is labeled demonstration);
3. the record's oracle_version equals the CURRENT oracle (computed
   from the toolkit repo's main by the calling workflow — this module
   never trusts a caller-supplied "current" without being given it
   explicitly);
4. the record's model profile is in the caller's allowlist.

Exit 0 = deployable evidence; exit 1 = refuse (reasons printed).
"""

import argparse
import json
import sys

DEFAULT_ALLOWED_MODELS = "anthropic/claude-haiku-4.5"


def verify(record, current_oracle_version, subject_sha,
           allowed_models):
    reasons = []

    if record.get("subject_sha") != subject_sha:
        reasons.append(
            "subject mismatch: record {0!r} != proposed {1!r}".format(
                record.get("subject_sha"), subject_sha))

    if record.get("forced_red"):
        reasons.append("record is a forced-red demonstration, not "
                       "qualification evidence")
    elif record.get("result") != "PASS":
        reasons.append(
            "result is {0!r}, not PASS".format(record.get("result")))

    if record.get("oracle_version") != current_oracle_version:
        reasons.append(
            "stale oracle: record {0!r} != current {1!r} — re-qualify "
            "the subject against the current oracle before promoting".format(
                record.get("oracle_version"), current_oracle_version))

    model = (record.get("model_profile") or {}).get("model")
    if model not in allowed_models:
        reasons.append(
            "model {0!r} not in allowed profiles {1}".format(
                model, sorted(allowed_models)))

    return {"verdict": "PASS" if not reasons else "FAIL",
            "reasons": reasons,
            "summary": {
                "subject_sha": record.get("subject_sha"),
                "oracle_version": record.get("oracle_version"),
                "result": record.get("result"),
                "model": model,
                "n": record.get("n"),
                "promotion_eligible_positives":
                    record.get("promotion_eligible_positives", []),
                "pair_integrity_violations":
                    record.get("pair_integrity_violations", []),
                "timestamp": record.get("timestamp"),
            }}


def main(argv=None):
    ap = argparse.ArgumentParser(description="verify a qualification record")
    ap.add_argument("record", help="path to the qualification record JSON")
    ap.add_argument("--oracle-version", required=True,
                    help="CURRENT oracle version (computed by the caller "
                         "from toolkit main)")
    ap.add_argument("--subject", required=True,
                    help="SHA the pin-bump PR proposes to deploy")
    ap.add_argument("--allow-model", action="append",
                    help="acceptable model profile (repeatable); when "
                         "given, the list is AUTHORITATIVE and replaces "
                         "the default — a caller restricting profiles "
                         "must be able to exclude the default too")
    args = ap.parse_args(argv)
    allowed = args.allow_model or [DEFAULT_ALLOWED_MODELS]

    with open(args.record) as fh:
        record = json.load(fh)

    verdict = verify(record, args.oracle_version, args.subject,
                     set(allowed))
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
