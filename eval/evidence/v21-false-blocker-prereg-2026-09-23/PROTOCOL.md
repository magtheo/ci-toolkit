# Phase 21A — false-blocker reduction: preregistration

**Status: preregistration only. No reduction evaluator exists; no run
has been performed. The rule family and every cost ledger below are
frozen; 21B executes the human-approved variant verbatim.**

## Problem statement (frozen)

The v2.1 blocking boundary admits **34 false blockers** that survive
`g2_contract_aware` on anchored quotes alone: **27** on
`control_blocker` rows and **7** on `positive_extra_blocker` rows
(M12/M13 extras). All 34 survive `g1_strict_quote` as well — the
gates never consult the route/predicate/relation layer that Phases
15–17 built and the holdout qualified.

Measured separability surface over the 145 g2-survivors (276-row
frozen corpus):

| survivor class | TP | control | extra |
|---|---:|---:|---:|
| qualified-relation-verified (six) | 34 | 0 | 0 |
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
- **R1-strict**: witness = any closed-world predicate **or** a
  qualified six-relation firing (FAILED relation does not count).

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
near-miss evidence), all 44 non-contract bare survivors (26
non-contract controls stay — the corpus-wide witness question is
explicitly NOT resolved by this experiment), and every
non-survivor row.

## Decision points (human adjudication at this PR's review)

- **D1 — variant**: loose (keeps M10 TP; FAILED relation counts as
  witness) vs strict (drops M10 TP; cleaner witness semantics).
- **D2 — M4 cost**: accept the 2 named M4 TP downgrades, or defer
  R1 until an M4 relation exists (its own preregistered cycle).
- **D3 — holdout cost**: accept the dsc-P4 downgrade (the dsc family
  already FAILED generalization), or scope the reduction's claimed
  validity to the corpus oracle with dsc-P4 recorded as a known,
  accepted cost.

## 21B execution contract

The approved variant runs mechanically and must: reproduce its frozen
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

R1 is a measurement experiment on the frozen corpus boundary. It
changes no deployed reviewer behavior and authorizes nothing. The
corpus-wide witness question (26 non-contract bare controls vs 13
bare TPs), the sle/dsc false-positive redesign, the M4 relation, and
any route extension all remain separate future preregistrations.
