# Blocking-evidence boundary simulation — 2026-09-21 (Phase 09)

Deterministic, offline, zero-call replay over the frozen 414 Stage-A/B1
records (276 blocking findings). Question:

> Had a blocker required a verifiable harm-bearing quote from the
> cited diff, which historical blocking findings would have survived?

Run: `python3 eval/evidence_boundary_sim.py`

## Gates simulated

- **G1 "strict quote"** — blocker survives only if the cited file is
  in the diff AND ≥1 explicit quoted span from its comment occurs in
  that file's patch (Phase-08 normalization; bare identifiers are not
  quotes; code-shaped characters preserved).
- **G1h "harm-anchored" (exploratory extra)** — G1 but the quote must
  share a sentence with harm/presumption language.
- **G2 "contract-aware"** — G1 OR the (ii-a) file-local
  contract-contradiction path (contract-reference language +
  contradiction language + a quote from the cited file's documentation
  region).

## Results (276 blocking findings)

| Role | n | G1 survive | G1h survive | G2 survive |
|---|---|---|---|---|
| Control blockers | 77 | **27 (35%)** | 17 (22%) | 27 (35%) |
| True-positive detections | 165 | **111 (67%)** | 47 (28%) | 111 (67%) |
| Extra blockers on positives | 34 | 7 (21%) | 2 (6%) | 7 (21%) |

Focus fixtures (all sources combined):

| Fixture | n | G1 | G1h | G2 |
|---|---|---|---|---|
| C3 | 17 | 6 | 3 | 6 |
| C12 | 18 | 9 | 5 | 9 |
| C13 | 15 | **3** | 2 | 3 |
| M3 | 14 | **14** | 3 | 14 |
| M12 | 26 | 15 | 12 | 15 |
| M16 | 18 | 15 | 3 | 15 |

## What the simulation establishes

1. **G1 separates directionally but unacceptably.** Control blockers
   survive at less than half the true-positive rate (35% vs 67%),
   and the worst control family behaves as hoped — C13 keeps only
   3/15, C3 6/17. But the cost side is heavy: **54 genuine blocking
   detections (33%) would be downgraded**, including 11/26 M12 and
   3/18 M16 findings. A gate that deletes a third of its true
   positives is not a severity boundary; it is a different reviewer.
2. **Harm-anchoring by text mining collapses the separation** (22%
   control survival vs 28% true-positive survival). Where the
   presumption lives in a sentence is not extractable from v1 prose.
3. **G2 ≡ G1 exactly.** The (ii-a) contract path fired on 44 rows —
   contract findings do quote their file's documentation — but it
   never rescued a G1-downgraded finding: findings that fail G1 don't
   operationalize the path on v1 prose (e.g. M12's "the docstring
   says an empty cache must raise… but the code returns {}" contains
   no explicit quote at all). **The M3 distinction is neither
   validated nor refuted by v1 data; it is unmeasurable post-hoc.**
4. **The surviving-control residue is the presumed-harm class,
   exactly.** Every C13 survivor anchors to a REAL in-diff keyword
   (`pull_request_target`, `!head.repo.fork`) inside a sentence
   carrying the presumed consequence (head checkout by an unseen
   workflow). The true fact and the invented consequence are
   lexically inseparable in v1 comments.
5. **The oracle repair and the gate compose.** M12 extra-blockers
   quoting the PR-description phrase 'on origin failure serve
   last-good' now downgrade mechanically: the clarified fixture no
   longer contains that contract text.

## Methodology honesty

- v1 findings carry no evidence fields; quotes are heuristic
  extractions (backtick, double-quoted, guarded single-quoted spans).
  Comments systematically quote real diff text as CONTEXT while the
  harm lives in unquoted prose — so G1/G2 survival here is an UPPER
  BOUND on a v2 model-emitted-quote gate.
- The line-in-hunk rule is reported per row, not gated (v1 line
  fields are noisy).
- The simulation cannot adjudicate claim DIRECTION: C12's KeyError
  family survives any quote gate while misstating the contract —
  that failure mode belongs to oracle clarity (fixed in Phase 08),
  not to the boundary.

## Recommendation

**FOR implementing the structured blocking-evidence boundary
(ReviewResult v2 + parser-owned deterministic gate) — conditionally,
and on the strength of what the simulation NEGATES rather than what
it shows:**

- Post-hoc quote verification on v1 prose either keeps presumed harm
  (G1/G2) or destroys true positives (G1h). The separating
  information — which claim is harm-bearing, and what kind of claim
  it is — exists only in the model's generation-time intent. The
  boundary must therefore be **declared by the model at generation
  time** (`evidence.kind`, `evidence.harm`, `evidence.quote`) and
  **verified deterministically by the parser** (file-in-diff,
  normalized quote-in-patch, line-in-hunk, kind ≠
  `out_of_diff_assumption`, harm = `demonstrated`), failing closed to
  a recorded downgrade (`BLOCKING_EVIDENCE_INSUFFICIENT`).
- The simulation cannot measure v2's true separation — only a
  preregistered trial with model-generated v2 outputs can. Required
  before any B-class spend: (a) ReviewResult v2 schema + parser gate
  as an engine-contract feature phase; (b) an **honesty audit** of
  the declared `kind`/`harm` against adjudicated samples (a declared
  `demonstrated` must itself be spot-checkable); (c) a small N=1
  calibration preregistration on the repaired oracle before any
  B1.1/B2 decision.
- The M3 (ii-a) distinction remains a rubric-level proposal for that
  same future preregistration; this simulation neither validates nor
  refutes it.

**Not started, by standing direction:** ReviewResult v2 implementation,
B1.1, B2, any paid campaign, any rubric/parser change inside Phase 09.

## Contents

- `boundary-sim-report.json` — per-finding rows (276): fixture /
  effort / run / role / original severity / cited file+line /
  file-in-diff / line-in-hunk / candidate quotes with per-quote
  in-patch + doc-region + harm-anchored flags / per-gate outcome +
  reason; role × gate summaries overall, per source, and for
  C3/C12/C13 vs M3/M12/M16.
- `eval/evidence_boundary_sim.py` — the deterministic tool.
- `tests/test_boundary_sim.py` — 13 structural, determinism,
  extraction-honesty, and evidence-pinned tests.
