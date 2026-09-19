#!/usr/bin/env bash
# Stage-A execution — frozen preregistered campaign (authorized 2026-09-19, $10 ceiling).
# Requires OPENROUTER_API_KEY in the environment. Both live gates active.
# Balanced cyclic order; one evidence directory + campaign identity per effort.
set -euo pipefail
cd "$(dirname "$0")/../../.."

: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY must be in the environment}"
export PM_QUALIFY_LIVE_AUTHORIZED=1

EV=eval/evidence/stage-a-glm-profiles-2026-09-19
PRICE_ARGS="--spend-ceiling-usd 10 --price-input-per-m 0.075 --price-output-per-m 0.25 --price-source 'openrouter.ai z-ai/glm-5.3-flash 2026-09-18 discounted'"

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
    --spend-ceiling-usd 10 \
    --price-input-per-m 0.075 \
    --price-output-per-m 0.25 \
    --price-source "openrouter.ai z-ai/glm-5.3-flash 2026-09-18 discounted"
  python3 - "$EV/$effort/summary.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
sp = s.get("spend", {})
print("reviews=%s gens=%s escalations=%s inconclusive=%s ceiling_left=$%s" % (
    s.get("logical_reviews"), s.get("provider_generations"),
    s.get("escalations"), s.get("final_inconclusive"),
    sp.get("ceiling_remaining_usd")))
PY
}

# preregistered balanced cyclic schedule
run low  0
run high 0
run max  0
run high 1
run max  1
run low  1
run max  2
run low  2
run high 2

echo "=== campaign complete $(date -Is) ==="
for e in low high max; do
  python3 eval/profile_qualification.py --report "$EV/$e/records.jsonl" \
    > "$EV/report-$e.json" && echo "report-$e.json written"
done
