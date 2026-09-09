# T1.3 iteration 2 measurement — grounding rule + direct-contradiction protection (2026-09-09)

## STATUS: **ITERATION 2 FAIL — mechanism must revert.**
## Hard invariants violated on multiple independent criteria. NOT BINDING —
## does not earn the T1.2 reference. No further spend authorized. Per the
## frozen keep/revert lifecycle, the #43 reviewer behavior reverts after
## this bundle merges.

Frozen identity: subject `1bd0ef9a0b22e3ab265a774fa53f0afe26542330`
(#43 merge), rubric `345b8af00cd5db1e`, oracle `cb6870c5a4c635b2`
(repair 5), corpus `72035a00b8db828d`. Freeze revision 2
(`8e9485d`) predates call 1 by commit history.

## Frozen criteria — all five FAIL

| # | frozen criterion | measured | verdict |
|---|---|---|---|
| 1 | zero GATING violations, both profiles | **C7 violates GATING on both profiles** — haiku: 1 INCONCLUSIVE (label-evidence mismatch; 0 false blockers); sonnet: 8 false blockers | **FAIL** |
| 2 | every Deviation 6 per-positive floor | **4 violations** (below) | **FAIL** |
| 3 | speculative-consequence ≤ 53 / ≤ 50 / ≤ 103 | **65 / 100 / 165** | **FAIL** |
| 4 | control FBs ≤ 78 / ≤ 112 | **83 / 142** | **FAIL** |
| 5 | sonnet C7 clean | 8 false blockers | **FAIL** |

## Hard-invariant failures

**Floor violations (criterion 2):**

| profile | fixture | measured | floor |
|---|---|---|---|
| haiku | M1 | 1/5 | 5 |
| haiku | M9 | 0/5 | 1 |
| sonnet | M13 | 0/5 | 1 |
| sonnet | **M17** | **0/5** | **5/5** |

**GATING regression (criterion 1):** C7 — the control whose sonnet
speculative blockers iteration 1 eliminated — violates GATING on both
profiles in this run, by two different mechanisms: sonnet emits 8 false
blockers; haiku emits 0 false blockers but 1 INCONCLUSIVE (the
authoritative normalizer audit attributes it to the label-evidence
mismatch: an ISSUES_FOUND label with no validated blocking finding).
Both raw reports independently record `C7` under `gating_violations`.

## Why M17 failed — the central result

Iteration 1: grounding rule → C7 clean, specificity up, sonnet M17
5/5 → 0/5 (reverted by #41).
Iteration 2 added the explicit direct-contradiction protection — and got
**sonnet M17 = 0/5 again**, C7 regressed on both profiles, control FBs
**rose** (78→83 haiku, 112→142 sonnet), and new sensitivity collateral
appeared (haiku M1 1/5, haiku M9 0/5, sonnet M13 0/5).

(Haiku M17 is not a floor violation — its Deviation 6 floor is 0;
the sonnet M17 floor is 5/5.)

Run-detail diagnosis (sonnet M17): CLEAR on all five runs with
documentation-completeness advisories only — the same-input
cache-absolute-vs-probe-bypass contradiction went unflagged exactly as in
iteration 1. The protection paragraph did not restore the detection.

**Conclusion recorded for the architecture decision (not chosen in this
bundle): the rubric-only grounding approach is unstable as a
discrimination mechanism** — iteration 2 failed to repair the
sensitivity loss AND forfeited much of iteration 1's specificity gain.
The next mechanism class to investigate is the plan's
**(b) structured finding support + deterministic support validation**,
not a third rubric paragraph.

## Repair-5 matcher integrity

The repair-5 targets were NOT the failure: M11 5/5 both profiles (both
entries firing), M12/M16 floors held on both profiles. M17's loss is a
reviewer-reasoning failure (CLEAR with advisories), not a matcher,
parser, or pair artifact — paired control C17 is clean.

Five matcher-vocabulary gap narratives appeared (recorded as
`defect-expression-unmatched`, frozen coding untouched): M3 and M16
(haiku), M9, M10, and a second M16 variant (sonnet). The M16
fabricated-success defect is phrased as *"mimics success. This is a
lie — the sync failed"* and *"dict claiming success … no labels were
actually synced"*; the M10 narrative states the contains-anywhere
non-anchoring defect without any frozen anchor-vocabulary needle. The
matcher-vocabulary chase continues to confirm the case for mechanism
layer (b).

## Emitted-family movement (false blockers, #40 → this run)

| family | haiku | sonnet | total |
|---|---|---|---|
| speculative-consequence | 54→**65** | 50→**100** | 104→**165** |
| hallucinated-fact | 15→28 | 42→49 | 57→77 |
| absolute-consistency | 4→15 | 5→14 | 9→29 |
| severity-inflation | 12→8 | 26→8 | 38→16 |
| risk-boilerplate | 22→6 | 43→21 | 65→27 |

Three of the five emitted false-blocker families worsened — including
the target speculative-consequence family (104→165) — while
severity-inflation (38→16) and risk-boilerplate (65→27) improved
further. Overall control false blockers nevertheless regressed on both
profiles, so iteration 2 lost the required specificity while also
violating sensitivity floors.

Exact per-profile tables: `derived-metrics.json#narrative_coding_summary`.
Coding: 505 blocking narratives = 186 expected-expression + 314
false-blocker + 5 defect-expression-unmatched (invariant holds; coded
counts reconcile with raw blocking counts per fixture).

## Run integrity & spend

360 logical calls (36 fixtures × 5 runs × 2 profiles), exactly once,
zero retries/reruns, everything preserved as emitted. Cost **$2.80**
of the $3.50 cap (list-pricing upper bound; method in metrics).
INCONCLUSIVE: haiku 12 (11 JSON decode failure + 1 label-evidence
mismatch — authoritative normalizer replay, not surface-format
inference), sonnet 0. False-clears on positives: 30/90 haiku,
20/90 sonnet (unchanged vs #40).

## Files

- `freeze.json` — revision 2 (supersedes `4184dbd`, both pre-call)
- `haiku-n5.json`, `sonnet-n5.json`, `run-haiku.log`, `run-sonnet.log` — raw, byte-immutable
- `derived-metrics.json` — identity, protocol, spend, floors, criteria
- `narrative-coding.jsonl` — every blocking narrative coded, pointers preserved
- `inconclusive-audit.json` — authoritative normalizer causes

## Provenance note

Raw-evidence commit `5b44bca`'s message says "M17 0/5 both profiles vs
5/5 floors" — imprecise: the sonnet M17 floor is 5 (violated, 0/5); the
haiku M17 floor is 0 (not violated). The commit is immutable; this note
is the correction of record.
