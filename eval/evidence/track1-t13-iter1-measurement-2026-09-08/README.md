# T1.3 iteration 1 measurement — speculative-consequence grounding rule (2026-09-08)

## STATUS: MEASURED — DISCRIMINATION DECISIVELY IMPROVED; SENSITIVITY
## FLOOR VIOLATED ON ONE POSITIVE (sonnet M17 5→0). T1.2 REMAINS
## INCOMPLETE. Phase 15 (keep/revert) pending — this bundle makes no
## decision.

## Headline (vs frozen #36 diagnostic and Deviation 6 floors)

| | haiku | sonnet |
|---|---|---|
| GATING violations | **NONE — C4/C5/C7 all clean** | **NONE — C4/C5/C7 all clean** |
| detection hits (floor) | 52/90 (51) ✓ hold | 61/90 (66) ✗ **−5, all M17** |
| per-positive regressions | none | **M17: 0/5 vs floor 5/5** |
| control false blockers | 78 (was 90) | 112 (was 135) |
| false-clears (CLEAR/INCONCLUSIVE) | 30/90 (was 29) | 20/90 (was 15) |
| pair-integrity failures | M1 M2 M8 M10 (was 6) | M2 M8 M9 M14 (was 2) |
| INCONCLUSIVE runs | 7 (all JSON decode failure) | 3 (all JSON decode failure) |

**First run ever with zero GATING violations on both profiles.**
Sonnet's C7 speculative blockers (6/6 in #36) are gone; haiku's C7
labeling-protocol failure did not recur.

## The floor violation (Phase 15 input)

**M17 (absolute-consistency family), sonnet: 0/5 vs floor 5/5.**
Diagnosis (run-detail verified): not matcher, not parser — sonnet
answered CLEAR on all five runs, emitting only documentation-
completeness advisories (TTL values, cache-key construction,
formatting). The unqualified-absolute-vs-probe-bypass contradiction
in the same file went unflagged: the grounding rule chilled a
legitimate same-input consistency detection. Haiku M17 held (floor
met; no haiku regression anywhere).

## Emitted-family movement (false blockers, #36 → this run)

| family | haiku | sonnet | total |
|---|---|---|---|
| speculative-consequence | 63→54 | 52→50 | 115→104 |
| hallucinated-fact | 20→15 | 50→42 | 70→57 |
| risk-boilerplate | 18→22 | 52→43 | 70→65 |
| severity-inflation | 16→12 | 39→26 | 55→38 |
| absolute-consistency | 6→4 | 8→5 | 14→9 |
| **total** | **123→107** | **201→166** | **324→273** |

Narrative coding invariant: **469 total = 193 expected-expression +
273 false blockers + 3 defect-expression-unmatched** (mechanically
reproduced; see derived-metrics.json).

## New matcher-gap candidates (recorded, NOT repaired)

1. **M11** (haiku r3f1): "|| true suppresses the exit code …
   impossible to detect migration failures" — expresses the defect
   functionally; `comment_all: ["status"]` requires a word this
   phrasing never uses.
2. **M16** (haiku r2f1, r4f1): "the fallback return {\"ok\": True…}
   is returned when an exception occurs, not when the sync
   succeeded / even when the PUT failed" — fabricated-success stated
   as returned-on-failure; a distinct phrasing family, NOT the
   frozen #35 response-shape negative (which remains a false blocker
   here: h r0f2 / s r0f2 coded severity-inflation per the frozen
   ruling).

## Miss decomposition (90 non-detecting positive runs)

haiku: 5 protocol (JSON decode failures — M9 cluster again, M6/C9)
+ 33 reviewer-miss; sonnet: 29 reviewer-miss; 3 runs contained
gap-candidate narratives.

## Frozen run identity (freeze.json committed before call 1)

- subject `9772b8b5808a07d4c2e0eeda48639e4f15c89fc0` (#39 merge;
  rubric.md-only delta; rubric_hash `8c14fdc4ce8c5b20`)
- oracle `1ef8dc90badc27bd` · corpus `902738301d0a8bd7`
- N=5 × 36 fixtures × both governed profiles = **360 calls, exactly
  once each; 0 transport retries; no reruns**
- tokens: 279,975 prompt per profile; completions 76,178 (sonnet) /
  79,043 (haiku) · **$2.64 of $3.50 cap**
- Deviation 6 floors: haiku 51/90, sonnet 66/90 (per-positive in
  repair-4 witness-replay)

## Files

- `freeze.json` (pre-call identity freeze, committed before the run)
- `haiku-n5.json`, `sonnet-n5.json` + transport logs (byte-untouched)
- `derived-metrics.json`, `narrative-coding.jsonl`,
  `inconclusive-audit.json` (10 runs, all JSON decode failure,
  surface format recorded non-causally),
  `oracle-validity-audit.json` (miss decomposition, gap candidates,
  M17 regression diagnosis)
