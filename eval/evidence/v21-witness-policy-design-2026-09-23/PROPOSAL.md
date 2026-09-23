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
(24 relation-only rows: **23 from the five Phase-18D failures** —
dsc 9, pcd 7, cbv 5, jfu 2 — **plus 1 M10-family row**).

**Correction admitted (review finding):** the originally proposed
"bare scoping" does NOT escape this trap, because bare-ness is itself
defined by evidence presence. A bare-scope downgrade rule is
**evidence-presence-dependent by construction**: redacting T3/T4
firings turns non-bare rows into bare rows and expands the fall set
22 → 46. The redaction-equivalence invariant therefore **cannot
hold**, and R1′ is **relation-dependent, not relation-blind**. The
22-row ledger stands as an exploratory measurement only; R1′ is
**not adoptable** as specified.

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

## Revised rule: R1′ (bare-scoped, explicitly relation-dependent)

> A `g2_contract_aware` `BLOCK_SURVIVES` on the `contract_contradiction`
> route with **no evidence of any kind** — no T1 predicate, no
> relation firing of any tier — downgrades to `DOWNGRADE`.

R1′ is the **intersection of both 21A variants**: the same 22-row
fall set (15 controls: C12/C13/C16/C2/C3/C4/C8; 5 extras: M12/M13;
2 TPs: M4 ×2), with the loose/strict M10 divergence outside its fall
set (M10 rec55 carries a T4 firing — not bare — and is **kept by
that firing**, which is decision-bearing dependence on the FAILED
M10 relation; the design no longer calls this an endorsement, it
calls it what it is).

**The dependence, quantified (mechanically measured, test-pinned):**
redacting all T3/T4 firings expands the fall set **22 → 46**: the
24 additional rows are 23 carried by the five Phase-18D failures
(dsc 9, pcd 7, cbv 5, jfu 2) and 1 by the M10 family. None of the
24 carries a T1 predicate or a T2 psd firing — so **no independent
evidence predicate is derivable from existing validated evidence**;
preserving them requires newly qualified evidence or an explicit
human authority grant.

## Adoption paths (none taken by this design)

- **PA1** — qualify relations (or successor predicates) for
  **preservation authority** through preregistered holdout cycles: a
  new authority type, distinct from the Phase-19 admission authority.
- **PA2** — develop genuinely independent preservation evidence for
  the affected rows; same qualification burden; not derivable from
  current validated evidence (the 24 rows are predicate-less and
  psd-less by construction).
- **PA3** — an explicit human grant of relation-dependent
  preservation for specific tiers with recorded rationale; the 21A
  review declined this, and it remains the human's call.
- Until one of PA1/PA2/PA3 is chosen AND the PC1/PC2 cost paths
  below are resolved, **R1′ is non-adoptable** and the 22-row ledger
  remains exploratory.

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
- **V3 — relation-dependence accounting**: the redaction delta
  (22 → 46; 23 five-failure + 1 M10-family) is mechanically measured
  and test-pinned. The prose-only redaction-equivalence assertion is
  withdrawn: the invariant cannot hold for bare-scope rules. Any
  future preservation-authority claim must carry its own
  qualified-evidence proof, never a redaction assertion.
- **V4 — human acceptance gates** at PC1, PC2, and any execution PR;
  no GATING authorization, no deployed reviewer change, oracle-scoped
  humility throughout.

The three known relation-level holdout control leaks (sle-C3,
dsc-C1, dsc-C2) are not g2-survivors: R1′ does not address them and
must not be counted as progress on them — they belong to the
redesign cycle (PC2's own acceptance gate).
