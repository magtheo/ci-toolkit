# Stage-A qualification report — z-ai/glm-5.3-flash, efforts low/high/max (2026-09-19)

**Campaign complete: 324/324 logical reviews (36 fixtures × N=3 × 3
efforts), zero missing records, all three campaign identities
consistent. Actual spend: $0.3916 of the authorized $10 ceiling.**

## Verdict per the pre-registered selection rule

**ALL THREE PROFILES ARE DISQUALIFIED. The frozen rule selects
nothing.**

| effort | D1 transport | D2 GATING | D3 control false-block | D4 post-esc exhaustion | tuple |
|---|---|---|---|---|---|
| low | — | — | **FIRED** (6 controls) | — | [-32, 5, -6, 66576, 1933.3] |
| high | — | **FIRED** (C4) | **FIRED** (9 controls) | — | [-36, 11, -6, 151033, 2121.2] |
| max | — | **FIRED** (C4) | **FIRED** (9 controls) | — (1/22 = 4.5%) | [-34, 12, -4, 1224785, 12634.8] |

The failure mode is **reviewer over-triggering on clean code**
(D3: unexpected blocking findings on control runs — zero-tolerance
per the repaired oracle), not transport: 0 unresolved transport
failures in 346 completed generations, budget exhaustion only at max
(23 length-exhaustions → 22 escalations → 1 post-escalation
exhaustion → 2 final INCONCLUSIVE).

## Headline metrics

| metric | low | high | max |
|---|---|---|---|
| aggregate run-level positive detection /54 | 32 | **36** | 34 |
| false blockers on positives | **5** | 11 | 12 |
| controls false-blocking (zero tolerance) | 6/18 | 9/18 | 9/18 |
| pair-integrity violations | 3 | 4 | 4 |
| promotion-eligible positives | 6 | 6 | 4 |
| GATING regressions | none | C4 | C4 |
| final INCONCLUSIVE | 0 | 0 | 2 |
| provider generations | 108 | 108 | 130 |
| length exhaustions / escalations | 0/0 | 0/0 | 23/22 |
| avg wall per logical review | 18s | 20s | 117s |
| tokens in / out(+reasoning) | 129k/67k | 129k/151k | 156k/1.22M |
| actual cost | $0.0263 | $0.0474 | $0.3179 |

More reasoning effort did **not** buy sensitivity (36/54 at high,
34/54 at max) but did buy over-triggering (5 → 12 FB-on-positives),
cost (≈12× tokens at max) and latency (≈6.5×). The false-block
pattern on controls is broadly stable across efforts (C2, C3, C8,
C12, C13, C16 fail everywhere; C10, C11, C4 join at high/max) —
this reads as a model-level calibration property of GLM-5.3-flash
as an advisory reviewer, not an effort-tuning problem.

## Frozen-rule interpretation

- D3 (zero-tolerance control false-block) disqualifies **every**
  effort. Under the preregistered rule there is no profile to
  promote, no tuple comparison to run, and no low-vs-high-vs-max
  winner.
- The historical Haiku/Sonnet floors (51/90, 66/90) remain
  **methodological context, not numerically comparable thresholds**
  — but even descriptive comparison is unflattering: GLM's best
  effort-level detection (36/54 ≙ run-level) comes with 11 false
  blockers on positives and 9/18 controls false-blocking.
- GATING regressions at high/max (C4 false-blocks) would
  independently veto deployment of those efforts.
- Consequence for the deployed provisional profile (low/8000): the
  sweep gives **no measured basis** to change it, and documents that
  even the current dogfood effort fails the zero-tolerance control
  screen. Whether to keep, change, or disable the GLM dogfood caller
  is a human decision informed by this report; no config was touched.

## Execution record

- **Q0 merge SHA**: `cdaf736d1322eef752a945402e223ac9856734ca`
  (#75, reviewed head `c0be6c2…`, human-merged).
- **Execution branch**: `phase/glm-profile-qualification/02-stage-a-execution`
  (`4b3611a` ceiling enforcement, `a2e8281` frozen execution script,
  this report).
- **Oracle**: checkout `4b116a7c…`, `oracle_version 9e20730cb0436002`
  (recorded in every `campaign.json`; recomputed unchanged).
- **Campaign identities**: one per effort directory (`campaign.json`:
  model, effort, budget 8000, N=3, oracle/subject/transport
  content-refs and SHAs, rubric/corpus hashes).
- **Execution order**: exactly the pre-registered cyclic schedule —
  run 0 low→high→max, run 1 high→max→low, run 2 max→low→high — via
  `--run-index` invocations of the frozen script (08:46–14:20).
- **D1 halt + authorized resume**: during max run 2, fixture C10
  exhausted 3 legacy HTTP attempts (upstream timeouts, zero tokens
  billed). The campaign halted per D1; the halt marker is archived
  verbatim in `max/halt-marker-2026-09-19.jsonl`; the human directed
  "clear marker + resume" (2026-09-19); the same script resumed,
  deduped against persisted records, and completed the campaign.
- **Provider routing**: recorded per generation, deliberately not
  pinned; 14 upstreams observed (Together and Parasail dominate at
  every effort) — the variance the balanced schedule was designed to
  absorb.
- **Completeness**: complete=True for all three efforts; no absent
  fixtures; no missing runs.

## Validity concerns

1. **Ceiling scope correction (disclosed)**: the seeded $10 ceiling
   is enforced **per effort-directory** (each directory seeds from
   its own records), not across the whole campaign as reported
   before execution. Actual aggregate spend ($0.3916) was far below
   the ceiling either way; for any future campaign with a tighter
   binding constraint, seed the guard from all campaign directories.
2. **Upstream timeouts clustered** in the max invocations (curl rc
   28 at 180s, retried by the unchanged legacy policy: 16 raw
   retries at max). Max wall time (3.5h) is dominated by these
   timeouts plus 117s mean generation time.
3. **Routing variance is large** (14 upstreams); per-provider
   breakdowns are in the report JSONs. If a follow-up wants
   provider-attributed quality, that is a new pre-registered
   question (Stage A.1), not derivable here with authority.
4. Reasoning tokens are billed in the cost model as additive to
   completion tokens (conservative over-count if the provider
   already includes them).

Raw evidence: `{effort}/records.jsonl` (324 records, no
reasoning-chain content), `{effort}/summary.json`,
`{effort}/campaign.json`, `report-{effort}.json` (full oracle
outputs: per-fixture evaluate results, per-group hits, pair
integrity, promotion eligibility, hard-disqualifier detail),
`planned_bounds.json`-equivalents in the Q0 bundle.
