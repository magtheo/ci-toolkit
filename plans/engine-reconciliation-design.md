# Engine Reconciliation Design (context-aware review, Phase 3)

Status: PROPOSED — **design only. Nothing is implemented, executed, or
measured by this phase.** No model calls, no oracle change, no
qualification campaign, no pin promotion, no deployment change, no
consumer-workflow change.

Phase branch: `phase/glm-profile-qualification/24a-engine-reconciliation-design`
→ PR targets `feature/glm-profile-qualification` (Parent: #10).
Owning plan: `plans/context-aware-review.md` Phase 3 (authoritative
copy on `feature/context-aware-review`, PR #110). Authorization:
directing-human directive 2026-10-24 (post-merge sequence step 3),
within the rev-2 routing decision (PR #110 planning review).

Implementation is a **separate, separately reviewed phase** (24b) and
does not follow from this design's approval automatically.

## Problem (audit finding §1.5 of the owning plan)

Two reconciled-but-divergent reviewer implementations exist:

- **`main`** (the deployed surface consumers pin; now at `330e95f`,
  including the PR #111 head-staleness guards): monolithic `review.sh`
  + `transport.py` + `model_profiles.json`. Reasoning-model profiles,
  structured output where profiled, envelope classification, ONE
  budget escalation, transport reason codes, and
  INCONCLUSIVE-on-exhaustion **posted as an assessment** (green job,
  reason-coded review). Empty/no-final content and refusals are
  transport-diagnosed, never red-job failures.
- **Feature umbrella** (the extraction the eval harness shares):
  thin `review.sh` → `engine.py` (prompt + model call + normalize) →
  `render.py`. The engine builds its request payload directly
  (fixed temperature/max_tokens, no profiles, no structured output),
  and treats empty model content as a **hard failure** (red job).
  No profile/reason-code/classification machinery is wired in.

Both are fail-closed, but consumer-visible failure semantics differ.
The owning plan requires reconciliation **before** any
context-retrieval behavior work (Phase 5), with an explicit
behavior-preservation evidence matrix and **no silent regression of
deployed semantics**.

## Goal

One reconciled engine path on the feature umbrella that is
**behaviorally equivalent to deployed `main`** across every response
class, while preserving the Phase-1 extraction boundaries (engine =
the single model-facing pipeline shared with the eval harness;
`review.sh` = thin GitHub transport; `parse_review.py` = semantic
trust; `render.py` = presentation) and **preserving both
head-staleness guards from PR #111**.

## Non-goals (hard boundaries for this design and its implementation)

- No context retrieval, no `ReviewInput` extension (the
  `merge_base_sha` field stays with Phase 5), no rubric change, no
  prompt wording change.
- No eval-semantics change: no fixture, matcher, threshold, GATING
  state, or `oracle_version` change. No model calls in any acceptance
  for this phase (matrix is fixture-driven).
- No qualification campaign, no GATING change, no pin bump, no
  deployment activation. Gate runs remain experimental on
  feature-branch subjects (deployment contract PENDING ACTIVATION).
- No new runtime dependencies; no multi-model routing; no retry-policy
  redesign (parity with the deployed contract only).

## Design principles carried forward unchanged

1. **Trust boundaries**: `transport.py` owns the ENVELOPE (did
   generation complete?); `parse_review.py` owns SEMANTIC trust
   (INCONCLUSIVE is parser-produced, fail-closed, never Clear).
   Decoration refuses anything that is not a reason-coded plain
   COMMENT INCONCLUSIVE payload; parser verdict/event/findings are
   never altered by decoration.
2. **Profiles are reviewed configuration** traveling with the pin
   (`model_profiles.json`); unknown slugs resolve to the default
   profile, which must reproduce the legacy request
   **object-for-object** (the pinned transport invariant).
3. **ONE budget escalation** (profile-flagged, 2× max_tokens, effort
   fixed); infrastructure failures during escalation are hard failures
   (exit 1), never verdicts.
4. **COMMENT-only advisory event**; humans merge.
5. **Head-staleness guards preserved verbatim in behavior** (see
   below).

## Head-staleness guard preservation (explicit commitment)

PR #111 (merged `330e95f`) added two fail-closed guards to `main`'s
`review.sh` (`verify_head_unchanged`, exit 4 head-moved / exit 5
re-check-unavailable, after file acquisition and immediately before
the POST, with SHA-naming notices and the downstream
`commit_id`-validation rule). The feature branch's thin `review.sh`
does **not** have them yet. The reconciled implementation phase MUST:

- port the guards into the reconciled `review.sh` at the same two
  lifecycle points (post-acquisition, pre-POST), preserving exit
  codes, notice content, fail-closed semantics, and the documented
  non-atomicity + base-residual notes (including the PR #112
  clarifications if that PR has merged; otherwise as merged in
  `330e95f`);
- port `tests/stub` + `tests/test_review_head_guard.py` and keep all
  guard scenarios green **unchanged in assertion** against the
  reconciled script (the harness is behavior-anchored, so it transfers
  as-is; the docs-only/stale-precedence and guard-2 failure scenarios
  bind the reconciled path identically).

Until the umbrella merges, `main` has guards and the feature path does
not — an accepted, temporary divergence that this phase closes.

## The six response classes — reconciliation matrix

Per class: definition → deployed `main` behavior (the preservation
target) → feature-branch delta → reconciled target → evidence anchor.
All anchors are existing recorded fixtures
(`tests/fixtures/openrouter/`) or pinned invariants; the matrix runs
deterministically with **zero model calls**.

| # | Class | `main` (deployed truth) | Feature-branch today | Reconciled target | Evidence anchor |
| --- | --- | --- | --- | --- | --- |
| 1 | **Successful content** (200, final content present, valid review JSON) | Profile-shaped request (reasoning/structured fields per profile); content → `parse_review` → payload; diagnostics line reports provider/tokens | Legacy fixed-shape request; content → `normalize` | Profile-shaped request; parse/normalize path unchanged; **default-profile request object-for-object identical** to `transport.py`-built main request | `glm_valid.json`; golden-request test |
| 2 | **200 with no final content** (envelope OK-shaped, content empty/null, e.g. reasoning consumed the budget, `finish_reason: stop`-adjacent `NO_CONTENT`) | `classify → NO_CONTENT` → `failure_reason → NO_FINAL_CONTENT` → **posted reason-coded INCONCLUSIVE** (green job, "do not treat as clear") | Engine hard-fails (red job, no assessment) | Main's posted-INCONCLUSIVE semantics | `glm_reasoning_only.json`; matrix test |
| 3 | **Refusal** (`finish_reason: content_filter`) | REFUSAL wins even if content also present → posted INCONCLUSIVE, `UPSTREAM_ERROR` (content_filter detail) | Not classified; content would be parsed or hard-fail | Main's semantics (refusal precedence) | `refusal.json`; matrix test |
| 4 | **Budget exhaustion** (`finish_reason: length`; both no-final-content and truncated-partial JSON shapes) | ONE escalation (2× budget, effort fixed, profile-flagged); still-length → posted INCONCLUSIVE `OUTPUT_BUDGET_EXHAUSTED`; truncated-partial that fails validation → parser INCONCLUSIVE **decorated** with `OUTPUT_BUDGET_EXHAUSTED` (parser reason preserved as provenance); infra failure during escalation → hard exit 1 | No escalation; empty → hard fail; malformed partial → plain INCONCLUSIVE, no root cause | Full port: escalation, exhaustion mapping, decorate path, `STRUCTURED_OUTPUT_INVALID`→`OUTPUT_BUDGET_EXHAUSTED` | `glm_partial_truncated.json`; matrix + decorate tests |
| 5 | **Transport failure / retry exhaustion** (curl rc ≠ 0; retryable 429/5xx ×3 attempts, attempt-scaled backoff; exhaustion) | Hard failure (exit 1), red job, last status reported, **no fabricated assessment** | Engine `_post_with_retries`: same observable contract (3 attempts, same retryable set, last-status reporting) — verify parity, then preserve | Identical observables; parity pinned by test | transport/engine retry tests; matrix test (stubbed rc paths) |
| 6 | **Malformed envelope** (200 body without a `choices` array / error envelope) | `classify → MALFORMED` → posted INCONCLUSIVE, `UPSTREAM_ERROR` (malformed envelope detail) | JSON parse yields no content → hard fail | Main's posted-INCONCLUSIVE semantics | `error_envelope.json`; matrix test |

Matrix discipline (from the owning plan): every row is executed
pre-implementation on both paths (feature delta demonstrated by test),
post-implementation against the reconciled path, and any residual
divergence is either eliminated or **explicitly reviewed as a
recorded change** in the implementation PR body. No silent regression.

## Implementation shape (proposed for review — decision belongs to 24b)

**Recommended — Option A: engine absorbs the transport contract.**
`engine.py` builds its request via `transport.build_request_body`
(profile-aware), classifies the envelope (`classify_response`), applies
`escalation_decision` + the one retry policy, and returns either a
parsed review result or a terminal transport verdict; `review.sh`
(fail-closed fetch + guards + post) maps terminal verdicts to payloads
via the existing `transport.py` CLI steps (`inconclusive`, `decorate`,
`failure`) exactly as `main` does. Consequences:

- `review.sh` stays thin; the extraction boundary survives (the eval
  harness keeps driving `engine.py`); prompts and normalization are
  untouched (class 1 golden pins this);
- the default-profile request must remain object-for-object identical
  to the legacy/main request — pinned by a golden test, since the eval
  harness shares this path;
- `render.py` and `parse_review.py` are unchanged;
- the engine's (inert) trace sidecar is retained; its
  `provider_call_count` counts logical model stages, so an escalated
  review counts 2 — semantics already frozen in the sidecar contract.

**Rejected — Option B: monolith orchestration in `review.sh`.** Would
duplicately re-home prompt construction in shell, regressing the
Phase-1 extraction that the oracle shares. Not proposed.

Open questions for the 24b review (recorded, undecided here): exact
error-channel mapping when the engine runs in-process vs the CLI steps
(proposed: engine writes a terminal-verdict JSON that `review.sh`
feeds to `transport.py` — keeps verdict ownership where it is today);
whether the matrix tests live beside `tests/stub` (proposed: yes — one
offline harness directory); backoff timing constants in tests
(proposed: inject/patch, never sleep).

## Acceptance criteria (for the 24b implementation phase)

1. All six matrix rows green on the reconciled path, fixture-driven,
   zero model calls; per-row pre/post evidence in the PR body.
2. Golden default-profile request test: object-for-object equality
   with `transport.py`-built main request.
3. Head-guard behavioral suite passes **unchanged in assertions**
   against the reconciled `review.sh` (both windows, both fail-closed
   re-check failures, fork skip, docs-only skip, stale-docs-only
   precedence).
4. Deterministic suite green; `bash -n` clean; COMMENT-only invariant
   tests unchanged.
5. Any reviewed delta from deployed semantics is enumerated in the PR
   body (target: none).
6. No oracle file, fixture, rubric, workflow-input, or pin change in
   the diff; `git diff --name-only` matches this scope exactly
   (PR-description freshness rule).

## Plan deviations

None yet.
