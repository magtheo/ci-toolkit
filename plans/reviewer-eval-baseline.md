# Reviewer Eval Baseline

Status: DRAFT rev 2 — revised 2026-08-29 per external plan review
(nine amendments: shared-core boundary, eval trust model, GATING vs
KNOWN_GAP, M4 ownership, M5 promotion, trigger set, eval profile
metadata, vocabulary). Awaiting maintainer approval — no
implementation before approval.

## Goal

Give the AI reviewer a measured quality baseline before any
intelligence change: a fixed eval corpus of recorded miss cases, a
replay harness (offline from GitHub, live to OpenRouter) that
replays them through the SAME semantic core production uses, and a
trusted-base CI gate that prevents any reviewer-behavior change from
merging without passing the corpus's GATING fixtures.

Turns "the reviewer seems better now" into "previously-failing
fixtures pass at the required stability, previously-passing fixtures
did not regress."

Origin: five confirmed miss classes (ledger in
student-platform:plans/ai-pr-review.md, misses #4/#5 recorded in its
PR #37); sequencing amendment to that plan's Deviation 2 — evaluation
baseline precedes intelligence changes (Stage 3 context retrieval
and Stage 2 diff budgeting wait behind this feature).

## Non-goals

- No change to reviewer intelligence in early phases: the
  consistency rule (phase 3) is the first and only behavior change,
  and it must pass the corpus first.
- No Stage 3 base-context retrieval, no Stage 2 diff budgeting.
- No online/runtime changes to review.sh semantics — Layer A
  (runtime validation) stays as-is.
- No GitHub transport in the eval path (no PR fetch, no review
  posting).
- No artifact/broker architecture for evaluating arbitrary PR-head
  prompt-generation code with the LLM secret — explicitly premature.
- No corpus hosting outside ci-toolkit; no external eval framework.

## Constraints

- **Fixture secrecy policy (hard)**: ci-toolkit is public;
  student-platform is private. Fixtures derived from private-repo
  misses (#1, #4, #5) MUST be synthetic replicas that reproduce the
  miss class without private content. Misses #2 (ci-toolkit #3) and
  #3 (ci-toolkit #7) may use the real public diffs.
- **Shared semantic core (no parallel reviewer)**: the eval must
  exercise the same model-facing pipeline production uses. Current
  review.sh mixes GitHub transport with the semantic core; phase 1
  extracts the core (input preparation -> OpenRouter call -> model
  output -> deterministic parser) into a shared invocation path used
  by BOTH production and eval. A fixture cannot be passed through
  today's transport-coupled review.sh as-is.
- **Eval trust invariant (hard)**: no PR-controlled executable code
  may run with the LLM secret. The CI eval therefore runs from the
  trusted base (same protection model as the production reviewer):
  the gate workflow executes harness code from base; the PR's
  candidate rubric/config/code is fetched as DATA only. Deterministic
  parser changes continue to run in ordinary secretless pull_request
  tests. `pull_request` + LLM_API_KEY is forbidden, full stop.
- **One-way boundary**: eval/ depends on the shared core, parser,
  rubric as black boxes; production never depends on eval/.
- **Fixture states**: every fixture is classified GATING (known
  capability; must never regress) or KNOWN_GAP (known failure;
  capability does not exist yet; owner recorded). Classification is
  MEASURED in phase 1, not guessed. Ratchet rule: once a capability
  is gained, its fixture is promoted to GATING permanently.
- **Nondeterminism policy (settled with maintainer, 2026-08-29)**:
  N=3 runs per fixture; a fixture requiring an expected finding
  passes if the finding (by stable matcher) appears in >=2 of 3
  runs; fixtures expected Clear must produce zero blocking findings
  across all runs (zero tolerance for false blockers).
- **Full-output fixtures**: assessment label, findings, severity —
  so the harness reports per-fixture stability statistics (e.g.
  "label matched 3/3"), the confidence measure for future Stratum
  evidence consumption.
- **Eval profile metadata**: every report carries the profile that
  produced it — toolkit SHA, rubric SHA, model ID, applicable
  generation parameters (temperature, max_tokens when set), fixture
  corpus version, N. Stability numbers are meaningless without it.
- **Cost policy**: no budget machinery; every run reports calls,
  tokens, approximate cost. Guards only if corpus exceeds ~50
  fixtures.

## Phase 1 — Corpus + shared semantic core + baseline classification

Status: NOT STARTED

### Scope

- Extract the model-facing semantic core from review.sh into a
  shared invocation path; production review.sh and the eval harness
  both call it. Behavior-preserving refactor: the existing test
  suite stays green and the next live review must be unchanged.
- `eval/fixtures/` — five fixtures, one per miss class:
  - M1 synthetic: caller uses `secrets: inherit` + praise risk
  - M2 real (ci-toolkit #3): pull_request + secret + floating ref
  - M3 real (ci-toolkit #7): guard contradicting documented contract
  - M4 synthetic: docstring contract false of unseen code (PR #35 class)
  - M5 synthetic: "Every X" claim vs in-diff exclusions (PR #36 class;
    regression reference: student-platform PR #36 head e51ee75e)
  - fixture format: input diff, rubric in force, expected assessment
    + findings (+ matchers), miss class, origin/synthetic flag
- `eval/run_corpus.sh` — replays fixtures through the shared core +
  parser (no GitHub transport), N runs per fixture, pass-policy
  evaluation, per-fixture stability stats, aggregate report, spend
  report, eval profile metadata.
- **Baseline classification run**: measure each fixture against the
  current reviewer and record GATING or KNOWN_GAP per fixture.
  Expected shape (to be confirmed by measurement, not assumption):
  M1–M3 plausibly GATING if currently caught; M4 KNOWN_GAP (owner:
  Stage 3 — requires repository context that does not exist); M5
  KNOWN_GAP (owner: this feature, phase 3).

### Acceptance criteria

- `eval/run_corpus.sh` runs the full corpus locally (OpenRouter
  live, GitHub absent) and exits nonzero iff any GATING fixture
  violates the pass policy.
- Report includes per-fixture: assessment, label stability, finding
  stability, state (GATING/KNOWN_GAP), spend; report header carries
  the eval profile metadata.
- Every fixture has a measured classification recorded; M4's entry
  names Stage 3 as owner.
- No private-repo content appears in eval/ (checked by review).
- Production refactor verified: existing tests green; observed live
  review on the phase PR unchanged in behavior.

### Validation

- `./tests/run` green before and after the core extraction.
- Corpus run reproduces the recorded baseline report.

## Phase 2 — Secure CI evaluation (trusted base)

Status: NOT STARTED

### Scope

- Gate workflow executing from the trusted base (pull_request_target
  protection model): harness + secret live in base; PR candidate
  rubric/config fetched as data. No PR-head executable code receives
  LLM_API_KEY.
- Trigger: pull_request path-filtered to the reviewer-behavior
  inputs — review.sh (transport shell), the shared core, parse_review.py,
  rubric.md, .github/workflows/ai-review.yml (owns the model default
  routed into AI_REVIEW_MODEL — a model change is a behavior change),
  the gate workflow itself, and eval/**.
- Required branch-protection check on main. Gate verdict reflects
  GATING fixtures only; KNOWN_GAP fixtures are reported, not gating:

  ```text
  Gating fixtures:     x/x passing
  Known gaps:          0/2 passing (M4, M5 — reported)
  Overall gate:        PASS
  ```

### Acceptance criteria

- A PR touching reviewer-behavior inputs cannot merge on a GATING
  fixture failure.
- A PR not touching them spends nothing (verified with a
  templates/README-only PR).
- Gate integrity: PR modifications to the gate workflow take effect
  only after merge (trusted-base semantics), same as the production
  reviewer.

### Validation

- One deliberate red run (GATING fixture forced fail) and one green
  run observed in CI before the check becomes required.

## Phase 3 — First gated behavior change: consistency rule (M5)

Status: NOT STARTED

### Scope

- Rubric amendment: absolute behavioral claims must be qualified
  against exceptions, filters, guards present in the same diff;
  unqualified absolutes are a finding.
- No parser changes expected; if needed, parser changes are in scope
  only for expressing this rule.

### Acceptance criteria

- M5 passes at policy (expected finding in >=2/3 runs).
- No GATING fixture regresses.
- **Promotion recorded: M5 KNOWN_GAP -> GATING** (permanent ratchet).
- M4 remains KNOWN_GAP, owner Stage 3 — explicitly NOT required to
  pass.
- Pin-bump PRs in consumer repos pick this up via the normal
  deliberate upgrade procedure (old pin reviews the bump).

### Validation

- Corpus run shows the promotion delta; observed live review on the
  bump PR.

## Phase 4 — Drift detection + profile reporting + Stage 3 handoff

Status: NOT STARTED

### Scope

- Scheduled (e.g. monthly) corpus re-run on the unchanged deployed
  reviewer; report stability deltas (model/routing drift early
  warning), each report stamped with eval profile metadata.
- Confidence stats (blocking recall, false-blocker rate, stability
  per profile) packaged as input to the future Stage 3 plan
  (base-context retrieval), which remains a separate feature.

### Acceptance criteria

- One scheduled run observed; drift report artifact exists with
  profile metadata.
- Stage 3 plan (when written) references corpus stats by profile.

### Validation

- Manual inspection of first two scheduled reports.

## Plan deviations

(none yet — rev 2 revisions were pre-approval review feedback on a
draft, not deviations from an approved plan)

## Notes

- Sequencing dependency: student-platform plans/ai-pr-review.md
  Deviation 2 amendment (evaluation precedes intelligence) should
  land alongside this plan's approval; this plan implements it.
- Governance dogfood gap: ci-toolkit ships governance templates but
  has not installed its own AGENTS.md/plans/PR-template/ROADMAP.
  That bootstrap is a separate small change, not part of this
  feature.
- The still-queued dogfood pin bump (main advanced past c328fee8)
  is unrelated routine maintenance and may land before phase 1.
