# Matcher repair replay — 2026-09-21 (Phase 08)

Deterministic, offline rescore of the FROZEN Stage-A and Stage-B1
records under the pre-Phase-08 oracle vs the Phase-08 oracle
(`117b4164e5446f50`). Zero network, zero spend, evidence untouched.

Run: `python3 eval/replay_oracle_repair.py`

## Result

| Source | Records | Control blockers | Flips |
|---|---|---|---|
| stage-a-low | 108 | 18 (unchanged) | 0 |
| stage-a-high | 108 | 19 (unchanged) | 0 |
| stage-a-max | 108 | 21 (unchanged) | 0 |
| b1-low | 45 | 11 (unchanged) | 2 |
| b1-high | 45 | 8 (unchanged) | 1 |

Flips (run-level detection, legacy -> Phase 08):

- `M16` low run1: False -> True ("discards ... falls through to
  return {\"ok\": ...}" — semantically detected in B1, lexically
  missed)
- `M4` low run2: False -> True ("outside this diff")
- `M4` high run2: False -> True ("not part of this diff")

**Nothing moves False <- True anywhere. No Stage-A classification
moves at all** — Stage-A disqualification results (D1-D4, detection
floors) are unaffected by the repair. Control blocker counts are
severity-scored and matcher-independent by construction; they are
identical under both scorers in every source.

## Integrity of the legacy scorer

The replay reconstructs the pre-Phase-08 scorer as (legacy matcher
copy + current needles minus the documented Phase-08 additions) and
checks it against the COMMITTED `b1-report-{low,high}.json` detection
numbers: both sources report `match: true` for every fixture
(see `legacy_integrity_vs_committed_b1_report` in the report JSON).
The reported deltas are therefore trustworthy as exactly the
Phase-08 repair effect and nothing else.

## Contents

- `replay-report.json` — full per-source, per-fixture, per-run report
- `../stage-b1-diagnosis-2026-09-21/DIAGNOSIS.md` — the diagnosis this
  repair implements (with the human's C12 adjudication addendum)
- `../stage-b1-diagnosis-2026-09-21/DESIGN-NEXT-INTERVENTION.md` —
  M3 policy resolution + blocking-evidence boundary design (proposal
  only; requires a new preregistration)
