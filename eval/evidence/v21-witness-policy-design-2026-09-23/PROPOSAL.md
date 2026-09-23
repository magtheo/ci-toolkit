# Phase 21B — revised witness-policy proposal (design only)

**Status: DESIGN ONLY. No rule is adopted, no evaluator exists, no
run is authorized. This proposal responds to the Phase-21A review
disposition (neither variant approved; D2 deferred; D3 not accepted
for generalization). Nothing here executes until the revised rule,
recall costs, and validation plan have been reviewed and approved.**

## Design constraints from the 21A review

1. The 21A "qualified six" witness set was **not qualified**: only
   psd passed the unseen holdout (18D); five relations FAILED, two
   with control leakage. No rule may grant failed relations
   authority merely because they match the historical corpus.
2. Neither 21A variant is approvable as framed: loose grants a known
   FAILED relation witness authority; strict still grants the five
   FAILED relations authority and loses M10 without removing any
   additional false blocker.
3. The two M4 true-positive losses are **deferred, not accepted**;
   the dsc-P4 holdout loss is **not accepted for generalization**.
4. Corrected population language (now frozen in the merged 21A
   record): **44 bare survivors and 26 bare controls corpus-wide**;
   **22 non-contract bare survivors** including **11 non-contract
   bare controls**; R1′ addresses only the contract-route bare
   slice.

## The quantified trap this design avoids

Applying witness authority across ALL contract-route survivors with a
psd-only + predicate witness set — the naive "only psd is qualified"
reading — would fall **46 rows, 26 of them true positives**
(including 24 rows carried by the five FAILED relations' firings:
dsc 9, pcd 7, cbv 5, jfu 2, M10-family 1). A policy that consults
relations on non-bare rows must either grant FAILED relations
authority (rejected by review) or destroy recall (26 TPs). Therefore
the revised rule **never consults any relation on non-bare rows.**

## Witness tiers (design)

| tier | evidence | decision authority |
|---|---|---|
| T1 | closed-world predicates (Phase-15; M3 precedent) | block-preserving |
| T2 | psd (holdout PASS 5/5 · 0/5, 18D; integration 19A/19B) | block-preserving |
| T3 | the five holdout-FAILED relations | **advisory only — recorded, never decision-bearing** |
| T4 | the FAILED M10-family relation | regression evidence only; no role in any rule |

Preservation guarantees: the psd promotion row (stage-a-max r28) is
T2-witnessed and untouched; the psd qualification record
(`eval/evidence/v21-psd-qualification-closeout-2026-09-23/RECORD.json`)
remains frozen; T2 authority is exactly what 19A/19B measured — no
more, no less.

## Revised rule: R1′ (bare-scoped, relation-blind)

> A `g2_contract_aware` `BLOCK_SURVIVES` on the `contract_contradiction`
> route with **no evidence of any kind** — no T1 predicate, no
> relation firing of any tier — downgrades to `DOWNGRADE`.

R1′ is the **intersection of both 21A variants**: the same 22-row
fall set (15 controls: C12/C13/C16/C2/C3/C4/C8; 5 extras: M12/M13;
2 TPs: M4 ×2), with the loose/strict M10 divergence outside its scope
entirely (M10 rec55 carries a T4 firing — not bare — so R1′ keeps
it, without consulting or endorsing the FAILED relation).

**Authority invariant (the design's core):** R1′'s output is
byte-identical whether T3/T4 firings are present or redacted — R1′
gains nothing from failed relations and grants them nothing. Rows
with relation firings keep their blocks via the existing gates
(status quo), not via any new authority.

Frozen scope limits: the 22 non-contract bare survivors (11 bare
controls among them) are explicitly **out of scope**; the corpus-wide
witness question remains open and requires its own preregistration.

## Recall costs, addressed explicitly

- **M4 (2 rows: b1-low r44, stage-a-max r66)** — oracle-matching
  cross-file-verifiability/caveat findings with no covering relation.
  Resolution path **PC1**: an M4 relation through its own
  preregistered cycle (Phase-17-style design, binding pair discipline,
  unseen-holdout validation). Postcondition, mechanically checked:
  the bare fall set shrinks 22 → 20. Until PC1 completes, the M4
  losses remain deferred — R1′ is **not adoptable**.
- **dsc-P4 (holdout, bare contract-route positive)** — a genuine
  contradiction the FAILED dsc family cannot yet witness. Resolution
  path **PC2**: the dsc/sle first-principles redesign cycle producing
  a relation that fires on dsc-P4. Postcondition: the holdout fall
  set is 0. Alternative only by explicit human decision, scoped
  corpus-only. Until PC2, the dsc-P4 loss remains not accepted.

## Independent validation plan (frozen design, executed only after approval)

- **V1 — corpus execution**: exact reproduction of the then-current
  bare fall set; every untouched decision byte-identical; standing
  guards held (frozen five, M10 FAILED, C10 near-miss, oracle
  `117b4164e5446f50`); psd chain artifacts hash-unchanged.
- **V2 — holdout run**: fully predicted behavior (3 g2-survivors;
  dsc-C4/dsc-P2 kept; dsc-P4 witnessed post-PC2 → zero positive
  falls); any divergence halts.
- **V3 — authority invariants**: mechanical T3/T4 redaction-
  equivalence (V3 is what distinguishes this design from both 21A
  variants); tier table re-verified against the 18D report verdicts.
- **V4 — human acceptance gates** at PC1, PC2, and any execution PR;
  no GATING authorization, no deployed reviewer change, oracle-scoped
  humility throughout.

The three known relation-level holdout control leaks (sle-C3,
dsc-C1, dsc-C2) are not g2-survivors: R1′ does not address them and
must not be counted as progress on them — they belong to the
redesign cycle (PC2's own acceptance gate).
