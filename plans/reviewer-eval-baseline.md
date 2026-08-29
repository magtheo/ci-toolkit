# Reviewer Eval Baseline

Status: DRAFT — awaiting maintainer review (no implementation before
approval)

## Goal

Give the AI reviewer a measured quality baseline before any
intelligence change: a fixed eval corpus of recorded miss cases, an
offline harness that replays them, and a CI gate that prevents any
reviewer-behavior change from merging without passing the corpus.

Turns "the reviewer seems better now" into "previously-failing
fixtures pass at the required stability, previously-passing fixtures
did not regress."

Origin: five confirmed miss classes (ledger in
student-platform:plans/ai-pr-review.md, misses #4/#5 recorded in its
PR #37); sequencing amendment to that plan's Deviation 2 — evaluation
baseline precedes intelligence changes (Stage 3 context retrieval
and Stage 2 diff budgeting wait behind this feature).

## Non-goals

- No change to reviewer intelligence in this feature's early phases:
  the consistency rule (phase 3) is the first and only behavior
  change, and it must pass the corpus first.
- No Stage 3 base-context retrieval, no Stage 2 diff budgeting.
- No online/runtime changes to review.sh semantics — Layer A
  (runtime validation) stays as-is.
- No corpus hosting outside ci-toolkit; no external eval framework.

## Constraints

- **Fixture secrecy policy (hard)**: ci-toolkit is public;
  student-platform is private. Fixtures derived from private-repo
  misses (#1, #4, #5) MUST be synthetic replicas that reproduce the
  miss class without private content. Misses #2 (ci-toolkit #3) and
  #3 (ci-toolkit #7) may use the real public diffs.
- **One-way boundary**: eval/ depends on review.sh, parse_review.py,
  rubric.md as a black box; the reviewer never depends on eval/.
- **Nondeterminism policy (settled with maintainer, 2026-08-29)**:
  N=3 runs per fixture; a fixture requiring an expected finding
  passes if the finding (by stable matcher) appears in >=2 of 3
  runs; fixtures expected Clear must produce zero blocking findings
  across all runs (zero tolerance for false blockers).
- **Full-output fixtures**: assessment label, findings, severity —
  so the harness reports per-fixture stability statistics (e.g.
  "label matched 3/3"), the confidence measure for future Stratum
  evidence consumption.
- **Cost policy**: no budget machinery; every run reports calls,
  tokens, approximate cost. Guards only if corpus exceeds ~50
  fixtures.
- Eval uses the LLM_API_KEY secret already present in this repo.

## Phase 1 — Corpus + offline harness

Status: NOT STARTED

### Scope

- `eval/fixtures/` — five fixtures, one per miss class:
  - M1 synthetic: caller uses `secrets: inherit` + praise risk
  - M2 real (ci-toolkit #3): pull_request + secret + floating ref
  - M3 real (ci-toolkit #7): guard contradicting documented contract
  - M4 synthetic: docstring contract false of unseen code (PR #35 class)
  - M5 synthetic: "Every X" claim vs in-diff exclusions (PR #36 class;
    regression reference: student-platform PR #36 head e51ee75e)
  - fixture format: input diff, rubric in force, expected assessment
    + findings (+ matchers), miss class, origin/synthetic flag
- `eval/run_corpus.sh` — black-box invocation of review.sh over the
  corpus, N runs per fixture, pass-policy evaluation, per-fixture
  stability stats, aggregate report, spend report
- Current reviewer is EXPECTED to fail M5 (and likely M4) — the
  baseline report records this honestly; those fixtures are red
  until phase 3.

### Acceptance criteria

- `eval/run_corpus.sh` runs the full corpus locally and exits
  nonzero iff any fixture violates the pass policy.
- Report includes per-fixture: verdict, label stability, finding
  stability, spend.
- No private-repo content appears in eval/ (checked by review).

### Validation

- `./tests/run` still green (no reviewer changes).
- Corpus run reproduces the recorded baseline (M5 red).

## Phase 2 — CI gate

Status: NOT STARTED

### Scope

- Workflow: on pull_request, path-filtered to the eval's transitive
  inputs (review.sh, parse_review.py, rubric.md, eval/**), runs the
  corpus, becomes a required check.
- Required branch protection check on main.

### Acceptance criteria

- A PR touching reviewer files cannot merge on corpus failure.
- A PR NOT touching them spends nothing (path filter verified with a
  templates/README-only PR).

### Validation

- One deliberate red run (fixture forced fail) and one green run
  observed in CI before protection is required.

## Phase 3 — First gated behavior change: consistency rule (miss #5)

Status: NOT STARTED

### Scope

- Rubric amendment: absolute behavioral claims must be qualified
  against exceptions, filters, guards present in the same diff;
  unqualified absolutes are a finding.
- No parser changes expected; if needed, parser changes are in scope
  only for expressing this rule.

### Acceptance criteria

- M5 passes at policy (finding in >=2/3 runs).
- No other fixture regresses; corpus green overall.
- Pin-bump PRs in consumer repos pick this up via the normal
  deliberate upgrade procedure (old pin reviews the bump).

### Validation

- Full corpus green in CI; observed live review on the bump PR.

## Phase 4 — Drift detection + Stage 3 handoff

Status: NOT STARTED

### Scope

- Scheduled (e.g. monthly) corpus re-run on unchanged reviewer;
  report stability deltas (model/routing drift early warning).
- Confidence stats packaged as input to the future Stage 3 plan
  (base-context retrieval), which remains a separate feature.

### Acceptance criteria

- One scheduled run observed; drift report artifact exists.
- Stage 3 plan (when written) references corpus stats.

### Validation

- Manual inspection of first two scheduled reports.

## Plan deviations

(none yet)

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
