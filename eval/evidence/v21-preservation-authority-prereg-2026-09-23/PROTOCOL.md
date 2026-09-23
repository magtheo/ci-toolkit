# Phase 22A — preservation-authority qualification: preregistration

**Status: preregistration only. No candidate evidence exists, no
qualification run has been performed, and no reduction rule is
adopted. The 22-row exploratory ledger (Phase 21B) remains frozen
exactly as it is. This phase freezes what it would take for ANY
evidence to earn preservation authority — before any candidate is
designed.**

## The two authorities (frozen separation)

- **Admission authority** — evidence sustaining a NEW block. Measured
  path exists: psd (holdout PASS 18D; integration 19A/19B). psd
  remains the only admission-authority evidence.
- **Preservation authority** — evidence keeping an EXISTING block
  alive under a bare-scope downgrade rule. **No evidence currently
  holds it.** The five Phase-18D-failed relations and the M10 family
  carry the 24 affected true positives only inside the exploratory,
  non-adoptable 22-row measurement; that is not authority.

Preservation authority, once granted to a candidate, does exactly one
thing: exempts candidate-firing rows from future bare-scope downgrade
rules. It never creates a block, never admits, never gates, and never
touches deployed reviewer behavior.

## Affected populations (frozen, mechanically re-derived)

- **P-RELCARRIED** — 24 contract-route g2-survivor true positives
  carried only by T3/T4 firings: dsc 9, pcd 7, cbv 5, jfu 2,
  M10-family 1. Protected today only inside the non-adoptable
  exploratory measurement.
- **P-M4** — the 2 bare contract-route M4 true positives
  (stage-a-max r66, b1-low r44). Unprotected by anything; fall under
  any bare rule. (M4 b1-low r29 is a survivor on the unwitnessed
  route — explicitly NOT in this population and untouched by bare
  rules.)
- **P-DSC-P4** — the holdout dsc-P4 positive (bare contract route):
  falls under any bare rule extended to the holdout.
- **Anti-targets** — the 26 bare controls corpus-wide (11 on
  non-contract routes): candidates firing on ANY control row fail
  outright. Protecting a control is failure, not nuance.

## Qualification gates (frozen before any candidate exists)

- **QG1 — corpus pair discipline**: a candidate fires on 100% of its
  declared target positives and on ZERO control rows corpus-wide.
  Any control firing anywhere = FAILED, auto-excluded (the Phase-17
  binding rule, unchanged).
- **QG2 — holdout**: candidate fires on zero holdout controls (a dsc′
  or sle′ redesign must NOT fire on dsc-C1/C2 or sle-C3). Positive
  firings are recorded and scoped to declared targets. Where a
  candidate was designed with knowledge of holdout rows (dsc′ knows
  dsc-P4/C1/C2), its holdout PASS is **remediation validation, not
  out-of-sample discovery** — recorded as such in the qualification
  record.
- **QG3 — independence**: a candidate is NEW evidence — not a
  re-label, re-export, or wrapper of any T3/T4 relation or any
  function of the frozen Phase-17 module (`bb0ebdee…` stays
  byte-frozen; candidates live in new modules). Mechanical: distinct
  module, distinct entry point, no delegation to the frozen module's
  relation functions.
- **QG4 — standing guards**: frozen five (C11/M13/C12/M12 refused,
  M3 witnessed), M10 relation still FAILED, C10 standing near-miss,
  oracle `117b4164e5446f50` — all held at qualification time.
- **QG5 — human acceptance**: a qualification record is published,
  human-reviewed, and merged before any adoption PR. Agents never
  grant authority, not even a passed candidate.

## Candidate slate (frozen order; sketches only — no patterns frozen here)

1. **m4rel** — "unsubstantiated absolute docstring claim" family for
   M4 (targets: P-M4; family context: 7 M4 true positives corpus,
   3 g2-survivors; adjacency to declare: the 4 M4 positive-extra
   scope-violation rows, which are non-targets — candidate firings on
   extras are recorded and scope-reviewed, not auto-FAIL, but
   adoption scoping must address them). Cleanest first candidate: no
   failed-relation baggage.
2. **dsc′** — remediation redesign of doc-self-contradiction
   (targets: the 9 P-RELCARRIED dsc rows + holdout dsc-P4; must not
   fire on dsc-C1/C2). Carries PC2. In-sample caveat per QG2.
3. **sle′** — remediation for the sle-C3 leak (targets: the 2
   P-RELCARRIED sle-family rows are pcd/cbv/jfu-adjacent; sle′'s
   declared scope is the redesign contract, recorded at its own
   preregistration).
4. **pcd′, cbv′, jfu′** — recall-focused successors for the
   remaining P-RELCARRIED rows (7/5/2).
5. **m10′** — lowest priority; successor must clear the C10
   standing near-miss to qualify.

Failure at any gate is recorded as evidence (like the FAILED M10
relation) and the candidate is auto-excluded; it is never tuned
post hoc against the same gates.

## Cost ledger (unchanged, restated)

The two M4 losses and the dsc-P4 holdout loss remain unresolved until
(m1) qualifying candidates exist under these gates, AND (m2) a
separately reviewed adoption preregistration is approved. The psd
qualification is preserved untouched throughout.

## Non-goals

No reduction-rule adoption; no downgrade execution; no GATING
activation; no deployed reviewer change; no edits to the frozen
Phase-17 module, fixtures, routes, parser, or oracle; the 21A/21B
records remain frozen as exploratory evidence.

## Future-phase artifacts (named now, must not exist until their own phases)

- `eval/v21_m4_relation.py` — candidate module (22B+)
- `eval/evidence/v21-m4-relation-*/` — candidate protocol/results
- `eval/evidence/v21-preservation-qualification-*/` — qualification records
