# Phase 23A — PC2 disposition (UNRESOLVED — operator decision required)

**Status: decision preparation only.** This document compares the
three resolution paths for PC2, states exactly what each requires,
and **does not select one**. No path is adopted, executed, or
assumed approved. The combined-policy adoption design
(`ADOPTION-DESIGN.md`) is written so that its gates are checkable
under **any** of the three dispositions.

## The question

The remaining holdout recall cost of a future bare-scope reduction is
**dsc-P4**. What is dispositioned is not a row on the qualification
corpus: it is the holdout-side consequence of extending that
reduction to holdout material.

What the frozen records establish (all mechanically verifiable;
see `COMBINED-LEDGER.json` → `observed_facts`):

- **18A** (frozen report, `generalization-report.json`): the dsc-P4
  oracle probe was **not admitted** (`admitted: false`) and the dsc
  relation **did not fire** on it (`fired_relations: []`).
- **18D** (`generalization-report-18d.json`): the dsc family
  **FAILED** generalization — it missed dsc-P3/P4/P5 and leaked
  dsc-C1/C2 controls (`GENERALIZATION_FAIL`).
- **21B** (frozen design, `POLICY_DESIGN.json` / `PROPOSAL.md`):
  dsc-P4 is the predicted **bare contract-route positive** on the
  holdout — a genuine contradiction the failed dsc family cannot
  witness. The 21B holdout validation run (V2: 3 predicted g2
  survivors; dsc-C4 and dsc-P2 kept; dsc-P4 bare) was **never
  executed** and is not executed by this phase.

Because the dsc relation is qualification-FAILED, its firing (even
where it occurs) is **not qualified preservation evidence**, and the
accepted `m4rel` grant does not cover dsc-P4 (`m4rel.covers` is
claim-bound to the M4 shape; zero holdout or corpus control/extra
preservation is in scope). A bare-scope reduction extended to the
holdout would therefore remove dsc-P4's true-positive block unless
one of the paths below is taken.

## Path A — Accept the recall cost

- **What is lost, exactly:** the blocking decision for dsc-P4 — one
  holdout positive (a genuine doc-contract contradiction) — in any
  context where the reduction applies. Today dsc-P4 is additionally
  an 18A detection miss (not admitted, dsc did not fire), so the
  acceptance also forecloses recovering it later without reopening
  the disposition.
- **Intended population:** every dsc-P4-like case — genuine
  contradictions whose only potential witness sources are
  qualification-failed relations or not-yet-existing successors.
  The cost is not "one fixture"; it is the class it anchors.
- **Safety implications:** no control or extra is endangered by the
  acceptance itself (0/77 corpus controls, 0/30 existing-holdout
  controls are untouched by preservation questions). The risk is
  concentrated entirely in recall, and it is permanent until
  revisited: acceptance is recorded in the adoption preregistration
  and binds the combined policy.
- **Evidence requirements:** the adoption preregistration must state
  the acceptance explicitly, scope it (which populations), and carry
  the exact ledger row. No new qualification evidence is required —
  that is precisely its weakness.
- **Complexity:** lowest. No new cycles.
- **What it can legitimately establish:** only that the *human*
  has accepted a specific, bounded recall loss. It can never be
  cited as preservation evidence. **An explicit human risk acceptance is a scope decision, not a qualified preservation witness** — it must never appear in any grant registry, evidence
  tier, or runtime policy input.
- **Exact authorization required:** a recorded human risk
  acceptance, scoped and rationale-bearing, inside the adoption
  preregistration review.

## Path B — Qualify dsc′ first

- **Work required, under the frozen 22A framework:**
  1. A first-principles dsc′ candidate that remediates the known
     **dsc-C1/C2 control leaks** and the P3/P4/P5 misses — not a
     re-tune of the failed relation.
  2. Candidate-specific preregistration on the 22A pattern: frozen
     targets/contract, near-miss paired controls, thresholds frozen
     before execution, **fresh, independently authored holdout** for
     any generalized-authority claim.
  3. Measured qualification (N=5, ≥4/5, paired control clean, zero
     GATING regressions), executed once with the same
     execution-discipline rules as 22D.
  4. A **separate preservation-authority decision** (QG5-shaped):
     qualification PASS is scoped to the oracle and never implies
     authority; the grant is its own human act.
- **Recall cost if it succeeds:** holdout fall set 0 (dsc-P4
  witnessed). **If it fails:** PC2 returns, unresolved, with Path A
  or C as the remaining options — a failed cycle consumes effort but
  grants nothing.
