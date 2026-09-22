# v2.1 claim-route replay result

Method: `python3 eval/v21_routes_replay.py` under
`PROTOCOL.md` (rules fixed before recording). Oracle `117b4164e5446f50`
unchanged. Inputs: the frozen 414-record / 276-blocker Phase-09
population plus the five sha-linked regression cases. Zero provider
calls.

## Gate-level result

| role | quote-only | closed-world (Phase 15) | route-typed |
|---|---:|---:|---:|
| control blockers | 27 / 77 | 0 / 77 | **0 / 77** |
| oracle-matching detections | 111 / 165 | 50 / 165 | **50 / 165** |
| positive extra blockers | 7 / 34 | 2 / 34 | 2 / 34 |

The preregistered identity held **per row, fail-closed**: route-typed
admission equals Phase-15 closed-world admission exactly. Route typing
explains refusals; it does not widen them.

## Route × role decomposition (admitted / total)

| route | controls | oracle-matching TPs | extra blockers |
|---|---:|---:|---:|
| `contract_contradiction` | 0 / 35 | 29 / 68 | 1 / 22 |
| `witnessed_behavior` | 0 / 0 | **21 / 23** | 1 / 5 |
| `external_fact` | 0 / 14 | 0 / 45 | 0 / 7 |
| `unwitnessed_behavior` | 0 / 28 | 0 / 29 | 0 / 0 |
| `out_of_diff` | 0 / 0 | 0 / 0 | 0 / 0 |

Reading:

- **Registry-backed admission is the existence proof, not the
  `witnessed_behavior` row by itself.** Across all routes, every
  admitted row still has a Phase-15 structural witness: 50/165
  oracle-matching TPs with 0/77 control admissions. Within the
  precedence-conditioned non-contract `witnessed_behavior` route,
  21/23 TPs are admitted and no controls are assigned to that route.
  Because contract-shaped rows take precedence, the route-local 0/0
  control denominator is **not** a standalone precision estimate of
  the witness registry.
- **`contract_contradiction` is the biggest recoverable gap**: 39
  oracle-matching TPs carry the right claim shape and a quote but die
  for lack of a relation verifier (only one exists today:
  `parsed_date_vs_mtime`, which admits M3). C11 is the mirrored
  control: the same route correctly refuses the fabricated
  contradiction because no verifier exists. Growing this registry is
  exactly where over-triggering risk lives — every addition must be
  pair-validated (positives + near-miss controls), never ad hoc.
- **`external_fact` is the largest single bucket (45 TPs) and is
  unverifiable offline by construction.** The same route refuses all
  14 controls that land in it — the M13 dilemma quantified: offline
  rules cannot separate honest external-fact detections from
  fabricated extrapolation. Recovery requires pinned external facts
  plus mechanically bounded consequence checks; that is research
  infrastructure, not a rubric tweak.
- **`unwitnessed_behavior` (29 TPs)** needs generic static/execution
  witnesses; **`out_of_diff` never occurs** in Phase-09 v1 blockers —
  the route earns its keep only on v2 records (C12).
- 2 `witnessed_behavior` TPs were refused by the **quote gate**, not
  the route: a v1 comment-extraction artifact (upper-bound limit, as
  in Phase 09).

## Frozen five-case projection

| case | route | outcome | reason |
|---|---|---|---|
| C11 fabricated contradiction | `contract_contradiction` | refused | no registered relation verifier |
| M3 context-only quote | `contract_contradiction` | **admitted** | relation witness `parsed_date_vs_mtime` |
| M13 external extrapolation | `external_fact` | refused | external route offline-refused (pinned fact + bounded consequence required) |
| C12 honest uncertainty | `contract_contradiction` | refused | quote gate: machine downgrade `BLOCKING_EVIDENCE_INSUFFICIENT` |
| M12 non-contiguous quote | `witnessed_behavior` | refused | quote gate: machine downgrade — the witness agrees the defect is real, but the invalid evidence quote keeps it non-blocking |

All five match the adjudicated ground truth, each now with a stated
mechanical reason.

## Conclusion

The bottleneck is confirmed and now located per claim class: the
route layer adds no recall by itself — **verification infrastructure
per route is the only recall lever**. The existing registry shows that
mechanically witnessed admissions can preserve meaningful recall
without historical control leakage, while the route decomposition
shows where that verifier coverage is missing.

Research priority is **feasibility/risk ordered, not raw-yield
ordered**: (1) pair-validated contract relation verifiers (39 refused
TPs, C11 as a standing near-miss control, fully offline-testable);
(2) external-fact pinning with bounded-consequence checks (45 refused
TPs — the larger raw bucket — but M13 shows this requires new pinned
fact/consequence infrastructure and ultimately a live trial);
(3) broader static witnesses (29 refused TPs).
No threshold, promotion, or implementation is authorized by this
study.
