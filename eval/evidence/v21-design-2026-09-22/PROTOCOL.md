# Offline v2.1 design replay protocol

This is a **design-study protocol**, not a promotion preregistration
and not a claim that any candidate is ready to implement. It fixes the
inputs and measures reported by `eval/v21_replay.py`; `REPLAY.md`
contains the deterministic result.

## Inputs

- all 414 records from the frozen Phase-09 sources enforced by
  `eval/evidence_boundary_sim.py` (276 blocking findings);
- the five sha-linked post-trial regression cases in
  `eval/evidence/v2-declaration-regression-freeze-2026-09-22/`;
- oracle content identity `117b4164e5446f50`.

No provider call, corpus mutation, or reviewer behavior change is
permitted by this study.

## Candidates compared

1. **quote_only**: existing Phase-09 G1 quoted-span admission.
2. **closed_world_predicates**: quote_only plus a matching,
   independently checkable patch predicate from the deliberately
   narrow registry described in `DESIGN.md`.

The registry is a lower-bound safety experiment, not a proposed
universal semantic verifier.

## Required reported measures

- admissions / totals for control blockers, oracle-matching
  true-positive detections, and positive extra blockers;
- per-case admissions and matching predicates for C11, M3, M13, C12,
  and M12;
- whether the oracle identity moved (it must not).

No threshold selects a winner, permits implementation, authorizes a
provider trial, or promotes the v2 boundary. A later v2.1
implementation/preregistration must explicitly choose a mechanism and
name every frozen regression expectation it intentionally changes.
