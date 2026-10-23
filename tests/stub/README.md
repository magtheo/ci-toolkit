# tests/stub — scenario-driven API stub harness (behavioral, not grep)

A fake `curl` executable placed first on `PATH` so `review.sh` runs
end-to-end against canned GitHub/OpenRouter responses — no network, no
API key, no model spend.

- `curl` — the stub (see its docstring for the route/response model).
- Scenarios are built at runtime by `tests/test_review_head_guard.py`;
  each scenario directory holds `routes.json` (ordered substring
  routes; per-route call counters make head movement between calls
  expressible), fixture JSON files, `calls.log` (every request the
  script made), and `posts/` (bodies the script tried to POST).

Design constraint (review advisory 3): race windows are asserted from
**observed behavior** — exit codes, the calls log, and saved POST
bodies — never by grepping the script for guard keywords.
