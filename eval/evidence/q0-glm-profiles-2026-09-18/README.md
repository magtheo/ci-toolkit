# Q0 preflight evidence — GLM reasoning-profile qualification (2026-09-18)

**Zero model calls were made in Q0.** Everything here is produced by
`eval/profile_qualification.py --dry-run` (deterministic, no network —
asserted by `tests/test_profile_qualification.py`) plus static
identity proofs.

## Identity record (directive §7)

| Field | Value |
|---|---|
| oracle checkout SHA | `4b116a7c7c4e9e78cddd362cd3ca4766aaf6ea25` (#74 merge) |
| oracle_version | `9e20730cb0436002` (recomputed live in tests; oracle inputs byte-identical to checkout — `git diff` empty) |
| subject/reviewer | byte-identical to oracle checkout (engine.py, render.py, rubric.md, parse_review.py, review.sh) |
| transport | `b663bfd3139bb04a70f95d661c96ee150f534513` (#70) — transport.py, model_profiles.json, review_result_schema.json byte-identical |
| rubric sha256 | see `dry-run-*/meta.json` |
| corpus sha256 | see `dry-run-*/meta.json` |
| model | `z-ai/glm-5.3-flash` (provisional deployed profile low/8000 — untouched) |

`eval/profile_qualification.py` is **not an oracle input**:
`oracle_version` hashes `eval/run_corpus.py` + fixtures +
`states.json` only; recomputation at HEAD returns `9e20730cb0436002`.

## What was proven (deterministic; suite count tracked in the PR — 222 passed at rev 3)

- **Request equivalence (§6)**: low/8k request pins the exact
  production #70 shape — `model`, `temperature 0.2`, `max_tokens
  8000`, `reasoning.effort`, canonical strict `response_format`
  schema, `provider.require_parameters=true`, engine prompts
  verbatim. high and max differ from low by **only**
  `reasoning.effort`; escalation differs by **only**
  `max_tokens` (8000→16000).
- **Escalation semantics (§4)**: `finish_reason=length` → exactly one
  retry at 2× budget, effort fixed (guaranteed structurally: the
  profile object is never mutated between attempts); `stop` never
  escalates; partial truncation escalates identically to null
  content; a second exhaustion does not produce a third attempt.
  Logical reviews / provider generations / HTTP retries are counted
  separately; infra failure is a hard fail-closed
  (`TRANSPORT_FAILURE`), never an INCONCLUSIVE verdict.
- **Prompt fidelity (§2)**: golden sha256 pairs for all 36 fixtures'
  (system,user) prompts — byte-identical through the adapter, and
  invariant across effort/budget overrides.
- **Zero-call guarantee**: dry-run completes with `socket.socket`
  replaced by a trap; two runs are byte-identical.
- **Governance**: live mode refused without `--live` AND
  `PM_QUALIFY_LIVE_AUTHORIZED=1`; `model_profiles.json` byte-identity
  asserted after measurement-profile construction.

## Stage A — pre-registered campaign (directive §8; DO NOT RUN YET)

```
model: z-ai/glm-5.3-flash      efforts: low, high, max
initial budget: 8000           N: 3
corpus: full repaired 36-fixture corpus
logical reviews: 36 x 3 x 3 = 324
```

**Balanced execution order (pre-registered)** — efforts are NOT run
in three contiguous blocks; that would confound effort with time and
provider-routing drift (OpenRouter routes among many GLM upstreams;
automatic routing is part of the production environment and is
recorded per generation, not pinned). Instead, a deterministic
cyclic schedule per fixture:

```
run 0: low  -> high -> max
run 1: high -> max  -> low
run 2: max  -> low  -> high
```

Each effort's records land in its own --out directory (campaign
identity makes cross-profile directory mixing impossible); the
schedule is the invocation interleaving the operator follows.

Measured request sizes (dry-run manifests): 178,015 prompt chars
across 36 fixtures ⇒ ~44.5k prompt tokens per review-set pass ⇒
~14.4M prompt tokens across Stage A (chars/4 heuristic).

### Transport-metric separation

Transport failure and semantic reviewer failure are NEVER collapsed:
per-invocation records carry attempts[] (kind, max_tokens,
finish_reason, state, provider, tokens, latency) plus the normalized
ReviewResult. Aggregates: logical_reviews, provider_generations,
http_retries, prompt/completion/reasoning tokens, length_exhaustions,
escalations, post_escalation_exhaustions, final_inconclusive,
transport_failures, wall time, cost.

### Reviewer/oracle metrics (oracle semantics only)

per-positive detection counts (N=3); aggregate positive detection;
per-group detection (25k AND-of-groups / OR-of-alternatives); control
false blockers; false blockers on positives; paired-control outcomes
(control pass is necessary for every positive claim); assessment
stability across N; GATING regressions vs current states; INCONCLUSIVE
count.

### Transport metrics

length exhaustion rate; escalation frequency; post-escalation
exhaustion; refusal/malformed counts; infra failures; reasoning/output
token usage; latency; provider distribution; cost.

## Pre-registered selection rule (directive §9)

**Hard disqualifiers** (any ⇒ effort disqualified):

- D1 transport viability: final INCONCLUSIVE > 10% of logical
  reviews, or any unresolved transport failure (campaign halt);
- D2 GATING regression: any GATING fixture failing its oracle
  stability requirement at that effort;
- D3 discrimination failure (zero tolerance): ANY unexpected
  blocking finding on ANY control run disqualifies the effort. This
  is the repaired oracle's actual control semantics
  (`evaluate(): passes = CLEAR-stability == N and no false
  blockers`) — no tolerance was invented; controls still gate alone.
  D2 remains the separate regression check against the recorded
  GATING states;
- D4 post-escalation exhaustion on >5% of escalated reviews
  (escalation not rescuing ⇒ budget misfit).

**Selection metrics** among survivors, lexicographic:

1. (B) reviewer sensitivity: aggregate positive detection (higher is
   better; run-level definition pinned by
   `AGGREGATE_DETECTION_DEFINITION`, denominator 54). Frozen
   Haiku/Sonnet floors (51/90, 66/90) are **methodological context,
   not numerically comparable thresholds** — different aggregate
   denominators/populations; no governed rule makes them cross-model
   qualification thresholds and they must not be normalized onto the
   54-run aggregate.
2. (C) discrimination: false blockers on positives (lower), then
   paired-control clean count (higher).
3. (D) cost + latency: total tokens then wall time (tie-break).

**Descriptive/reference only**: token usage detail, latency, provider
distribution, cost, historical cross-model floors.

Stage A is profile **screening**: no state promotion, no GATING
change, no deployment-profile change, no fleet rollout follows from
its outcome alone.

## Spend gate (directive §10) — AWAITING HUMAN AUTHORIZATION

| Quantity | Value |
|---|---|
| planned logical reviews | 324 |
| max extra generations from escalation | ≤324 (one per logical review; only on length) |
| max provider generations | 648 |
| HTTP retries bound | ≤2 extra raw attempts per generation (legacy 3-attempt policy) |
| planned output tokens (no escalation) | 324 × 8,000 = 2.59M |
| credible worst-case output bound | 7.78M (every review escalates and exhausts 8k+16k) |
| input tokens, no escalation | ~14.4M (chars/4 heuristic from measured manifests; 324 generations) |
| input tokens, all reviews escalate | ~28.8M (escalation re-sends the prompt: ≤648 generations) |

**Pricing observed 2026-09-18, OpenRouter model page for
`z-ai/glm-5.3-flash`** (openrouter.ai; discounted listing):

| | input / 1M | output / 1M |
|---|---|---|
| current discounted | $0.075 | $0.25 |
| listed undiscounted | $0.15 | $0.50 |

Conservative **token-cap ceilings** (every token consumed at list
rates, every review escalating in the escalation rows) — these are
NOT expected spend; actual Stage-A cost is measured and recorded
from the run telemetry:

| ceiling | discounted | undiscounted fallback |
|---|---|---|
| no escalation (~14.4M in + 2.59M out) | ≈ $1.73 | ≈ $3.46 |
| full escalation (~28.8M in + 7.78M out) | ≈ $4.10 | ≈ $8.21 |

These ceilings do NOT constitute spend authorization. Stage A runs
only after explicit human authorization.

Wall-clock / load: 324 sequential generations at observed 15–60s
smoke latencies ⇒ 108 logical reviews per effort ≈ 0.45–1.8h per
effort, ≈ 1.35–5.4h for the whole three-effort campaign before
escalations/retries; backoff sleeps add under load.

`--live` is mechanically refused without BOTH `--live` AND
`PM_QUALIFY_LIVE_AUTHORIZED=1` (the env var alone is never a live
invocation). **Do not infer authorization from the #74 merge.**

## Known measurement-validity concerns

1. **Effort fallback**: the GLM slug advertises low/high/max, but the
   provider may silently fall back to max reasoning for unsupported
   values (per profile note). Detector: reasoning-token telemetry per
   effort; no machine-readable provider contract exists.
2. **Provider routing variance**: OpenRouter may route the slug to
   different upstreams with different reasoning behavior; provider
   distribution is recorded; if variance dominates, a provider-pinned
   Stage A.1 amendment needs separate human approval.
3. **Token accounting gaps**: some providers omit
   `reasoning_tokens`; nulls are recorded and excluded from sums.
4. **Temperature-0.2 non-determinism**: N=3 plus the oracle's
   ((N+2)//2)-of-N stability semantics is the designed treatment;
   per-run determinism is not claimed.
5. **ReviewInput.model metadata**: run_corpus's legacy
   temperature/max_tokens metadata is not the wire request; the wire
   request is transport+profile-governed and pinned by tests.
