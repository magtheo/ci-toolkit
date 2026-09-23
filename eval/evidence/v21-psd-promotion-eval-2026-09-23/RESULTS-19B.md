# Phase 19B — psd-only blocking-boundary promotion: result

Execution of the frozen Phase-19A preregistration
(`eval/evidence/v21-psd-promotion-prereg-2026-09-23/`), verbatim:
method `python3 eval/v21_psd_promotion.py`, report
`psd-promotion-report.json` (SHA-pinned and test-bound to live
evaluator output). The frozen Phase-17 verifier was called, never
modified (`bb0ebdee…` verified in-run); routes, predicates, parser,
fixtures, and oracle were called, never modified.

## Outcome: SUCCESS — every frozen invariant held

| measure | frozen prediction | observed |
|---|---:|---:|
| blocking population | 276 | 276 |
| baseline (g2) | 145 BLOCK / 131 DOWNGRADE | 145 BLOCK / 131 DOWNGRADE |
| psd-matching rows | 24 (all M2 TP, 0 control, 0 extra) | 24 (all M2 TP, 0 control, 0 extra) |
| psd-matched baseline split | 5 BLOCK / 19 DOWNGRADE | 5 BLOCK / 19 DOWNGRADE |
| downgraded matches by route | 1 contract / 12 external / 6 unwitnessed | 1 / 12 / 6 |
| **promotions** | **exactly 1** | **exactly 1** |
| unchanged decisions | 275 | 275 |
| collateral changes | 0 | 0 |
| new control/extra promotions | 0 | 0 |

**Integrated aggregate: 145 `BLOCK_SURVIVES` + 1
`BLOCK_EVIDENCE_BACKED` + 130 `DOWNGRADE`.** The single promoted row
is the frozen prediction exactly: `stage-a-max` record 28, finding 0,
fixture M2, `.github/workflows/ai-review.yml` — a reusable-workflow
reference changed from a pinned full commit SHA to mutable `@main`,
on the `contract_contradiction` route, previously downgraded by both
the quote gate and the contract-aware gate, now sustained by the
holdout-validated psd verifier.

Standing regression guards all held (C11 refused; M3 witnessed;
M13/C12/M12 refused; M10 relation still FAILED with C10 standing
near-miss; oracle `117b4164e5446f50`). The historical 18B and 18D
reports are byte-for-byte unchanged (SHA-256 verified in-run).

## Scope and meaning

psd is now **eligible as the first evidence-backed blocker on the
`contract_contradiction` route for this oracle** — a measured,
scoped integration result. Per the frozen prereg and the reviewer's
19A clarification, this does **not** authorize GATING activation, does
not promote the broader registry, and does not address the baseline's
27 surviving control blockers (zero new control promotions here; the
pre-existing baseline remainder is untouched by this experiment).

The accepted scope limitation holds: the 18 psd-matching downgrades
outside the contract route (12 `external_fact`, 6
`unwitnessed_behavior`) **remain downgraded by design** — the
existing route boundary is preserved rather than expanded. Extending
evidence-backed blocking beyond the contract route is future
preregistered work.

Humility rule: eligibility is scoped to this oracle (this harness,
corpus, and GATING state); it is not a correctness claim about any
subject.
