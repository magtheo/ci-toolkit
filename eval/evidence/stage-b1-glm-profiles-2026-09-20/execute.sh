#!/usr/bin/env bash
# Stage B1 execution — frozen preregistered calibration screen.
#
# AUTHORIZATION BOUNDARY: the operator must supply BOTH
#   OPENROUTER_API_KEY           (possession of a key is not authorization)
#   PM_QUALIFY_LIVE_AUTHORIZED=1 (explicit live-spend authorization)
# This script does not set the authorization gate itself.
#
# Ceiling: $1.00 AGGREGATE enforced by the shared ledger with atomic
# reserve/settle. Matrix: exactly the preregistered 15 fixtures
# (--fixtures below; the corpus default of 36 must never leak in),
# N=3, {low, high} = 90 logical reviews, frozen order
# (run 0 low->high, run 1 high->low, run 2 low->high).
set -euo pipefail
cd "$(dirname "$0")/../../.."

: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY must be in the environment}"
: "${PM_QUALIFY_LIVE_AUTHORIZED:?PM_QUALIFY_LIVE_AUTHORIZED=1 must be set by the operator (explicit live-spend authorization — possession of an API key is not authorization)}"
if [ "$PM_QUALIFY_LIVE_AUTHORIZED" != "1" ]; then
  echo "PM_QUALIFY_LIVE_AUTHORIZED must be exactly 1" >&2
  exit 1
fi

EV=eval/evidence/stage-b1-glm-profiles-2026-09-20
FIXTURES="C1,C2,C3,C4,C5,C12,C13,C14,C16,M2,M3,M4,M12,M13,M16"
BASELINE=eval/evidence/stage-b1-prereg-2026-09-20/baseline-stage-a.json
LEDGER_ARGS="--spend-ledger $EV/spend-ledger.json --spend-seed-dir $EV/low --spend-seed-dir $EV/high"

run() { # effort run_index
  local effort=$1 idx=$2
  echo "=== $(date -Is) effort=$effort run_index=$idx ==="
  # shellcheck disable=SC2086
  python3 eval/profile_qualification.py \
    --model z-ai/glm-5.3-flash \
    --reasoning-effort "$effort" \
    --run-index "$idx" \
    --runs 3 \
    --fixtures "$FIXTURES" \
    --out "$EV/$effort" \
    --live \
    --spend-ceiling-usd 1 \
    $LEDGER_ARGS \
    --price-input-per-m 0.075 \
    --price-output-per-m 0.25 \
    --price-source "openrouter.ai z-ai/glm-5.3-flash 2026-09-18 discounted"
  python3 - "$EV/$effort/summary.json" "$EV/spend-ledger.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
led = json.load(open(sys.argv[2]))
sp = s.get("spend", {})
print("reviews=%s gens=%s escalations=%s inconclusive=%s ceiling_left=$%s "
      "(ledger settled=$%s outstanding=%s invariant=%s)" % (
          s.get("logical_reviews"), sp.get("provider_generations"),
          sp.get("escalations"), sp.get("final_inconclusive"),
          sp.get("ceiling_remaining_usd"),
          led.get("settled_usd"), len(led.get("reservations", [])),
          (led.get("settled_usd", 0) + sum(r["usd"] for r in led.get("reservations", []))) <= 1.0 + 1e-9))
PY
}

# preregistered frozen order
run low  0
run high 0
run high 1
run low  1
run low  2
run high 2

echo "=== campaign complete $(date -Is) ==="
for e in low high; do
  python3 eval/profile_qualification.py --report "$EV/$e/records.jsonl" \
    > "$EV/stage-a-style-report-$e.json" && echo "stage-a-style-report-$e.json written (context only)"
  python3 eval/stage_b1_report.py \
    --records "$EV/$e/records.jsonl" \
    --baseline "$BASELINE" \
    --effort "$e" \
    --fixtures "$FIXTURES" \
    --runs 3 \
    --spend-summary "$EV/$e/summary.json" \
    > "$EV/b1-report-$e.json" && echo "b1-report-$e.json written (frozen criteria)"
done
python3 - <<'PY'
import json
EV = "eval/evidence/stage-b1-glm-profiles-2026-09-20"
reports = {e: json.load(open(f"{EV}/b1-report-{e}.json")) for e in ("low", "high")}
for e, r in reports.items():
    print(f"{e}: {r['verdict']} | failures: {r['gating_failures']}")
PY
