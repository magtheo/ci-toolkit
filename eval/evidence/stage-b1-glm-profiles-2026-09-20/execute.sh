#!/usr/bin/env bash
# Stage B1 execution — frozen preregistered calibration screen.
# OFFLINE UNTIL GATES: requires OPENROUTER_API_KEY in the environment
# and constitutes the live-spend authorization when run (both gates:
# --live + PM_QUALIFY_LIVE_AUTHORIZED=1, exported here). $1.00
# AGGREGATE ceiling enforced by the shared ledger with atomic
# reserve/settle — approving the ceiling is not approving spend of $1.
# Matrix: 15 fixtures x N=3 x {low, high} = 90 logical reviews,
# frozen order (run 0 low->high, run 1 high->low, run 2 low->high).
set -euo pipefail
cd "$(dirname "$0")/../../.."

: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY must be in the environment}"
export PM_QUALIFY_LIVE_AUTHORIZED=1

EV=eval/evidence/stage-b1-glm-profiles-2026-09-20
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
    > "$EV/report-$e.json" && echo "report-$e.json written"
done
