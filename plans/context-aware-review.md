# Context-Aware Review Reliability

Status: rev 2 (2026-10-23) — routing decision recorded from the PR #110
planning review: **Track 1 lifecycle, T1.3 layer (c); no Track 3
umbrella.** Implementation remains NOT BEGUN; no model campaign run;
PR #110 stays a draft design proposal until its plan reflects this
revision (it does, as of rev 2). No deployment or pin-promotion claim
is made or implied beyond current evidence.

Branch basis: `feature/glm-profile-qualification` @ `e08b618`
(merge of PR #108). `main` @ `1ae4287`.

Rev 2 amendments (maintainer-directed, recorded in Plan deviations):
Track 1/Track 3 ownership split; isolated `main` transport hotfix
scope; engine-reconciliation prerequisites; corrected phase sequence;
context-evidence requirements (denylist as defense in depth; manifest
is not coverage proof; integrity gate must distinguish meaningful
missing context from complete reviews; no trusted status check enabled
in this work).

## Goal

Let the advisory reviewer evaluate a PR against the **actual trusted
project context it touches** — existing code, callers, interfaces,
tests, architectural invariants and approved plans — so that
cross-file contract claims (the measured M4 class, 0/10 detections in
the frozen baseline) become checkable instead of unverifiable,
**without** weakening the paired-control discrimination discipline and
without raising the false-blocker rate.

Mechanism: ROADMAP **Track 3/4 capability**, delivered through the
already-admitted **T1.3 candidate layer (c): "evidence representation —
enrich ReviewInput context/budgeting so the model can ground rather
than guess"** — i.e., context enrichment is used *for discrimination*
inside Track 1's existing lifecycle. M4-class cross-file *detection*
remains owned by Track 3/4 with its own acceptance and promotion path,
and is explicitly **not** absorbed into the Track 1 exit obligation.

## Track 1 / Track 3 ownership and acceptance matrix

The two capability tracks share acquisition infrastructure but never
share fixtures, gates, exit criteria, or promotion records.

| | Track 1 — discrimination via context enrichment | Track 3/4 — cross-file (M4-class) detection |
| --- | --- | --- |
| Capability claim | Fewer false blockers on the **existing in-scope discrimination families**, because the model can ground instead of guess | Genuine cross-file contract defects detected when trusted base context is available |
| Owning lifecycle | ACTIVE Track 1 loop: T1.3 layer (c) → T1.4 holdout → T1.5 gate | Roadmap Track 3/4 stage, scheduled by the maintainer **after** Track 1 per ROADMAP ordering ("Tracks 3–8 start after the eval-baseline plan completes") |
| Fixtures used | T1 corpus families only (speculative-consequence, hallucinated-fact, absolute-consistency, severity-inflation, risk-boilerplate), with enrichment available on the same fixtures | CX family (context-refuted positives / context-confirmed controls) + absent-context M4/C4 variants — a separate, Track-3-owned fixture set |
| Acceptance criteria | T1.3 stage exit **verbatim, unchanged**: every confirmed in-scope family separates; M5 ≥4/5 with C5 clean; Deviation-6 floors held on both profiles (haiku 51/90, sonnet 66/90); zero GATING regressions (C4/C5/C7); keep/revert discipline | ROADMAP Track 3 acceptance, applied to CX fixtures: M4-class detections ≥2/3 (promotion-grade: N=5 ≥4/5) **with no increase in control false-blocks**; absent-context M4 behavior unchanged (KNOWN_GAP preserved until separately qualified) |
| Promotion | Existing Track 1 machinery only (T1.4 holdout → T1.5 → Phase 4/5 handoff) | Its own future qualification run + promotion PR via the standard loop and permanent ratchet |
| What this plan does NOT do | Does **not** add M4 ≥4/5 (or any CX criterion) to the T1.3 exit; does not let CX results count toward Track 1 gates | Does not begin before Track 1 work reaches its lifecycle boundary, unless the maintainer explicitly schedules it |

Corollaries (test-pinned when implemented): Track 1 qualification
records never cite CX fixtures; Track 3 qualification records never
relax Track 1 invariants; a single acquisition module feeding both is
infrastructure reuse, not shared authority.

## Relationship to the existing program (reconciliation)

- **One engine, one pass.** Context acquisition is a deterministic
  pre-model stage that *extends* `ReviewInput v1` with an additive,
  optional `context` field (plan constraint: "Stage 2/3 EXTEND these
  contracts — never a parallel execution path"). Semantic reasoning
  stays the single engine pass. Acquisition and reasoning are
  separable so the oracle can evaluate them independently.
- **The frozen v21 evidence layer is untouched.** This feature neither
  imports nor modifies `eval/v21_m4_relation.py` (SHA-pinned
  `1a01d8ff…`, grant-scoped preservation-only authority), the psd
  authority, the failed dsc family, the V2/PC2 reduction policy
  (UNRESOLVED by design), or any grant registry. m4rel is a
  vocabulary-tuned *witness relation* over recorded runs with no
  runtime authority; the reviewer must earn cross-file capability
  semantically, not by importing the detector.
- **Eval discipline unchanged.** New fixtures freeze BEFORE behavior
  changes; fixture/context-schema additions change `oracle_version`
  and fail closed; oracle changes never share a PR with reviewer
  behavior (standing rule).
- **Branch/PR lifecycle (rev 2).** PR #110 remains a draft design
  proposal and is **never merged** into `feature/glm-profile-qualification`
  as an implicit branching-policy exception. Accepted implementation
  is rehomed into authorized phase branches of the active umbrella
  (and, for the `main` hotfix, a `fix/*` small-change branch), per
  AGENTS.md.

## Non-goals

- No multiagent pipeline, no second model pass, no model change, no
  provider change, no vector-database/RAG infrastructure, no repo
  clone on the runner (GitHub API only), no PR-head retrieval.
- No change to the security model: GitHub-API-only data access, no
  PR-head checkout/execution, credential header-file transport, fork
  skip, COMMENT-only advisory event, human merge authority.
- No automatic merge authorization, **no trusted status check enabled**,
  no GATING change without measured qualification, no consumer pin
  bump, no KodeVerket production-workflow change.
- No whole-repo dumps: retrieval is bounded, claim-driven, and
  budgeted; omitted material is recorded, not silently dropped.
- No adoption of the V2 bare-scope reduction, no resolution of PC2,
  no grant-registry writes.
- No deployment or pin-promotion claims beyond current evidence: the
  deployment contract is PENDING ACTIVATION (Phase 1 finding 1.5);
  nothing in this feature activates or presumes it.

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
4. **Denylist is defense in depth, not a guarantee.** It excludes
   known secret-bearing path patterns (`.env*`, `*.pem`, `*.key`,
   `id_*`, `*credential*`, `.git/**`, token/session dirs, …) from
   retrieval, but retrieved base code can still contain sensitive
   material; consumers accept retrieved-base content going to the
   model provider on the same footing as diff content. Recorded
   denylist hits are omissions, never fetched.
5. PR head/base consistency: a review is never knowingly posted
   against a moved head (Phase 2 hotfix narrows the window; honest
   limits documented there). Any downstream decision consuming review
   output must validate the exact current head SHA against the
   review's `commit_id`.
6. Unsupported or materially missing context stays **visible as a
   limitation** (integrity block, Phase 6), never silently absorbed
   into Clear; **a context manifest is provenance, not proof of
   sufficient coverage.**
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
  KNOWN_GAP, owner "Stage 3" — Track 3/4 per the ownership matrix.
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
  context enrichment is layer (c) input for that same loop, not a
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
  fail-closed, but the consumer-visible failure semantics differ.
  **Reconciled before context-retrieval behavior work (Phase 2).**
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
  OpenRouter key; not available in this environment; not run now per
  the review boundary):**

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
| Cross-file/M4 misses | **Scheduled** — ROADMAP Track 3/4 (owner per the ownership matrix; not a T1.3 exit criterion) |
| False-blocker / discrimination | **In flight** — Track 1/T1.3 active; 3 mechanisms rejected; layer (c) = this plan's mechanism; layer (d) designed separately if earned |
| Same-diff consistency (M5) | **Blocked** — Phase 4 BLOCKED by plan Deviation 2; resumes after the Track 1 exit (T1.5 handoff). M5 KNOWN_GAP; its control C5 is GATING and must stay clean |
| State/lifecycle (M8), external contracts (M7), invariants (M6 family) | KNOWN_GAP families, owners recorded in ROADMAP tracks 5–7; not this feature |
| Truncation visible in result | **Scheduled** — MATURITY 3.6 (this plan Phase 6 implements the marker layer; verdict semantics remain 3.6's human decision) |
| SHA-bound decision state | **Scheduled** — MATURITY 3.7 (this plan Phase 6 produces its evidence input only; nothing enabled) |
| Head/base snapshot race | **Not scheduled anywhere** — new finding (this plan Phase 2, isolated `main` hotfix) |
| Secret-avoidance for retrieved context | **Not scheduled anywhere** — new (this plan Phase 4; denylist as defense in depth) |
| Engine-path divergence (main vs feature transport semantics) | **Blocked** → unblocked by this plan's Phase 2 reconciliation prerequisite |
| Eval→deployment activation | **Blocked** — umbrella merge + post-merge live demonstrations (Deviations 1/3); gap reported in 1.5 |

---

## Phase 2 — Isolated `main` transport hotfix: head-staleness guard

Status: NOT STARTED — **first implementation slice.** Small change,
deployed-surface only, no model calls added beyond two cheap GETs, no
engine-contract change (none exists on `main`), no eval-semantics
change, no `ReviewInput` extension.

### Scope (narrow, hotfix only)

- Target: `main`'s deployed monolithic `review.sh` — the surface
  consumers pin today.
- Branch `fix/review-head-staleness-guard` from verified `main`
  (confirm the base landed: `gh pr view`/`mergedAt` non-null per the
  branching-from-verified-state rules); PR → `main`.
- Two fail-closed checks, both comparing against the captured
  `head_sha`:
  1. **after file acquisition** (pagination complete), re-`GET
     /pulls/{n}`; head moved → abort **before the model call** with a
     distinct exit code and a step-summary notice ("head advanced
     during fetch; review skipped; the next run reviews the new
     head");
  2. **immediately before the POST**, re-`GET` once more; head moved
     → abort before posting, notice naming both the stale and current
     SHAs. A posted review's `commit_id` is then always the exact
     current head at post time.
- **Excluded from the hotfix (stays in feature work):** the
  `ReviewInput.merge_base_sha` field, compare-API merge-base lookup,
  any context retrieval, any renderer/schema change.
- **Honest limitation, documented in the hotfix itself (script
  comment + PR description):** pre/post checks narrow the race window
  but **cannot guarantee atomic snapshot consistency** with an
  unpinned files endpoint — a push completing after the final check
  is undetectable; the diff could theoretically mix heads. The guard
  converts an unbounded window into a tiny, bounded one and makes
  staleness explicit; it does not make the snapshot atomic.
- Downstream rule carried in the notice and in this plan: any
  consumer of the review (human or machine) must validate the
  review's `commit_id` against the exact current head SHA before
  relying on it.

### Acceptance criteria

- Deterministic tests (no network, no model calls) demonstrate head
  movement in **both windows**: (a) during file acquisition
  (pagination loop), and (b) during model execution (between the
  model call and the POST): no model call in (a); no POST in (b);
  distinct exit codes and notices in both; stable-head path unchanged.
- Source-level invariant tests assert the guard's presence and that
  abort paths never post.
- No change to prompts, rubric, review payload semantics, or
  transport behavior otherwise; `bash -n` green; existing suite green.

### Validation

- `python3 -m pytest tests/ -q` (on `main`'s suite); `bash -n
  review.sh`; PR description states the atomicity limitation verbatim.

## Phase 3 — Engine reconciliation prerequisites (before any context behavior)

Status: NOT STARTED — removes the audited main/feature divergence so
context-retrieval behavior work builds on ONE reconciled engine path
with no silent regression of deployed semantics.

### Scope

- Design + implement, on an authorized phase branch of the active
  umbrella: bring the feature branch's engine path to **behavioral
  parity with `main`'s deployed transport semantics** — model
  profiles (`model_profiles.json`), reasoning-model request shape,
  structured output where profiled, envelope classification, the
  single budget-escalation policy, transport reason codes, and
  INCONCLUSIVE-on-exhaustion/decoration — by wiring the extracted
  engine to `transport.py` (or an explicitly reviewed equivalent),
  keeping `review.sh` thin.
- **Behavior-preservation evidence matrix** over the recorded response
  classes × profile kinds (default + reasoning-profile), anchored on
  `tests/fixtures/openrouter/*.json` (valid, reasoning-only, partial
  truncation, refusal, error envelope) and main's pinned invariants
  (default-profile request body object-for-object identical;
  parser-vs-transport verdict ownership unchanged; decorate refuses
  non-INCONCLUSIVE payloads):
  1. successful content — request shape and normalized result;
  2. 200 with empty/no final content;
  3. refusal (`finish_reason: content_filter`);
  4. budget exhaustion incl. partial-JSON truncation
     (`finish_reason: length`) → escalation, then posted INCONCLUSIVE
     with `OUTPUT_BUDGET_EXHAUSTED`;
  5. transport failure / retry exhaustion → hard failure;
  6. malformed envelope → `UPSTREAM_ERROR` reason code.
- Every residual divergence is either preserved byte-for-byte or
  explicitly reviewed as a change, recorded per class in the phase PR
  description. **No silent regression of deployed semantics.**

### Acceptance criteria

- The matrix is executed deterministically (fixture-driven, **zero
  model calls**) and green; each class shows pre/post behavioral
  equivalence (or the reviewed, recorded delta).
- Consumer-visible semantics of the deployed reviewer (assessment
  vocabulary, INCONCLUSIVE reason codes, failure states) unchanged.

### Validation

- `python3 -m pytest tests/ -q` with new matrix tests; goldens for the
  default-profile request body; no live calls in acceptance.

## Phase 4 — Eval: enrichment fixtures + harness context injection

Status: NOT STARTED — eval-semantics only; NO reviewer change in this
phase (standing rule).

### Scope

- Extend the fixture schema with an optional `context` block
  (what acquisition *would* return at the merge base for a real
  repository — synthetic, self-contained, realistic) and teach
  `eval/run_corpus.py` to inject it into `ReviewInput`. The harness
  stays offline-from-GitHub as designed.
- **Two separately owned fixture sets (per the ownership matrix):**
  - **Track 1 enrichment variants** — discrimination-family fixtures
    (existing T1.1 families) with enrichment available, owned by
    Track 1, feeding T1.3 layer-(c) measurement only;
  - **Track 3 CX family** — context-refuted positives (expected
    blocking finding citing the context) paired with
    context-confirmed controls (expected CLEAR — a reviewer that
    reflexively blocks absolute docstring claims fails these),
    plus absent-context M4/C4 variants; owned by Track 3/4, **never**
    counted toward Track 1 gates.
- Fixture additions intentionally change `oracle_version`
  (fail-closed); states, matchers for existing fixtures, thresholds,
  GATING set untouched.

### Acceptance criteria

- New fixtures load under the extended schema; old corpus loads
  byte-identically; harness injects context verbatim into
  `ReviewInput`; fixture-set ownership is machine-checkable (Track 1
  gate runs cannot silently include CX fixtures and vice versa);
  oracle_version changes; deterministic suite green; zero model calls
  in this phase.

### Validation

- `python3 -m pytest tests/ -q` (corpus/loader/schema/ownership tests
  extended); `--print-oracle-version` shows the new identity.

## Phase 5 — Acquisition: bounded trusted-base retrieval

Status: NOT STARTED — deterministic infrastructure; engine output is
byte-identical when no context is present (measured). Serves both
tracks; confers no capability by itself.

### Scope

- New module `context.py` (pure acquisition, no model calls): input =
  budgeted diff + API reader; output = additive `ReviewInput.context`
  **and** the `ReviewInput.merge_base_sha` field (moved here from the
  hotfix per the rev 2 split):

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
  ReviewResult integrity block (Phase 7) cites its digest.
  **The manifest records what was retrieved and omitted; it is
  provenance, not evidence that coverage was sufficient.**
- Out of scope for this phase (recorded for a later slice): a
  base-resolved trusted `.ai-review-context.md` policy channel for
  architectural invariants / approved-plan excerpts. Kept separate
  from PR-authored claims by construction when it lands.

### Acceptance criteria

- Deterministic tests over recorded API fixtures covering: **retrieval
  selection** (targeting/ranking), **file revisions** (each item's
  `source_sha` is the exact merge-base blob), **pagination
  consistency** (multi-page changed-file inputs yield complete
  candidate sets), **omitted material** (budget cutoffs, binary,
  not-found, api_limited all recorded), and **confidentiality
  boundaries** (denylist hits recorded, never fetched; denylist
  documented as defense in depth).
- With context absent, engine prompts and results byte-identical to
  pre-change (pinned test); with context present, prompts embed it
  verbatim and delimited.
- No model calls in this phase's acceptance.

### Validation

- `python3 -m pytest tests/ -q`; one optional N=3 exploratory
  dual-profile run on enrichment fixtures only (spend-recorded,
  explicitly non-gating; requires the human key — none run yet).

## Phase 6 — Calibration: evidence-backed blocking (T1.3 layer (c))

Status: NOT STARTED — reviewer behavior on the **Track 1 lifecycle**.
Any oracle change stays in a separate PR from this one.

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
- Measured **as the next T1.3 mechanism**: T1.2 protocol, keep/revert
  lifecycle, negative results frozen like positive ones. M4/CX
  outcomes are diagnostics here, never exit criteria (ownership
  matrix).
- Deliberate non-import: the m4rel detector (frozen, grant-scoped)
  is not wired into production; the capability is earned semantically.

### Acceptance criteria

- Exactly the T1.3 stage exit, unchanged: every confirmed in-scope
  family separates across the complete development corpus (excluding
  holdout); M5 ≥4/5 with C5 clean; Deviation-6 floors held on both
  profiles; zero GATING regressions; no CX/M4 criterion added.
- On failure: full revert with restoration audit, negative result
  frozen under `eval/evidence/`.

### Validation

- Full-corpus N=5 dual-profile runs through `eval/run_corpus.py`
  (Track 1 corpus + enrichment variants) with frozen evidence bundles;
  deterministic suite green. **No large campaign runs until the human
  review boundary passes.**

## Phase 7 — Result integrity contract

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
                 "manifest_sha256": "…",
                 "coverage_claim": "scope-only"},
     "assessment_scope": "reviewed-material-only"}}
  ```

- **Meaningful-missing-context honesty:** the block must let a reader
  distinguish *meaningful missing context* (targeted claims with no
  retrievable witness, retrieval degraded/limited, omissions on
  claimed paths) from a *complete review*; coverage fields are scope
  statements, never completeness claims. What verdict (if any)
  missing context should escalate to remains MATURITY 3.6's human
  decision — this phase only makes the evidence visible.
- Renderer: extend the metadata `<details>` block additively
  (counts, truncation flags, context provenance digest,
  head-verification). No new verdict, no Partial/Inconclusive
  escalation in this phase.
- **Proposed (not enabled): SHA-bound result artifact** — the review
  job writes `review_evidence.json` (ReviewResult + integrity +
  model + toolkit pin + qualification scope) as a workflow artifact,
  bound to the exact head SHA. A future trusted status check (MATURITY
  3.7 `READY_FOR_HUMAN_MERGE_REVIEW` input) may consume it. **No
  trusted status check, merge authorization, GATING semantics, or
  auto-approval is enabled by this work**; the review event remains
  COMMENT-only.

### Acceptance criteria

- Deterministic tests: integrity block present and correct on
  synthetic inputs (truncated/uncapped, context present/absent,
  head verified/moved, meaningful-missing-context markers);
  renderer refuses old-result/new-renderer and new-result/old-renderer
  skew; COMMENT-only invariant tests still pass byte-for-byte on
  v1-shaped results.

### Validation

- `python3 -m pytest tests/ -q`; one dogfood PR observed end-to-end
  (metadata block inspection) — post-umbrella only.

## Phase 8 — Qualification, promotion, deployment boundaries

Status: NOT STARTED — uses the **existing** process only.

### Scope

- Qualification exactly per the standing contract: N=5, ≥4/5 on
  promoted targets, paired controls clean, Deviation-6 floors held,
  zero GATING regressions; promotion to GATING is permanent
  (ratchet); `oracle_version` discipline fail-closed throughout.
  Track 1 and Track 3 qualifications are separate records (ownership
  matrix); neither cites the other's fixtures.
- **Gap reported (not assumed enforced):** the qualification and
  pin-verification machinery is implemented on the feature umbrella
  but the deployment contract is **PENDING ACTIVATION** — no record
  gates pins today. Until the umbrella merges and the post-merge
  activation demonstrations pass, all gate runs here are experimental
  evidence on feature-branch subjects and authorize no deployment
  (the Deviation-1/3 lifecycle split). **No deployment or
  pin-promotion claim is made beyond current evidence.**
- No pin bump, no dogfood workflow change, no KodeVerket change in
  this feature. Deployment remains: reviewed PR → human merge.

### Acceptance criteria

- Every promotion claim cites a frozen evidence bundle; any activation
  remains a separate, human-authorized post-merge step.

---

## Corrected sequence of phase PRs

```text
1. fix/review-head-staleness-guard      -> main      (Phase 2 hotfix;
   small change; no ReviewInput extension; race-window limits documented)
2. engine-reconciliation design PR      -> active-umbrella phase branch
3. engine-reconciliation implementation -> same phase lifecycle
   (Phase 3; fixture-driven evidence matrix; zero model calls)
4. enrichment + CX fixture freeze       -> eval-semantics PR
   (Phase 4; oracle bump fail-closed; ownership tests)
5. acquisition infrastructure           -> phase PR (Phase 5;
   deterministic; byte-identical when absent)
6. T1.3 layer-(c) mechanism             -> phase PR (Phase 6; rubric +
   gate activation; measured under T1.2 protocol; keep/revert)
7. T1.4 holdout / T1.5 gate             -> EXISTING Track 1 lifecycle,
   unchanged
8. Track 3/4 CX qualification           -> separate, maintainer-
   scheduled; own gates and records
9. result-integrity block + artifact    -> phase PR (Phase 7; additive;
   nothing enabled)
```

Boundaries: oracle changes never share a PR with reviewer behavior;
each PR targets the branch its work belongs to (hotfix → `main`,
phases → the active umbrella's authorized phase branches); PR #110
stays draft and is never merged as an umbrella; no broad
context-retrieval implementation and no new large model campaign until
the human review boundary passes.

## Smallest recommended first implementation slice

**Phase 2 — the isolated `main` head-staleness hotfix.** Rationale:
fixes a defect confirmed by this audit on the deployed `main` surface
today; meets all small-change criteria; zero semantic/oracle impact;
honest, bounded improvement (window narrowing, not atomicity). The
`merge_base_sha` interface change stays out of the hotfix and lands
with Phase 5.

## Plan deviations

### rev 2 — routing decision and review corrections (PR #110 planning
review, directing human, 2026-10-23)

1. **Routing:** context-retrieval behavior work runs inside the
   existing Track 1 lifecycle as T1.3 layer (c); no Track 3 umbrella
   is created. M4 cross-file detection remains Track 3/4-owned with
   separate acceptance/promotion; M4 ≥4/5 (and any CX criterion) is
   NOT a T1.3 exit criterion. Ownership matrix added; T1.4/T1.5
   sequencing, paired controls, Deviation-6 floors, GATING invariants,
   and keep/revert rules preserved verbatim.
2. **Hotfix split:** the snapshot-consistency fix is scoped narrowly
   against deployed `main`; the `ReviewInput.merge_base_sha` extension
   moved to Phase 5 (feature work); required test windows (head
   movement during acquisition and during model execution) and the
   honest non-atomicity limitation are now explicit; downstream
   consumers must validate the exact current head SHA.
3. **Engine reconciliation** inserted as Phase 3 prerequisite, with
   the behavior-preservation matrix (successful content, empty
   content, refusal, budget exhaustion, transport failures) required
   before context-retrieval behavior work; no silent regression of
   deployed semantics.
4. **Evidence requirements** sharpened: denylist = defense in depth,
   not a guarantee; context manifest = provenance, not coverage
   proof; the future integrity gate must distinguish meaningful
   missing context from complete reviews; retrieval tests must cover
   selection, revisions, pagination consistency, omissions, and
   confidentiality boundaries; no trusted status check enabled.
5. **Branch/PR lifecycle:** PR #110 remains draft; accepted work
   rehomed into authorized phase branches per AGENTS.md; oracle
   changes never share a PR with behavior changes; no deployment or
   pin-promotion claims beyond current evidence.