- **Safety implications:** strongest. Authority arrives only through
  measured, pair-disciplined evidence, and the control-leak history
  (dsc-C1/C2) is exactly the failure mode the 22A gates exist to
  catch.
- **Evidence requirements:** highest — a full preregistered cycle
  comparable to 22B→22D. dsc-P4 itself is **burned**: it is known
  holdout material and may not serve as a qualification target; the
  cycle must prove the capability on fresh material.
- **Complexity:** highest; multi-phase effort before any adoption.
- **What it can legitimately establish:** a qualified preservation
  (or admission, if separately qualified) witness for the dsc-P4
  class — the only path that produces *evidence* rather than scope
  language.
- **Exact authorization required:** approval of the dsc′
  preregistration (plan-level), then an execution authorization for
  its qualification, then a separate QG5-style authority grant. No
  step follows from the previous one automatically.

## Path C — Limit the reduction's scope

Two sub-shapes, with very different legitimacy:

- **C1 — Operational/rollout boundary:** the reduction applies only
  to decisions inside a legitimately defined production boundary
  (e.g., records produced by a specific pipeline), which happens not
  to include holdout-context evaluation. This is **legitimate as an
  operational rollout scope** — but it does not resolve PC2; it
  **defers** it. The adoption documents must label it as deferment,
  never as evidence that dsc-P4 is safe.
- **C2 — Structural boundary tuned to exclude dsc-P4:** any boundary
  (feature threshold, shape rule, vocabulary condition) constructed
  so that dsc-P4 falls outside it is a **disguised holdout exception** and is rejected. Runtime policy may not use fixture
  IDs, oracle roles, hidden labels, or known holdout membership — a
  boundary that quietly encodes the same information is the same
  violation wearing a rule's clothing. Demonstration burden for any
  C-proposal: prove the boundary is derived from generalizable input
  properties and state what it would do on unseen material.
- **Recall cost:** 0 *within scope*; the holdout question is
  inherited unresolved by every future scope extension.
- **Safety implications:** neutral-to-positive (nothing new
  endangered), but the deferral compounds: each future extension
  re-opens PC2.
- **Evidence requirements:** for C1, a precise, reviewable
  boundary definition plus the deferral label; for C2, the
  legitimacy demonstration — which, done honestly, tends to collapse
  into Path B (a real input-property capability) or Path A
  (acceptance).
- **Complexity:** low for C1; deceptive for C2.
- **What it can legitimately establish:** an operational rollout
  scope. It cannot establish that dsc-P4's block survives any
  reduction — only that this reduction does not reach it **yet**.
- **Exact authorization required:** for C1, the boundary definition
  reviewed and accepted as *deferment* in the adoption
  preregistration; C2 shapes are out of bounds absent a Path-B-grade
  evidence story.

## Decision table

| | A — accept cost | B — qualify dsc′ first | C — scope boundary |
| --- | --- | --- | --- |
| Recall effect on dsc-P4 class | permanent loss, human-accepted | recovered if cycle PASSes | deferred; unresolved at each extension |
| Control/extra safety | unaffected | strengthened by new gates | unaffected |
| New evidence produced | none | qualified witness (only path that does) | none |
| Complexity | lowest | highest (multi-phase) | low (C1) / deceptive (C2) |
| Legitimate claim | scope acceptance only | qualified preservation for the class | operational rollout scope only |
| Failure mode to guard | acceptance silently treated as evidence | burned fixture reused; holdout not independent | boundary encodes holdout membership |
| Exact authorization | recorded human risk acceptance in adoption prereg | prereg approval → execution authorization → separate authority grant | boundary definition accepted as explicit deferment |

## Disposition

**UNRESOLVED by design.** The operator selects exactly one path (or
an explicit combination, e.g., B now with C1 as interim rollout
scope) at the adoption preregistration review. Until then:

- the adoption design treats holdout-extension effects as
  counterfactuals only;
- even after selecting PC2, the separate V2 policy decision about
  decision-bearing *presence* of failed-relation/M10 firings across
  the 24 relation-carried TPs remains subject to explicit human
  disposition. This is not a preservation-authority grant;
- no execution, no reduction implementation, no new holdout run, and
  no authority change occurs;
- the 21B rule holds: *until PC2 is dispositioned, the dsc-P4 loss
  is not accepted*.
