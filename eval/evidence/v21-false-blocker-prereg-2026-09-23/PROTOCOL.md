# Phase 21A — false-blocker reduction: preregistration

**Status: preregistration only. No reduction evaluator exists; no run
has been performed. The rule family and every cost ledger below are
frozen. Neither variant has been approved for 21B execution. A new,
reviewed authorization is required.**

## Problem statement (frozen)

The v2.1 blocking boundary admits **34 false blockers** that survive
`g2_contract_aware` on anchored quotes alone: **27** on
`control_blocker` rows and **7** on `positive_extra_blocker` rows
(M12/M13 extras). All 34 survive `g1_strict_quote` as well — the
gates never consult the route/predicate/relation layer that Phases
15–17 built. The unseen holdout qualified **only psd**; the other five
Phase-17 pair-surviving relations FAILED generalization.

Measured separability surface over the 145 g2-survivors (276-row
frozen corpus):

| survivor class | TP | control | extra |
|---|---:|---:|---:|
| Phase-17 pair-surviving relations (psd bucket excluded; five failed holdout) | 34 | 0 | 0 |
| psd-relation-verified | 5 | 0 | 0 |
| FAILED-relation-verified (M10 family) | 9 | 1 (C10, external route) | 0 |
| witnessed (closed-world predicate, no relation) | 50 | 0 | 2 |
| bare, contract route | 2 | 15 | 5 |
| bare, external_fact route | 10 | 4 | 0 |
| bare, unwitnessed route | 1 | 7 | 0 |

Every control false blocker except C10 is **bare**; C10 is kept alive
by the deliberately FAILED M10 relation (standing near-miss evidence)
on a non-contract route. Bare TPs are concentrated on
`external_fact` (10) — findings requiring external platform
semantics, where the model is often right — which is exactly why a
corpus-wide witness requirement is too blunt.

## Rule family (frozen)

**R1 — witness-required contract-route blocking.** A
`g2_contract_aware` `BLOCK_SURVIVES` on the `contract_contradiction`
route downgrades to `DOWNGRADE` unless the row carries a witness:

- **R1-loose**: witness = any closed-world predicate **or** any
  Phase-17 relation firing (including the FAILED M10-family
  relation).
- **R1-strict**: witness = any closed-world predicate **or** a firing
  from the six Phase-17 pair-surviving relations (the FAILED M10
  relation does not count). **This is not a qualified witness set:**
  five of those six FAILED the Phase-18D unseen holdout; only psd
  qualified. Both variants are exploratory measurements, not safe
  blocker-authority designs.

No other row changes. R1 never touches non-survivors, non-contract
routes, or the psd promotion row (psd-relation-verified → witnessed).

## Frozen ledgers (derived now, before any 21B run)

**R1-loose — 22 rows fall** (all on the contract route, all bare):
controls **15** (C12 b1-high r31, C12 b1-low r16, C12 stage-a-max
r75, C13 b1-high r32, C13 stage-a-high r4, C13 stage-a-max r40, C16
stage-a-max r7, C16 stage-a-max r43, C2 stage-a-max r46, C3 b1-high
r6, C3 b1-low r6, C3 stage-a-max r47, C3 stage-a-max r83 f1, C4
stage-a-high r48, C8 stage-a-high r16); extras **5** (M12 stage-a-max
r21 f1, M13 stage-a-high r22, M13 stage-a-high r58, M13 stage-a-max
r22, M13 stage-a-max r58); **TP cost: 2** (M4 b1-low r44, M4
stage-a-max r66 — no relation covers M4's claim type yet). Survivors:
145 → 123 (TP 111→109, control 27→12, extra 7→2).

**R1-strict — the same 22 plus 1**: M10 stage-a-max r55 (TP, kept
alive only by the FAILED relation). Survivors: 145 → 122 (TP
111→108).

**Holdout (60 fixtures, both variants identical)**: exactly 3 rows
survive g2 — dsc-C4 (REFUSES, unwitnessed route: kept), dsc-P2
(ADMITS, unwitnessed route, dsc-witnessed: kept), dsc-P4 (ADMITS,
contract route, bare: **falls**). R1 costs the holdout one
dsc-family positive. The three known relation-level holdout control
leaks (sle-C3, dsc-C1, dsc-C2) are not g2-survivors — R1 does not
address them; they remain the dsc/sle redesign problem.

**Untouched by both variants**: the psd promotion row
(stage-a-max r28, psd-witnessed), C10 (external route, standing
near-miss evidence), all **22 non-contract bare survivors** (including
**11 non-contract bare controls**), and every non-survivor row. There
are **44 bare survivors and 26 bare controls corpus-wide**, not on
non-contract routes alone; the corpus-wide witness question is
explicitly NOT resolved by this experiment.

## Decision points (review disposition: no 21B authorization)

- **D1 — variant: neither approved for blocker authority.** R1-loose
  allows a known FAILED relation to serve as a witness; R1-strict
  merely excludes M10 while retaining five other holdout-FAILED
  relations and losing an additional M10 TP without reducing any
  observed false blockers. Both exact ledgers remain frozen as
  exploratory evidence, not an approved execution rule.
- **D2 — M4 cost: defer.** The two named M4 TPs are oracle-matching
  cross-file-verifiability/caveat findings not covered by an in-diff
  relation. Do not count their loss as harmless; a future protocol
  must explicitly address them or transparently request acceptance.
- **D3 — dsc-P4 holdout cost: not accepted for generalization.**
  P4 is a directly contradictory in-diff document positive; R1 drops
  it. Corpus-only scope cannot erase the observed holdout loss.
  Preserve P4 as evidence and require a newly reviewed rule/holdout
  before broader claims.

**No variant selected; do not execute 21B under this preregistration.**
A future reviewed preregistration may design a narrower witness policy
or explicitly accept costs; never treat this exploratory ledger as
promotion or GATING authorization.

## 21B execution contract

Only after explicit, separately reviewed authorization, an approved
variant could run mechanically and must: reproduce its frozen
ledger **exactly** (same rows, same roles); leave every untouched
decision byte-identical; hold all standing guards (frozen five, M10
FAILED, C10 near-miss, oracle `117b4164e5446f50`); leave the psd
promotion row and all historical artifacts (18B/18D/19B reports,
19A contract, 20 closeout record) hash-unchanged. Any divergence is a
**halt**, resolvable only by reviewed amendment — and is never
silently reconciled.

## 21B artifacts (named now, must not exist until 21B)

- `eval/evidence/v21-false-blocker-eval-2026-09-23/RESULTS.md`
- `eval/evidence/v21-false-blocker-eval-2026-09-23/reduction-report.json`
  (SHA-pinned, test-bound to live evaluator output exactly)

## Scope and humility

R1 is an exploratory measurement on the frozen corpus boundary. It
changes no deployed reviewer behavior and authorizes nothing, including
21B execution. The corpus-wide witness question (**26 bare controls
and 13 bare TPs in total**, of which 11 controls and 11 TPs are on
non-contract routes), the sle/dsc false-positive redesign, the M4
relation, and any route extension all require separate future
preregistrations.
