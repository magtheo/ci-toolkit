# Iteration-4 campaign results (2026-09-15) — REVERT

One governed campaign per freeze.json rev 2. Authorization received before
call 1; pre-run projection $6.12 <= $7.00 cap. Campaign **COMPLETED**:
360 invocations, 614 logical model stages (haiku 300, sonnet 314; <= 720),
actual spend **$4.3119** <= $7.00.

## Mechanical application of frozen criteria (design §4)

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | zero GATING (C4/C5/C7), both profiles | **FAIL** | C7 violated on both profiles |
| 2 | Deviation-6 floors | **FAIL** | haiku 0/90 (floor 51), sonnet 0/90 (floor 66) |
| 3 | sonnet M17 = 5/5 | **FAIL** | 0/5 |
| 4 | FB caps | satisfied (vacuous) | final FBs 0 ≤ caps; mechanism blocked nothing final |
| 5 | family separation + pair integrity | **FAIL** | all five confirmed families failed to demonstrate separation (final positive detection 0); pair integrity: no violations, no promotable positives — does not rescue the criterion |
| 6 | causal non-vacuity | **FAIL** | zero refutations: 254/254 verifier outputs rejected |

**KEEP requires all six → verdict: REVERT** (full mechanism revert: engine
pass-2 policy/prompt, verifier parsing; trace stays inert). No partial
keeps, no post-hoc criterion editing (frozen §4).

## Failure mode

Verifier protocol/parsing interaction. Despite the bare-JSON-only protocol,
both profiles wrapped verdict JSON in code fences in **100%** of pass-2
calls (haiku 120/120, sonnet 134/134). The deliberately strict parser (#59)
rejected every output → semantic verification failure → INCONCLUSIVE per
invocation → no keep/remove applied → final reviewer blocked nothing
(0 ISSUES_FOUND in 360 final results) → detection 0 everywhere.

Non-gating telemetry (explicitly NOT the frozen gate): pass-1 blocking was
present (haiku 120, sonnet 134 ISSUES_FOUND invocations); pass-1-only floor
performance is a question for the next design cycle.

## Provenance

- Subject d1a2ef1 (ancestor of executed harness head e922545; reviewer
  blobs verified identical pre-launch), oracle cb6870c5, corpus 72035a00
  (36), rubric 415d8a38, protocol 1bbacabc, trace v2 (12-key schema
  verified on all 360 lines).
- raw/ is byte-frozen (SHA256SUMS); raw/haiku-run.log and
  raw/sonnet-run.log are the console transcripts; per-call provider costs
  recorded in traces are the spend evidence.
