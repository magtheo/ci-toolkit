# T1.3 iteration 1 — speculative-consequence grounding rule (2026-09-08)

## Mechanism definition (frozen before measurement)

- **Layer** (per the T1.3 candidate layers): (a) rubric / reasoning
  contract. Wording only — no engine, parser, schema, or
  representation change.
- **Rule**: a blocking finding must identify a concrete defect or
  violated invariant supported by evidence available in the supplied
  review input, and the claimed impact must follow from that
  evidence. Hypothetical harm depending on unseen code behavior, an
  unestablished external actor/compromise, or future misuse is
  advisory at most. Conditional reasoning is NOT disqualifying (a
  visible injection path still blocks); the unsupported premise is.
- **Representation-neutral by design**: "supplied review input", not
  "diff-visible" — the rule must survive future base-context
  retrieval enrichments (layer (c)).
- **Target family**: `speculative-consequence` (frozen T1.1 family:
  blocking grounded in a conditional harm chain about external
  actors/code rather than a present supported defect).

## Measured basis (frozen #36, diagnostic, NOT BINDING)

- speculative-consequence is the largest emitted family: 115/324
  false blockers (haiku 63, sonnet 52);
- 5/6 of sonnet's C7 GATING false blockers;
- dominant haiku family; the C7-pair mechanism on the gating surface.

## Measurement protocol (Phase 14 — spend-authorized separately)

Full corpus, N=5, BOTH governed profiles (haiku-4.5 + sonnet-4.5),
new subject (this rubric) against the current oracle
`1ef8dc90badc27bd`. Comparison axes (kept separate per Deviation 6):

1. **Sensitivity**: every positive meets the Deviation 6 pre-change
   floor on both profiles (haiku 51/90, sonnet 66/90; per-positive
   values in `track1-oracle-repair4-2026-09-07/witness-replay.json`)
   — hold or improve.
2. **Discrimination/GATING**: the run itself must independently
   satisfy the applicable criteria (zero GATING violations, control
   FB behavior per family) — C7 cleanliness is the open gating
   question this mechanism partially addresses (5/6 sonnet C7
   blockers were speculative-consequence).

Keep/revert decision (Phase 15) follows the T1.3 loop: invariants
hold → keep; otherwise revert and freeze the negative result.

## Non-effects

- No eval-semantics change (oracle `1ef8dc90badc27bd` unchanged —
  the rubric is subject bytes, not oracle bytes);
- no parser/labeling change: the Haiku C7 label-mismatch mechanism
  is deliberately NOT addressed here (deferred design review —
  generation-time consistency checkpoint or structured output);
- this PR alone proves nothing about behavior; the rule earns or
  loses its place only at Phase 14 measurement.
