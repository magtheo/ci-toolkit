# Reviewer Eval Baseline

Status: DRAFT rev 3 — revised 2026-08-29 across three external review
rounds (rev 2: shared core, trust model, GATING/KNOWN_GAP; rev 3:
qualification-before-pin, independent oracle, paired controls,
stability vocabulary, profile-scoped qualification, explicit I/O
contract, trigger consistency, harness language freedom). Awaiting
maintainer approval — no implementation before approval.

## Goal

Give the AI reviewer a measured quality baseline before any
intelligence change, and gate DEPLOYMENT (not merge) on it:

- a fixed eval corpus of recorded miss classes paired with clean
  negative controls;
- a replay harness (offline from GitHub, live to OpenRouter) driving
  the SAME engine production uses, behind an explicit data contract;
- qualification runs against merged, trusted SHAs only — never
  PR-head code;
- consumer pin promotion requires qualification evidence.

Turns "the reviewer seems better now" into qualification evidence,
and makes "main is not deployment; the immutable consumer pin is
deployment" the load-bearing rule.

Origin: five confirmed miss classes (ledger in
student-platform:plans/ai-pr-review.md, misses #4/#5 recorded in its
PR #37); sequencing amendment to that plan's Deviation 2 — evaluation
baseline precedes intelligence changes (Stage 3 context retrieval
and Stage 2 diff budgeting wait behind this feature).

## Non-goals

- No change to reviewer intelligence in early phases: the
  consistency rule (phase 3) is the first and only behavior change.
- No Stage 3 base-context retrieval, no Stage 2 diff budgeting.
- No online/runtime changes to review.sh semantics — Layer A
  (runtime validation) stays as-is.
- No GitHub transport in the eval path (no PR fetch, no review
  posting).
- No artifact/broker architecture for evaluating PR-head code with
  the LLM secret — structurally unnecessary because qualification
  runs post-merge on trusted SHAs.
- No provider abstraction, plugin system, database, eval service,
  model routing, or external benchmark framework.
- No probability-like "confidence" output for Stratum or any
  consumer — not until the corpus is materially larger and
  representative. Vocabulary is: corpus detection stability,
  false-blocker count on controls, qualification evidence.

## Constraints

- **Fixture secrecy policy (hard)**: ci-toolkit is public;
  student-platform is private. Fixtures derived from private-repo
  misses (#1, #4, #5) MUST be synthetic replicas that reproduce the
  miss class without private content. Misses #2 (ci-toolkit #3) and
  #3 (ci-toolkit #7) may use the real public diffs.
- **Engine contract (explicit, versioned)**: the semantic core is
  defined by its data contract, not by "extracted code":

  ```text
  ReviewInput v1: title, body, files[{path,status,patch}],
                  trusted policy, model config, schema_version
  ENGINE:         budgeting/input selection, prompt construction,
                  model call, deterministic normalization
  ReviewResult v1: assessment, findings, usage, raw model output,
                   schema_version
  ```

  GitHub transport and eval both construct ReviewInput; neither
  changes what the engine means. Stage 2 budgeting and Stage 3
  context retrieval EXTEND these contracts — never a parallel
  execution path.
- **Trust invariants (hard)**:
  1. No PR-controlled executable code runs with the LLM secret.
     Ordinary PR CI is secretless and deterministic; there is NO
     LLM evaluation of PR-head code, ever.
  2. No reviewer SHA is deployed until it has qualification
     evidence. Pin-bump PRs (ci-toolkit dogfood or any consumer)
     must cite a PASS qualification record for the exact SHA.
     main may temporarily hold an unqualified SHA — safe because
     the dogfood reviewer itself is pinned.
- **Oracle independence (hard)**: reviewer-behavior changes and
  eval-oracle changes are separate PRs. GATING fixture IDs are
  immutable — never deleted, never demoted. Matchers, expectations,
  and thresholds cannot be weakened in the same change as the
  behavior they judge.
- **Paired controls**: every positive fixture has a minimally
  different clean control. Unexpected BLOCKING findings fail EVERY
  fixture, positive and control alike (an always-blocking reviewer
  must not pass the corpus). Unexpected advisories are tracked as
  noise from day one, not initially gated.
- **Fixture states**: GATING (known capability; must never regress)
  or KNOWN_GAP (known failure; capability absent; owner recorded).
  Classification is MEASURED in phase 1, not guessed. Ratchet:
  once promoted, a fixture is GATING permanently.
- **Thresholds**: routine regression runs N=3, expected finding in
  >=2/3. Promotion KNOWN_GAP -> GATING requires N=5, >=4/5
  detection, and zero false blockers on the paired control.
- **Profile-scoped qualification (semantic rule)**: qualification
  belongs to a profile = code SHA + protocol version + rubric hash
  + model ID + generation parameters + corpus version. A green
  qualification for one profile says nothing about any other; a
  custom model or repository rubric is an UNQUALIFIED profile until
  evaluated.
- **Full-output fixtures**: assessment label, findings, severity
  recorded per run, enabling per-fixture stability statistics.
- **Cost policy**: no budget machinery; every run reports calls,
  tokens, approximate cost. Ten fixtures x N is still cents.
- **Harness implementation**: language decided in phase 1. Structured
  fixtures, repeated runs, semantic matchers, aggregation, and
  reporting have crossed the point where Bash is obviously the
  simplest choice; Python is already present (parse_review.py).
  review.sh remains the thin GitHub transport.

## Permanent methodology rules (project-level, outlive this feature)

1. Every confirmed reviewer miss becomes a frozen regression fixture
   BEFORE the corresponding intelligence fix is made.
2. Every new detection rule ships with a paired clean control.
3. Promotion to GATING is permanent (ratchet).

## Phase 1 — Corpus + engine contract + harness + baseline

Status: NOT STARTED

### Scope

- Extract the engine behind ReviewInput v1 / ReviewResult v1
  (schema_version fields included); review.sh becomes thin GitHub
  transport. Behavior-preserving: existing tests green, next live
  review unchanged.
- `eval/fixtures/` — ten fixtures, five positive miss classes each
  paired with a minimally different clean control:
  - M1 synthetic: `secrets: inherit` + praise risk | C1: explicit
    secret mapping (clean)
  - M2 real (ci-toolkit #3): pull_request + secret + floating ref |
    C2: hardened pull_request_target caller, pinned refs
  - M3 real (ci-toolkit #7): guard contradicting its documented
    contract | C3: guard honoring the contract
  - M4 synthetic: docstring contract false of unseen code (PR #35
    class) | C4: docstring claim consistent with code visible in
    the same diff
  - M5 synthetic: "Every X" claim vs in-diff exclusions (PR #36
    class; regression reference: student-platform PR #36 head
    e51ee75e) | C5: properly qualified statement
  - fixture format: input diff, rubric in force, expected assessment
    + findings (+ matchers), miss class, origin/synthetic flag,
    pairing reference
- Harness (`eval/run_corpus` — language per this phase): replays
  fixtures through engine + parser (no GitHub transport), N runs,
  matchers, GATING/KNOWN_GAP evaluation, per-fixture detection
  stability, false-blocker counts, noise counts, spend report,
  profile metadata header.
- Baseline classification run: MEASURE every fixture (positives and
  controls) against the current reviewer; record states. Expected
  shape (confirmed by measurement only): M1–M3 plausibly GATING if
  currently caught; M4 KNOWN_GAP (owner: Stage 3 — requires
  repository context that does not exist); M5 KNOWN_GAP (owner: this
  feature, phase 3); controls failing via false blockers become
  KNOWN_GAP of the over-triggering kind.

### Acceptance criteria

- Corpus runs locally (OpenRouter live, GitHub absent) and exits
  nonzero iff a GATING fixture violates policy (including unexpected
  blocking findings on any fixture).
- Report includes per-fixture: assessment, detection stability,
  false-blocker count, advisory-noise count, state, spend; header
  carries the profile metadata.
- Every fixture has a measured classification; M4's entry names
  Stage 3 as owner.
- No private-repo content appears in eval/.
- Engine extraction verified behavior-preserving (tests green,
  observed live review unchanged).

### Validation

- `./tests/run` green before and after extraction.
- Corpus run reproduces the recorded baseline report.

## Phase 2 — Qualification on trusted SHAs (deployment gate)

Status: NOT STARTED

### Scope

- Qualification workflow triggered on merge to main (path-filtered
  to reviewer-behavior inputs), manually, and on schedule: executes
  MAIN's engine — trusted code — with the LLM secret over the full
  corpus; records a check run + report artifact against the SHA.
- Ordinary PRs: secretless deterministic tests only. No LLM eval of
  PR-head code, no pull_request + secret, no trusted-base PR-time
  LLM job (rev 2's trigger contradiction is resolved by removal).
- Deployment contract: a pin-bump PR anywhere must cite a PASS
  qualification record for the exact SHA + profile. The ci-toolkit
  dogfood pin follows the same rule; an unqualified main does not
  silently change review behavior because the dogfood reviewer is
  itself pinned.
- Reviewer-behavior input set (qualification trigger + secretless PR
  test scope): engine/core files, parse_review.py, rubric.md,
  review.sh, .github/workflows/ai-review.yml (owns the model default
  — a model change is a behavior change), the qualification workflow
  itself, eval/**.

### Acceptance criteria

- Qualification observed green on a merged good SHA and red on a
  deliberately broken one, before the deployment contract is relied
  upon.
- Pin-bump procedure (README/template) requires the qualification
  reference.
- Invariant verified: no workflow path executes PR-head code with
  the secret (review + test).

### Validation

- One green and one forced-red qualification run inspected.

## Phase 3 — M5 consistency rule (oracle-first sequence)

Status: NOT STARTED

### Scope

Three separate PRs, honoring oracle independence:
1. Oracle PR: M5 fixture + matcher land as KNOWN_GAP; no reviewer
   changes.
2. Behavior PR: rubric consistency rule (absolute behavioral claims
   must be qualified against in-diff exceptions/filters/guards;
   unqualified absolutes are a finding); oracle untouched.
3. Promotion PR: M5 KNOWN_GAP -> GATING; tiny; cites qualification
   evidence.

### Acceptance criteria

- M5 promotion threshold met: N=5, >=4/5 detection, zero false
  blockers on C5, no GATING regressions.
- M4 remains KNOWN_GAP, owner Stage 3 — explicitly NOT required.
- Consumer pin-bumps pick the change up via the normal deliberate
  procedure, citing qualification.

### Validation

- Qualification runs inspected at each of the three steps.

## Phase 4 — Drift detection + evidence handoff

Status: NOT STARTED

### Scope

- Scheduled corpus re-run against the DEPLOYED pin's profile (not
  merely main): stability deltas as model/routing drift early
  warning, stamped with profile metadata.
- Qualification evidence bundle for future Stage 3 / Stratum
  consumption:

  ```text
  reviewer_sha / profile / qualification: PASS
  corpus_version / qualified_at
  known_gaps: [M4]
  detection_stability: ... (never "confidence")
  ```

### Acceptance criteria

- One scheduled run observed; drift artifact exists with profile
  metadata.
- Stage 3 plan (when written) references corpus stats by profile.

### Validation

- Manual inspection of first two scheduled reports.

## Plan deviations

(none — rev 2/rev 3 revisions were pre-approval review feedback on
a draft, not deviations from an approved plan)

## Notes

- Sequencing dependency: student-platform plans/ai-pr-review.md
  Deviation 2 amendment (evaluation precedes intelligence) should
  land alongside this plan's approval; this plan implements it.
- Governance dogfood gap: ci-toolkit ships governance templates but
  has not installed its own AGENTS.md/plans/PR-template/ROADMAP.
  That bootstrap is a separate small change, not part of this
  feature.
- The still-queued dogfood pin bump (main advanced past c328fee8)
  is unrelated routine maintenance; under this plan it additionally
  becomes the first consumer of the qualification-citation contract
  once phase 2 exists. Until then it proceeds under the old
  review-only procedure.
