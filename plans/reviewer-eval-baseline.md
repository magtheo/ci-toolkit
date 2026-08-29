# Reviewer Eval Baseline

Status: rev 4 — APPROVED 2026-08-29 (maintainer merge of PR #8;
four external review rounds, final approval relayed via external
review of the chain #8/#37/#40/#41). Implementation may begin under
the phase workflow: phase branches target
feature/reviewer-eval-baseline.

Revision history: rev 4 — engine/oracle phase separation, engine vs
consumer-profile qualification levels, current-oracle deployment
invariant, subject/oracle record separation, machine-verifiable
promotion, ReviewResult purity (no GitHub rendering), duplicate M5
step removed.

## Goal

Give the AI reviewer a measured quality baseline before any
intelligence change, and gate DEPLOYMENT (not merge) on it:

- an independent eval oracle: recorded miss classes paired with
  clean negative controls, replayed (offline from GitHub, live to
  OpenRouter) through the SAME engine production uses;
- qualification of trusted merged SHAs against the CURRENT oracle;
- pin promotion that is mechanically verified, not cited by hand.

Turns "the reviewer seems better now" into qualification evidence,
and makes "main is not deployment; the immutable consumer pin is
deployment" the load-bearing rule.

Origin: five confirmed miss classes (ledger in
student-platform:plans/ai-pr-review.md, misses #4/#5 recorded in its
PR #37); sequencing amendment to that plan's Deviation 2 — evaluation
baseline precedes intelligence changes (Stage 3 context retrieval
and Stage 2 diff budgeting wait behind this feature).

## Non-goals

- No change to reviewer intelligence until phase 4 (the M5
  consistency rule is the first and only behavior change).
- No Stage 3 base-context retrieval, no Stage 2 diff budgeting.
- No online/runtime changes to review.sh semantics — Layer A
  (runtime validation) stays as-is.
- No GitHub transport or rendering in the eval path.
- No artifact/broker architecture for evaluating PR-head code with
  the LLM secret — structurally unnecessary because qualification
  runs post-merge on trusted SHAs.
- No consumer-profile qualification (Level B) implementation yet —
  terminology and record shape only.
- No protocol/policy rubric split implementation yet — anticipated
  in terminology only.
- No provider abstraction, plugin system, database, eval service,
  model routing, or external benchmark framework.
- No probability-like "confidence" output — vocabulary is: corpus
  detection stability, false-blocker count on controls,
  qualification evidence.

## Constraints

- **Fixture secrecy policy (hard)**: ci-toolkit is public;
  student-platform is private. Fixtures derived from private-repo
  misses (#1, #4, #5) MUST be synthetic replicas that reproduce the
  miss class without private content. Misses #2 (ci-toolkit #3) and
  #3 (ci-toolkit #7) may use the real public diffs.
- **Engine contract (explicit, versioned, semantically pure)**:

  ```text
  ReviewInput v1: title, body, files[{path,status,patch}],
                  trusted policy, model config, schema_version
  ENGINE:         budgeting/input selection, prompt construction,
                  model call, deterministic normalization
  ReviewResult v1: assessment, findings, usage, raw model output,
                   schema_version
  ```

  ReviewResult contains NO GitHub concepts — no event type, no
  inline-comment payloads, no <details> rendering, no commit_id.
  GitHub presentation is a RENDERER consuming ReviewResult; the eval
  scorer is another consumer. parse_review.py's current mix of
  semantic normalization and GitHub rendering is split at this
  boundary. The eval never evaluates rendered Markdown. Stage 2/3
  EXTEND these contracts — never a parallel execution path.
- **Trust invariants (hard)**:
  1. No PR-controlled executable code runs with the LLM secret.
     Ordinary PR CI is secretless and deterministic; there is NO
     LLM evaluation of PR-head code, ever.
  2. A reviewer can only be NEWLY DEPLOYED if it passes the
     CURRENT GATING oracle. main may temporarily hold an unqualified
     SHA — safe because the dogfood reviewer itself is pinned.
- **Oracle independence (hard)**: reviewer-behavior changes and
  eval-oracle changes are separate PRs/phases. GATING fixture IDs
  are immutable — never deleted, never demoted. Matchers,
  expectations, and thresholds cannot be weakened in the same change
  as the behavior they judge.
- **Paired controls**: every positive fixture has a minimally
  different clean control. Unexpected BLOCKING findings fail EVERY
  fixture, positive and control alike. Unexpected advisories are
  tracked as noise from day one, not initially gated.
- **Fixture states**: GATING (known capability; must never regress)
  or KNOWN_GAP (known failure; capability absent; owner recorded).
  Classification is MEASURED in phase 2, not guessed. Ratchet:
  once promoted, a fixture is GATING permanently.
- **Thresholds**: routine runs N=3, expected finding in >=2/3.
  Promotion KNOWN_GAP -> GATING requires N=5, >=4/5 detection, zero
  false blockers on the paired control, no GATING regressions.
- **Qualification semantics (two levels)**:
  - Level A — ENGINE QUALIFICATION (mandatory): subject =
    trusted merged toolkit SHA; covers runtime code + protocol +
    bundled rubric + model + generation settings, measured with
    `oracle_version`/`corpus_hash` (NOT a single rubric hash —
    fixtures carry their own rubric-in-force).
  - Level B — CONSUMER-PROFILE QUALIFICATION (later, optional):
    qualified engine + repository policy + model override +
    repository-specific evals. Until it exists, a consumer running
    a custom rubric/model is honestly exposed as
    "engine: QUALIFIED; repository profile: custom / not yet
    profile-qualified". It is never silently treated as globally
    qualified or globally worthless.
- **Qualification record**:

  ```text
  Qualification {
      subject_sha    # trusted merged ci-toolkit commit
      oracle_version # eval implementation + corpus version
      model_profile
      result
      timestamp
  }
  ```

  subject and oracle are INDEPENDENT: an old trusted subject can be
  re-qualified against a new oracle without a new toolkit commit or
  consumer pin bump. The qualification runner verifies the subject
  SHA is a trusted merged commit before executing it. A PASS against
  an oracle that is no longer current does not satisfy the
  deployment invariant for NEW promotions.
- **Machine-verifiable promotion**: pin-bump PRs are verified by a
  secretless check that reads the proposed SHA, queries the
  qualification record, and confirms subject match + result PASS +
  current oracle + acceptable model profile. The qualification
  workflow attaches its status to the toolkit commit; consumers
  verify cheaply. PR-description citation alone is not a control.
- **Full-output fixtures**: assessment label, findings, severity
  recorded per run, enabling per-fixture detection stability.
- **Cost policy**: no budget machinery; every run reports calls,
  tokens, approximate cost.
- **Harness implementation**: language decided in phase 2. Structured
  fixtures, repeated runs, semantic matchers, aggregation, and
  reporting favor Python (already present via parse_review.py).
  review.sh remains the thin GitHub transport.

## Permanent methodology rules (project-level, outlive this feature)

1. Every confirmed reviewer miss becomes a frozen regression fixture
   BEFORE the corresponding intelligence fix is made.
2. Every new detection rule ships with a paired clean control.
3. Promotion to GATING is permanent (ratchet).
4. A PR description that contradicts its contents is a defect —
   keep PR bodies current.
5. Qualification PASS means: preserved the capabilities encoded by
   the current oracle, under this profile. It NEVER means "the
   reviewer is correct." No corpus size proves general review
   correctness.

## Phase 1 — Engine contract

Status: NOT STARTED

### Scope

- Extract the engine behind ReviewInput v1 / ReviewResult v1
  (schema_version fields included). review.sh becomes thin GitHub
  transport; the GitHub renderer (comment body, <details>, inline
  payloads, event COMMENT, commit_id) becomes a separate consumer of
  ReviewResult. No eval work in this phase.

### Acceptance criteria

- Behavior-preserving: existing tests green (parser tests moved to
  the normalization/renderer split), observed live review unchanged.
- ReviewResult contains no GitHub-specific concepts (verified by
  test).

### Validation

- `./tests/run` green; one observed live review identical in form.

## Phase 2 — Independent oracle (fixtures, controls, harness, baseline)

Status: NOT STARTED

### Scope

- `eval/fixtures/` — ten fixtures, five positives each paired with a
  minimally different clean control:
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
- Harness (`eval/run_corpus`, language chosen here): replays
  fixtures through engine + normalization (no GitHub transport, no
  rendered Markdown), N runs, matchers, GATING/KNOWN_GAP evaluation,
  per-fixture detection stability, false-blocker counts, noise
  counts, spend report, oracle profile metadata.
- Baseline classification run: MEASURE every fixture; record states.
  Expected shape (confirmed by measurement only): M1–M3 plausibly
  GATING if currently caught; M4 KNOWN_GAP (owner: Stage 3); M5
  KNOWN_GAP (owner: this feature, phases 4–5); controls failing via
  false blockers become KNOWN_GAP of the over-triggering kind.

### Acceptance criteria

- Corpus runs locally (OpenRouter live, GitHub absent), exits
  nonzero iff a GATING fixture violates policy (including unexpected
  blocking findings on any fixture).
- Report: per-fixture assessment, detection stability, false-blocker
  count, advisory-noise count, state, spend; header carries oracle
  metadata (oracle_version/corpus_hash).
- Measured classification recorded; M4 names Stage 3 as owner.
- No private-repo content in eval/.

### Validation

- Local run reproduces the recorded baseline report.

## Phase 3 — Qualification infrastructure

Status: NOT STARTED

### Scope

- Qualification workflow: given a trusted merged subject SHA
  (verified merged before execution) and the CURRENT oracle, run the
  full corpus; record Qualification {subject_sha, oracle_version,
  model_profile, result, timestamp}; attach status to the toolkit
  commit; retain report artifacts.
- Triggers: merge to main (path-filtered to reviewer-behavior
  inputs), manual, scheduled.
- Consumer-side secretless verification check: reads the proposed
  SHA from a pin-bump diff, queries the qualification record,
  confirms subject + PASS + current oracle + acceptable model
  profile; red/green in the pin-bump PR.
- Reviewer-behavior input set: engine/core files, parse_review.py
  (normalization + renderer), rubric.md, review.sh,
  .github/workflows/ai-review.yml (owns the model default), the
  qualification workflow itself, eval/**.
- Deployment contract text (README/templates): pin bumps require the
  verification check green; the ci-toolkit dogfood pin follows the
  same rule.

### Acceptance criteria

- Qualification observed green on a good merged SHA and red on a
  deliberately broken one, before the contract is relied upon.
- Old-subject x new-oracle re-qualification demonstrated (no new
  toolkit commit needed).
- Consumer verification check demonstrated on a real or simulated
  pin-bump PR, secretless.
- No workflow path executes PR-head code with the secret.

### Validation

- One green, one forced-red qualification, one verification run
  inspected.

## Phase 4 — M5 consistency rule (behavior change only)

Status: NOT STARTED

### Scope

- Single PR: rubric amendment — absolute behavioral claims must be
  qualified against exceptions/filters/guards present in the same
  diff; unqualified absolutes are a finding. Oracle untouched.

### Acceptance criteria

- M5 passes routine policy; no GATING regressions; no oracle file
  modified in the PR diff (reviewed).

### Validation

- Qualification run on the merged SHA shows the M5 delta.

## Phase 5 — M5 promotion

Status: NOT STARTED

### Scope

- Tiny PR: M5 KNOWN_GAP -> GATING, citing qualification evidence at
  promotion threshold.

### Acceptance criteria

- N=5, >=4/5 M5 detection, zero false blockers on C5, no GATING
  regressions.
- M4 remains KNOWN_GAP, owner Stage 3.
- Promotion permanent per ratchet.

### Validation

- Qualification record inspected; promotion PR diff is oracle-only.

## Phase 6 — Drift detection + evidence handoff

Status: NOT STARTED

### Scope

- Scheduled re-qualification of the DEPLOYED pin's subject against
  the current oracle: stability deltas as drift early warning.
- Evidence bundle for Stage 3 / Stratum:

  ```text
  subject_sha / oracle_version / model_profile
  qualification: PASS / corpus_version / qualified_at
  known_gaps: [M4]
  detection_stability: ... (never "confidence")
  ```

### Acceptance criteria

- One scheduled run observed; drift artifact carries full metadata.
- Stage 3 plan (when written) references stats by subject+oracle.

### Validation

- Manual inspection of first two scheduled reports.

## Plan deviations

(none — rev 2/3/4 revisions were pre-approval review feedback on a
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
  is routine maintenance; it proceeds under the current review-only
  procedure and only becomes subject to the verification contract
  after phase 3 exists.
