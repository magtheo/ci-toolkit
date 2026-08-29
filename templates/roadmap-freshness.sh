#!/usr/bin/env bash
# Roadmap freshness guard — logic (called by roadmap-freshness.yml).
#
# ci-toolkit governance copy-template: COPY to e.g.
# .github/scripts/roadmap-freshness.sh and adjust the workflow's path.
#
# Contract (validated by tests/test_roadmap_freshness.py):
#   - fresh review (< MAX_AGE_DAYS)                -> exit 0, quiet green
#   - stale + NO commits since the review date     -> exit 0, quiet green
#   - stale + commits since the review date        -> exit 1, red
#
# The "since" boundary is the PARSED 'Last reviewed:' date — never a
# rolling window: work that landed after a stale review must turn the
# guard red no matter how old that work is.

set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
ROADMAP="${1:-plans/ROADMAP.md}"
MAX_AGE_DAYS="${2:-28}"

last=$(grep -m1 '^Last reviewed:' "$ROADMAP" | sed 's/^Last reviewed: *//' | tr -d '[:space:]' || true)
if [ -z "$last" ]; then
  echo "::error::no 'Last reviewed:' date found in $ROADMAP"
  exit 1
fi
last_ts=$(date -d "$last" +%s) || {
  echo "::error::cannot parse 'Last reviewed:' date '$last'"
  exit 1
}
age_days=$(( ($(date +%s) - last_ts) / 86400 ))

if [ "$age_days" -lt "$MAX_AGE_DAYS" ]; then
  echo "roadmap reviewed ${age_days}d ago — fresh"
  exit 0
fi

# commits AFTER the review day count; same-day commits (including the
# review bump itself) are part of the review action
since_date=$(date -d "$last + 1 day" +%Y-%m-%d 2>/dev/null || echo "$last")
if [ -n "$(git rev-list -n1 HEAD --since="$since_date")" ]; then
  echo "::error::roadmap stale (${age_days}d) WITH commits since ${last} — reconsider and bump 'Last reviewed:'"
  exit 1
fi

echo "roadmap stale (${age_days}d) but no commits since the last review — quiet green"
