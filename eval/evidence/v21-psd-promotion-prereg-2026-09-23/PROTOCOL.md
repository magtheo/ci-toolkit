# Phase 19A — psd-only blocking-boundary promotion: preregistration

**Status: preregistration only. No evaluator exists yet; no promotion
run has been performed. Phase 19B executes this protocol verbatim
after human review of this document.**

## Question

Can `pinned_sha_demoted_to_branch` (psd) — the single
GENERALIZATION-PASS relation from the Phase-18 holdout (5/5 positives,
0/5 controls, PR #97) — be integrated into the v2.1 blocking boundary
**without changing the behavior of any other claim route**?

## Scope (frozen)

- psd promotion applies **only** on the `contract_contradiction`
  claim route. No other route's decision may change, including for
  rows where psd fires. The Phase-16 route precedence
  (`out_of_diff > contract_contradiction > witnessed_behavior >
  external_fact > unwitnessed_behavior`) is unchanged.
- psd is the only relation promoted. The other five relations remain
  non-gating exactly as before (sle/dsc: semantic false-positive
  failures; pcd/cbv: recall failures; jfu: recall boundary — each
  only revisitable through new preregistered cycles).

## Baseline decision (frozen)

Baseline per-row decision is the `g2_contract_aware` gate outcome from
`eval/evidence_boundary_sim.py::simulate_finding` over the frozen
blocking-finding population (276 rows; the 414-record corpus,
fail-closed). Values: `BLOCK_SURVIVES` / `DOWNGRADE`.

## Promotion rule (frozen, role-blind)

The integrated decision equals the baseline decision, except:

> `BLOCK_EVIDENCE_BACKED` iff `route == "contract_contradiction"` AND
> `"pinned_sha_demoted_to_branch" ∈ relation_names(finding, fixture)`
> AND baseline decision is `DOWNGRADE`.

Everything else is mechanically identical to baseline. Roles are never
consulted by the rule; they score it.

## Frozen predictions (made before any 19B run)

Computed deterministically from the frozen corpus and recorded here as
the exact expected outcome of 19B. Any divergence is a **halt**, not a
finding to reconcile silently.

- population: **276** blocking rows
- baseline g2 aggregate: **145 `BLOCK_SURVIVES` / 131 `DOWNGRADE`**
  (by role: TP 111/54, control 27/50, extra 7/27)
- contract-route baseline: **77 `BLOCK_SURVIVES` / 48 `DOWNGRADE`**
- psd fires on **24** rows: all fixture `M2`, all role
  `true_positive_detection`, **0 controls, 0 extras**; g2 split
  5 `BLOCK_SURVIVES` / 19 `DOWNGRADE`
- of the 19 downgraded psd-fired rows: **1** on
  `contract_contradiction`, 12 on `external_fact`, 6 on
  `unwitnessed_behavior`
- **predicted promotion set: exactly 1 row** —
  `("stage-a-max", record 28, finding 0, fixture M2,
  .github/workflows/ai-review.yml, route contract_contradiction,
  g1 DOWNGRADE, g2 DOWNGRADE)`

## Accepted scope limitation (recorded up front)

The 18 psd-fired downgrades on non-contract routes **remain
downgraded** under this protocol. The route taxonomy confines psd's
blocking power to contract-route rows by design; extending evidence-
backed blocking to other routes is future preregistered work, not a
deviation. The preregistered outcome values boundary containment over
recall.

The new-control discipline applies to **new promotions only**.
The baseline still contains 27 baseline control blockers that survive
`g2_contract_aware`. A one-row psd success neither repairs those
historical false blockers nor authorizes GATING activation.

## 19B invariants (all mechanical, all halt on violation)

1. Population exactly 276; sources exactly `boundary.SOURCES`;
   oracle `117b4164e5446f50`.
2. Verifier identity fail-closed: `eval/v21_contract_relations.py`
   sha256 `bb0ebdeeb7fc80395626bf10d3e9ad1a730936ccf0ab7e719c43c1b
   5754b1b57`, merge `0631b0956f795ab1ee6d13f68b0c1cebe8a6d23b`.
   The verifier, routes, predicates, parser, fixtures, and oracle are
   called, never modified.
3. Zero-collateral: all rows outside the predicted promotion set keep
   their baseline decision **byte-identically** (275 rows).
4. Control discipline at decision level: zero
   `BLOCK_EVIDENCE_BACKED` on `control_blocker` and
   `positive_extra_blocker` rows.
5. Promotion set equals the frozen prediction exactly (1 row, as
   identified above).
6. Standing regression guards held: frozen five (C11/M13/C12/M12
   refused, M3 witnessed), M10 relation still FAILED, C10 standing
   near-miss.
7. The historical 18B/18D artifacts remain byte-for-byte unchanged.

## Halt conditions

Any of: population drift, verifier-identity drift, any collateral
decision change, any control/extra promotion, promotion-set
divergence from the frozen prediction, or guard violation. A halt is
resolved only by a reviewed amendment to this protocol (before 19B
publishes) or by recording the experiment as FAILED. Divergence is
never silently reconciled.

## 19B artifacts (named now, must not exist until 19B)

- `eval/evidence/v21-psd-promotion-eval-2026-09-23/RESULTS.md`
- `eval/evidence/v21-psd-promotion-eval-2026-09-23/psd-promotion-report.json`
  (published report bound by tests to live evaluator output exactly)

## Success criteria and meaning

Success = all invariants hold and outcomes match the frozen
predictions exactly. Success means psd is **eligible** as the first
evidence-backed blocker on the contract route for this oracle — a
measured, scoped integration result, not a correctness claim about any
subject (humility rule), and not a GATING-registry promotion (that
remains a separate, permanent, qualification-gated act).
