# Context-Aware Review Reliability

Status: PROPOSED (rev 1, 2026-10-23) — plan + Phase-1 audit only. No
reviewer behavior change, no eval-semantics change, no pin change, no
consumer-workflow change has been made by this document. Implementation
must not begin until a maintainer reviews this plan and records the
routing decision (see "Routing decision required").

Branch basis: `feature/glm-profile-qualification` @ `e08b618`
(merge of PR #108). `main` @ `1ae4287`.

## Goal

Let the advisory reviewer evaluate a PR against the **actual trusted
project context it touches** — existing code, callers, interfaces,
tests, architectural invariants and approved plans — instead of the
diff alone, so that cross-file contract claims (the measured M4 class,
0/10 detections in the frozen baseline) become checkable instead of
unverifiable, **without** weakening the paired-control discrimination
discipline and without raising the false-blocker rate.

This is ROADMAP.md **Track 3 (targeted trusted-base context
retrieval) + Track 4 (cross-file contract reasoning)**, implemented as
the already-admitted T1.3 candidate **layer (c): "evidence
representation — enrich ReviewInput context/budgeting so the model can
ground rather than guess"**. It is not a new reviewer architecture.

## Relationship to the existing program (reconciliation)

- **One engine, one pass.** Context acquisition is a deterministic
  pre-model stage that *extends* `ReviewInput v1` with an additive,
  optional `context` field (plan constraint: "Stage 2/3 EXTEND these
  contracts — never a parallel execution path"). Semantic reasoning
  stays the single engine pass. Acquisition and reasoning are separable
  so the oracle can evaluate them independently.
- **Track 1 stays the active stage.** This plan does not preempt
  T1.3/T1.4. Its reviewer-*behavior* phase (Phase 5) is subject to the
  same invariants: Deviation-6 sensitivity floors (haiku 51/90,
  sonnet 66/90), zero GATING regressions (C4/C5/C7), zero control
  false-blocks, keep/revert lifecycle, evidence frozen before
  promotion. Its *infrastructure* phases (2–4) change no reviewer
  semantic behavior (byte-identical prompts when context is absent)
  and therefore do not collide with the T1.3 loop.
- **The frozen v21 evidence layer is untouched.** This feature neither
  imports nor modifies `eval/v21_m4_relation.py` (SHA-pinned
  `1a01d8ff…`, grant-scoped preservation-only authority), the psd
  authority, the failed dsc family, the V2/PC2 reduction policy
  (UNRESOLVED by design), or any grant registry. m4rel is a
  vocabulary-tuned *witness relation* over recorded runs with no
  runtime authority; the reviewer must earn cross-file capability
  semantically, not by importing the detector. Conversely, a measured
  context-grounded reviewer is exactly the kind of evidence source a
  future PC2 Path-B-style cycle would need — that is recorded as a
  note, never as a claim.
- **Eval discipline unchanged.** New fixtures freeze BEFORE behavior
  changes; fixture/context-schema additions change `oracle_version`
  and fail closed; oracle changes never share a PR with reviewer
  behavior (standing rule).

## Non-goals

- No multiagent pipeline, no second model pass, no model change, no
  provider change, no vector-database/RAG infrastructure, no repo
  clone on the runner (GitHub API only), no PR-head retrieval.
- No change to the security model: GitHub-API-only data access, no
  PR-head checkout/execution, credential header-file transport, fork
  skip, COMMENT-only advisory event, human merge authority.
- No automatic merge authorization, no trusted status check activation,
  no GATING change without measured qualification, no consumer pin
  bump, no KodeVerket production-workflow change.
- No whole-repo dumps: retrieval is bounded, claim-driven, and
  budgeted; omitted material is recorded, not silently dropped.
- No adoption of the V2 bare-scope reduction, no resolution of PC2,
  no grant-registry writes.

## Constraints

1. Retrieval reads **only trusted base material**: the PR merge-base
   (exact three-dot ancestor of the diff), never the PR head, fetched
   via the GitHub API with the existing credential-transport pattern.
2. Approved plans and project policy stay **distinct from PR-authored
   claims**: the policy channel remains the base-resolved
   `.ai-review-rubric.md`; PR title/body/diff remain untrusted claims.
3. Bounded context: hard caps on file count and bytes (env-tunable),
   deterministic selection, recorded omissions. No uncontrolled
   expansion.
4. Secret-avoidance: a denylist excludes secret-bearing paths
   (`.env*`, `*.pem`, `*.key`, `id_*`, `*credential*`, `.git/**`,
   token/session dirs, …) from retrieval; denylist hits are recorded
   as omissions, never fetched.
5. PR head/base consistency is verified before publishing a review
   (Phase 2); a review is never posted against a moved head.
6. Unsupported or materially missing context stays **visible as a
   limitation** (integrity block, Phase 6), never silently absorbed
   into Clear.
7. Every retrieved item records its exact source revision and the
   reason it was selected; every omission records why.

---

## Phase 1 — Audit and evidence (findings)

Status: COMPLETE (2026-10-23; this audit. Deterministic work only —
no model calls, no oracle change, no behavior change. 480/480
deterministic tests green on `e08b618`.)

### 1.1 Exact current review input

`ReviewInput v1` (engine.py / review.sh, feature branch): `title`,
`body` (hard-truncated to 2000 chars, **no note**), `files[]
{path, status, patch}` from `GET /pulls/{n}/files` (paginated,
100/page), `policy` (bundled rubric or base-resolved
`.ai-review-rubric.md`), `model {id, temperature 0.2, max_tokens
2000}`. **The model's entire knowledge of the repository is the
diff.** No base content, no callers, no tests, no interfaces, no
invariant/policy documents beyond the rubric.

Budgeting (`engine._budget`): file list capped at
`AI_REVIEW_MAX_FILES` (200) with an in-prompt note; diff text capped
at `AI_REVIEW_MAX_DIFF` (120,000 chars) with an in-prompt note;
patch-less files excluded; engine exits 3 (transport: clean skip,
exit 0) when the budgeted input has no textual diff.

### 1.2 Missing-context behavior (measured, frozen)

The rubric's Demonstrability rule forces out-of-diff-dependent
findings to non-blocking, and its "unsubstantiated absolute guarantee"
rule *may* block unverifiable cross-file claims. Measurement shows the
single-pass form does neither:

- **M4** (docstring asserts an absolute cross-file contract, e.g.
  "the orchestrator consults this flag and no other signal", about
  code outside the diff): **0/5 detections on haiku AND sonnet,
  5/5 false CLEARs on both** (`eval/evidence/track1-baseline3-2026-09-07/derived-metrics.json`;
  floor parity exact under the group-semantics oracle replay,
  `eval/evidence/track1-oracle-group-semantics-2026-09-18/`). M4 is
  KNOWN_GAP, owner "Stage 3" — this feature.
- **C4** (paired control, strictly self-scoped claim): **0 false
  blockers on both profiles; GATING.** The M4 pair's false-blocker
  baseline is clean today and must stay clean (roadmap Track 3
  acceptance: "no increase in control false-blocks").
- Broader frozen baseline (same bundle): Deviation-6 floors haiku
  51/90, sonnet 66/90; C7 (GATING) violated by **both** profiles in
  the last full unchanged-reviewer measurement (haiku labeling
  protocol; sonnet 6 blocking false-blockers); pair-integrity
  violations haiku 6 pairs / sonnet 2 pairs. The binding T1.2
  reference remains **unearned** (plan Deviations 5/6 deadlock) —
  context retrieval is layer (c) input for that same loop, not a
  substitute for it.
- Three single-pass T1.3 mechanisms already measured and rejected
  (iter-1 rubric, iter-2 grounding, layer-(b) structured support:
  "support presence is not semantic entailment"). Input enrichment
  (layer c) is the remaining admitted single-pass candidate; a
  dedicated-pass form (layer d) stays available but is NOT proposed
  here (smallest-change discipline).

### 1.3 Truncation handling

- Truncation notes exist **only in the prompt**. `ReviewResult` v1
  carries **no coverage/truncation metadata**; a truncated PR can be
  assessed Clear (README Limitations; MATURITY Stage 3.6 open).
- `body` truncation at 2000 chars is silent (no note at all).
- Patch-less (binary/docs) files are excluded with no count anywhere.

### 1.4 Snapshot freshness / head–base consistency (new audit finding)

`review.sh` (both main and feature variants): `head_sha`/`base_sha`
are captured from `GET /pulls/{n}`; the changed-file list is then
fetched from `GET /pulls/{n}/files` — **an unpinned endpoint that
serves the current head**; the review is POSTed with
`commit_id: head_sha`. A push between fetch and post yields a review
whose payload mixes the old head's identity with the new head's files
(or skips posting entirely — no verification exists at any point).
No re-check of `head_sha` occurs before publishing. The rubric fetch
pins `base_sha` correctly. Additional subtlety: GitHub PR diffs are
three-dot (merge-base…head); `base.sha` may sit ahead of the merge
base after base-branch movement, so any context retrieval must use
the **merge base** (`GET /compare/{base}...{head}` →
`merge_base_commit.sha`), not `base.sha`, to honor "exact source
revisions".

### 1.5 GitHub Actions result semantics

- Successful/skip runs: green step (review posted, or explicit skip
  for fork PRs and docs/binary-only diffs). `Inconclusive` is a
  posted COMMENT review, deliberately an assessment, on a green job.
- Infrastructure failure: red failed job, never a fabricated
  assessment (README; verified in both review.sh variants).
- **Divergence (reconciliation debt):** `main`'s monolithic review.sh
  (the deployed surface) uses `transport.py`/`model_profiles.json` —
  reasoning-model profiles, structured output, envelope
  classification, budget-exhaustion → posted INCONCLUSIVE with reason
  codes (`OUTPUT_BUDGET_EXHAUSTED`, …). The feature branch's extracted
  engine path (`engine.py`, Phase-1 extraction) does **not** use
  transport.py; empty model content is a hard failure (red job), and
  no profile/reason-code machinery is wired into it. Both remain
  fail-closed, but the consumer-visible failure semantics differ;
  the umbrella reconciliation must resolve this before merge.
- **Deployment contract gap (reported, not assumed):** qualification
  and pin promotion (`qualify.yml`, `verify-qualification.yml`,
  `verify-pin` job) exist **only on the feature umbrella**; `main`
  has neither `engine.py` nor `qualify.yml`. The contract is
  **PENDING ACTIVATION** (README): no qualification record gates any
  pin today; the dogfood pin bump still follows the review-only
  procedure. Nothing currently enforces the qualification contract.

### 1.6 Baseline reproduction

- **Deterministic reproduction (performed here, zero calls):**
  deterministic suite 480/480 green at `e08b618`; the frozen
  baseline-3 per-fixture metrics re-read directly (M4 0/5+0/5,
  10/10 false CLEARs; C4 0 FBs both profiles; floors 51/90, 66/90);
  the 25k group-semantics bundle already proved exact floor parity of
  the frozen #36 rescore under the current oracle. Current oracle:
  `117b4164e5446f50`. GATING states: C4, C5, C7.
- **Live reproduction procedure (requires the directing human's
  OpenRouter key; not available in this environment):**

  ```bash
  # M4 pair first (small, cheap):
  OPENROUTER_API_KEY=… python3 eval/run_corpus.py --only M4,C4 \
      --model anthropic/claude-haiku-4.5 --n 5 --out /tmp/m4-repro.json
  # expected: M4 detections 0/5 (KNOWN_GAP reproduced), C4 0 false blockers
  # full-corpus unchanged-reviewer baseline (probe scale, ~180 calls/profile):
  OPENROUTER_API_KEY=… python3 eval/run_corpus.py \
      --model anthropic/claude-haiku-4.5 --n 5 --out /tmp/base-h.json
  # sonnet profile likewise; compare to baseline3 bundle + floors
  ```

  Spend rules per plan: probe-scale runs are pre-authorized by the
  eval-baseline plan; larger scales ask first.

### 1.7 Disposition of shortcomings: scheduled / completed / blocked

| Shortcoming | Disposition |
| --- | --- |
| Cross-file/M4 misses | **Scheduled** — ROADMAP Track 3/4, owner "Stage 3" = this plan |
| False-blocker / discrimination | **In flight** — Track 1/T1.3 active; 3 mechanisms rejected; layer (c) = this plan's mechanism; layer (d) designed separately if earned |
| Same-diff consistency (M5) | **Blocked** — Phase 4 BLOCKED by plan Deviation 2; resumes after the Track 1 exit (T1.5 handoff). M5 KNOWN_GAP; its control C5 is GATING and must stay clean |
| State/lifecycle (M8), external contracts (M7), invariants (M6 family) | KNOWN_GAP families, owners recorded in ROADMAP tracks 5–7; not this feature |
| Truncation visible in result | **Scheduled** — MATURITY 3.6 (this plan Phase 6 implements the marker layer; verdict semantics remain 3.6's human decision) |
| SHA-bound decision state | **Scheduled** — MATURITY 3.7 (this plan Phase 6 produces its evidence input only) |
| Head/base snapshot race | **Not scheduled anywhere** — new finding (this plan Phase 2) |
| Secret-avoidance for retrieved context | **Not scheduled anywhere** — new (this plan Phase 4) |
| Eval→deployment activation | **Blocked** — umbrella merge + post-merge live demonstrations (Deviations 1/3); gap reported in 1.5 |
| Engine-path divergence (main vs feature transport semantics) | **Blocked** — umbrella reconciliation concern; recorded in 1.5 |

---

## Phase 2 — Transport integrity: snapshot consistency

Status: NOT STARTED — **recommended first implementation slice**
(transport-only, no model calls added beyond two cheap GETs, no
engine-contract change, no eval-semantics change, no rubric change).

### Scope

- After file pagination and again immediately before the review POST,
  re-fetch `GET /pulls/{n}` and compare `head.sha` to the captured
  `head_sha`. On mismatch: abort **before** the model call (first
  check) / before the POST (second check) with a distinct exit code
  and a step-summary notice ("head advanced during review; skipped;
  the next run reviews the new head"). Never post a review bound to a
  stale head.
- Add `GET /compare/{base_sha}...{head_sha}` to record the exact
  `merge_base_commit.sha` and pass it through `ReviewInput` (additive
  optional field `merge_base_sha`) so downstream retrieval and the
  integrity block can cite the true diff ancestor.
- Apply the same invariant to the feature branch's thin `review.sh`
  and (at umbrella reconciliation) main's monolith.

### Acceptance criteria

- Deterministic tests simulate: stable head → review posts; head
  moved pre-model → no model call, clean skip exit; head moved
  post-model pre-post → no POST, distinct exit code + notice.
- No change to prompts, rubric, ReviewResult semantics, or eval
  behavior; full deterministic suite green.

### Validation

- `python3 -m pytest tests/ -q`; bash syntax check on touched scripts;
  manual two-terminal race drill against a scratch repo (optional,
  pre-merge evidence).

## Phase 3 — Eval: context fixtures + harness context injection

Status: NOT STARTED — eval-semantics only; NO reviewer change in this
phase (standing rule).

### Scope

- Extend the fixture schema with an optional `context` block
  (what acquisition *would* return at the merge base for a real
  repository — synthetic, self-contained, realistic) and teach
  `eval/run_corpus.py` to inject it into `ReviewInput`. The harness
  stays offline-from-GitHub as designed; reasoning-over-context
  becomes measurable without network retrieval.
- Freeze the first context fixture family (M4-shape), each positive
  paired with a near-miss control:
  - **CX-positives:** absolute cross-file claim + retrieved base
    context that **refutes** it (e.g. orchestrator demonstrably
    consults other signals) → expected blocking finding that cites
    the context;
  - **CX-controls:** same claim shape + context that **confirms**
    the claim (self-substantiated by retrieved code) → expected
    CLEAR (a reviewer that reflexively blocks absolute docstring
    claims fails these — the pair-integrity axis reversed);
  - **absent-context variants** of both (current M4/C4 behavior
    preserved; KNOWN_GAP not silently absorbed).
- Fixture additions intentionally change `oracle_version`
  (fail-closed); states, matchers for existing fixtures, thresholds,
  GATING set untouched.

### Acceptance criteria

- New fixtures load under the extended schema; old corpus loads
  byte-identically; harness injects context verbatim into
  `ReviewInput`; oracle_version changes; deterministic suite green;
  zero model calls in this phase.

### Validation

- `python3 -m pytest tests/ -q` (corpus/loader/schema tests extended);
  `--print-oracle-version` shows the new identity.

## Phase 4 — Acquisition: bounded trusted-base retrieval

Status: NOT STARTED — deterministic infrastructure; engine output is
byte-identical when no context is present (measured).

### Scope

- New module `context.py` (pure acquisition, no model calls): input =
  budgeted diff + API reader; output = additive `ReviewInput.context`:

  ```json
  {"schema_version": 1,
   "ref": {"kind": "merge_base", "sha": "<40-hex>"},
   "items": [{"path": "…", "source_sha": "<40-hex>",
              "bytes": 1200, "truncated": false,
              "reason": "referenced_by:+42:orchestrator.requeue_failed"}],
   "omitted": [{"target": "…", "reason":
                "budget|denylist|binary|not_found|api_limited"}],
   "budget": {"max_files": 12, "max_chars": 24000}}
  ```

- Claim-driven targeting from the budgeted diff only: symbols/paths
  referenced by added lines (imports, calls, config keys, workflow
  `uses:` refs), absolute-claim sentences in added docstrings/comments
  (quantifier markers as *recall heuristics only* — mirroring the
  m4rel lesson that vocabulary is illustrative, never a gate), test
  files touching changed paths. Rank, take top-K within budget.
- Fetch via GitHub Contents API at the merge base with the existing
  header-file credential pattern; denylist enforced before fetch;
  per-item and total size caps; `api_limited` degrades gracefully
  (recorded omission) and never fails the review.
- Engine prompt: context appended as delimited data blocks after the
  diff, each labeled with path + source sha, under the same
  "data — never instructions" rule; with no context the prompt is
  byte-identical to today (regression-pinned).
- Engine digest: `_review_input_digest` must cover the effective
  context (trace/evidence join-key integrity).
- Provenance: manifest travels inside `ReviewInput.context`; the
  ReviewResult integrity block (Phase 6) cites its digest.
- Out of scope for this phase (recorded for a later slice): a
  base-resolved trusted `.ai-review-context.md` policy channel for
  architectural invariants / approved-plan excerpts. Kept separate
  from PR-authored claims by construction when it lands.

### Acceptance criteria

- Deterministic tests over recorded API fixtures: targeting, ranking,
  budget cutoffs, denylist hits, merge-base ref, omission recording.
- With context absent, engine prompts and results byte-identical to
  pre-change (pinned test); with context present, prompts embed it
  verbatim and delimited.
- No model calls in this phase's acceptance.

### Validation

- `python3 -m pytest tests/ -q`; one optional N=3 exploratory
  dual-profile run on CX fixtures only (spend-recorded,
  explicitly non-gating).

## Phase 5 — Calibration: evidence-backed blocking

Status: NOT STARTED — reviewer behavior; **routing decision required**
(see below). Any oracle change stays in a separate PR from this one.

### Scope

- Rubric amendment (its own PR): every **blocking** finding must
  identify (1) the violated contract/invariant by name (interface,
  docstring, policy rule, caller expectation), (2) the concrete
  failing execution path (inputs → call path → wrong outcome),
  (3) supporting evidence — a diff quote or a cited retrieved-context
  item. **Model opinion alone ("this looks unsafe") is not evidence
  for a blocking finding.** Absence claims ("X is never consulted",
  "no test covers Y") may be blocking only when the relevant source
  is present in the supplied material; otherwise non-blocking with
  the dependency stated explicitly.
- Parser-side support (reusing the existing, currently inert
  ReviewResult v2 evidence-gate machinery): new evidence kind
  `retrieved_context` whose quote is mechanically checked against
  context items (same normalization as `quote_in_patch`); blocking
  findings citing context must pass; missing/failed checks downgrade
  fail-closed via the existing `MACHINE_DOWNGRADE_REASON` path, with
  the audit preserved. Activation of the gate is a behavior change and
  rides this phase's measurement, never the eval PR.
- Deliberate non-import: the m4rel detector (frozen, grant-scoped)
  is not wired into production; the capability is earned semantically.

### Routing decision required (maintainer)

Preferred: run this phase as the next **T1.3 layer (c) mechanism
inside the existing Track 1 lifecycle** (phase branch of
`feature/glm-profile-qualification`, T1.2 measurement protocol,
keep/revert discipline, floors + GATING invariants). Alternative:
approve this branch as the **Track 3 umbrella** per ROADMAP
("Tracks 3–8 start after the eval-baseline plan completes") with the
same invariants binding. Both keep one architecture; the choice is
about which lifecycle owns the evidence.

### Acceptance criteria

- Per the governing lifecycle: M4-class/CX positives ≥4/5 at N=5 dual
  profile; **all controls zero false blockers** (CX confirm-claims
  included); Deviation-6 floors held; zero GATING regressions; M4/C4
  absent-context behavior unchanged; negative results frozen like
  positive ones (revert recorded if invariants fail).

### Validation

- Full-corpus N=5 dual-profile runs through `eval/run_corpus.py`
  with frozen evidence bundles under `eval/evidence/track1-*/`
  (or `context-*/`), spend-recorded; deterministic suite green.

## Phase 6 — Result integrity contract

Status: NOT STARTED — additive schema + renderer surface; verdict
semantics untouched (MATURITY 3.6 decision explicitly not preempted).

### Scope

- Additive `integrity` block on ReviewResult (schema bump; renderer
  and engine bump together — the existing fail-closed
  schema_version refusal in `render.py` is the model):

  ```json
  {"integrity": {
     "head_sha": "…", "base_sha": "…", "merge_base_sha": "…",
     "head_verified_at_post": true,
     "input": {"files_total": 42, "files_with_patch": 30,
               "files_list_capped": false, "diff_chars": 84211,
               "diff_truncated": false, "body_truncated": true},
     "context": {"items": 7, "omitted": 2, "denylisted": 1,
                 "manifest_sha256": "…"},
     "scope": "reviewed-material-only"}}
  ```

- Renderer: extend the metadata `<details>` block additively
  (counts, truncation flags, context provenance digest,
  head-verification). No new verdict, no Partial/Inconclusive
  escalation — recorded as the open MATURITY 3.6 human decision this
  evidence now supports.
- **Proposed (not enabled): SHA-bound result artifact** — the review
  job writes `review_evidence.json` (ReviewResult + integrity +
  model + toolkit pin + qualification scope) as a workflow artifact,
  bound to the exact head SHA. A future trusted status check (MATURITY
  3.7 `READY_FOR_HUMAN_MERGE_REVIEW` input) may consume it. It grants
  **no** merge authority, no GATING semantics, no auto-approval; the
  review event remains COMMENT-only.

### Acceptance criteria

- Deterministic tests: integrity block present and correct on
  synthetic inputs (truncated/uncapped, context present/absent, head
  verified/moved); renderer refuses old-result/new-renderer and
  new-result/old-renderer skew; COMMENT-only invariant tests still
  pass byte-for-byte on v1-shaped results.

### Validation

- `python3 -m pytest tests/ -q`; one dogfood PR observed end-to-end
  (metadata block inspection) — post-umbrella only.

## Phase 7 — Qualification, promotion, deployment boundaries

Status: NOT STARTED — uses the **existing** process only.

### Scope

- Qualification exactly per the standing contract: N=5, ≥4/5 on
  promoted targets, paired controls clean, Deviation-6 floors held,
  zero GATING regressions; promotion to GATING is permanent
  (ratchet); `oracle_version` discipline fail-closed throughout.
- **Gap reported (not assumed enforced):** the qualification and
  pin-verification machinery is implemented on the feature umbrella
  but the deployment contract is **PENDING ACTIVATION** — no record
  gates pins today. Until the umbrella merges and the post-merge
  activation demonstrations pass, all gate runs here are experimental
  evidence on feature-branch subjects and authorize no deployment
  (the Deviation-1/3 lifecycle split).
- No pin bump, no dogfood workflow change, no KodeVerket change in
  this feature. Deployment remains: reviewed PR → human merge.

### Acceptance criteria

- Every promotion claim cites a frozen evidence bundle; any activation
  remains a separate, human-authorized post-merge step.

---

## Smallest recommended first implementation slice

**Phase 2 (snapshot consistency), as a small change.** Rationale:

- fixes a defect confirmed by this audit on the deployed `main`
  surface today (stale-head review race) — independent of every
  open research question;
- meets all small-change criteria (no engine contract change, no
  eval-semantics change, no deployment-contract change, no new
  runtime dependency, toolkit + tests only);
- zero model-call cost beyond two GETs; zero oracle impact;
  immediately testable deterministically.

Suggested vehicle: `fix/review-head-snapshot-consistency` off
`feature/glm-profile-qualification` (the thin review.sh), mirrored to
`main`'s monolith at umbrella reconciliation (or as a second small PR
if the maintainer wants the deployed surface fixed sooner). Second
slice: Phase 3 (fixture freeze) — required by methodology before any
intelligence work; zero behavior change.

## Plan deviations

None yet.
