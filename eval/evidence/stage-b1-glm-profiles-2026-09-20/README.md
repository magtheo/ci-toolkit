# Stage B1 evidence — GLM profiles (frozen preregistered calibration screen)

Executed 2026-09-21. **Verdict: B1 FAIL** (see `b1-campaign-verdict.json`,
aggregate denominators). Published exactly as produced — no rerun, no
normalization, no regeneration of any model output.

## Identities (verified before the first provider request)

| Identity | Value |
|---|---|
| Executed at | feature merge `74127231d1bac4d43fd46096127579cb05cc0150` |
| Model | `z-ai/glm-5.3-flash` |
| `oracle_version` | `5472d990f3b946c3` |
| Rubric SHA-256 | `f13db50022cab1f498c13c1abdb802e1a3624c33bae28ab2c31c32b12f407e37` |
| Subject content ref | `9234a662e65cd368c4a1a65b53d0b84d800acf12fa85f06b1eb9753cbae98a78` |
| Transport content ref | `dd655bd7c12c7394ba3344d890eae1364731cf5d6a117609305e01c414636833` |
| Matrix | controls C1,C2,C3,C4,C5,C12,C13,C14,C16 + positives M2,M3,M4,M12,M13,M16, N=3, {low, high} |

The regenerated 90-review dry-run preview was byte-identical to the committed
`dry-run-preview.json` before launch.

## Execution

- **90/90 logical reviews completed**, frozen order `low0, high0, high1, low1, low2, high2`.
- **Zero transport failures. Zero INCONCLUSIVE. Zero escalations. Zero ceiling halts**
  (0 orphan sweeps, 0 outstanding reservations at close).

## Spend

- **Authoritative aggregate ledger: $0.044286 settled** of the $1.00 hard ceiling
  (156,002 input / 130,302 output tokens; ledger invariant held throughout).
- **Recorded accounting discrepancy (not repaired here):** summed per-effort
  `summary.json` `actual_cost_usd` fields total ≈ **$0.015485**, which does not
  reconcile with the ledger. The shared ledger was the authoritative
  hard-ceiling instrument for this campaign; the summary-field mismatch
  requires separate tooling diagnosis in a later reviewed change and does not
  retroactively alter this frozen evidence.

## Outcome (frozen criteria, `b1-report-{low,high}.json`)

- **Control blockers at BOTH efforts: C3, C12, C13**
  (C12: 3 low + 3 high; C13: 3 low + 3 high; C3: 5 low + 2 high blocking
  findings) → zero-control-blocker gate FAIL on both efforts.
- **Low-effort detection regressions: M3 2/3 vs 3/3 baseline; M16 2/3 vs 3/3
  baseline.** High effort: no regressions (all at baseline).
- **M4 standalone (zero Stage-A baseline, not gateable): 2/3 low, 2/3 high.**
- **M13 standalone (zero Stage-A baseline): 0/3 low, 0/3 high** — KNOWN_GAP,
  unchanged from baseline.
- Viability gates all PASS (0/90 INCONCLUSIVE, 0 transport failures,
  0 escalations).

## Consequences

- **B1 FAIL → B2 is not permitted** (no B2 preregistration on a FAIL).
- **GLM remains non-authoritative**; no profile promotion, no deployment change.
- Any next intervention must be chosen from this frozen evidence and reviewed
  separately.

## Contents

- `b1-campaign-verdict.json` — final campaign verdict (aggregate denominators)
- `b1-report-low.json`, `b1-report-high.json` — per-effort frozen-criteria reports
- `stage-a-style-report-{low,high}.json` — context-only Stage-A-style reports
- `low/records.jsonl`, `high/records.jsonl` — full frozen records (45 each)
- `low/summary.json`, `high/summary.json` — per-effort run summaries
- `spend-ledger.json` — the authoritative aggregate spend ledger
- `dry-run-preview.json`, `execute.sh`, `preview.py` — pre-committed launch artifacts
