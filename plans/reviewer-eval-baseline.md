# Reviewer Eval Baseline

Status: rev 5 — APPROVED through rev 4 (2026-08-29, maintainer merge
of PR #8); rev 5 adds the Track 1 staged sub-plan (T1.1–T1.5,
Deviation 4) — PROPOSED, approval = maintainer review of the T1
plan phase PR. Implementation may continue under the phase
workflow: phase branches target feature/reviewer-eval-baseline.

Revision history: rev 5 — Track 1 discrimination sub-plan (stages,
invariants, gates, lifecycle boundaries; Deviation 4). rev 4 —
engine/oracle phase separation, engine vs consumer-profile
qualification levels, current-oracle deployment invariant,
subject/oracle record separation, machine-verifiable promotion,
ReviewResult purity (no GitHub rendering), duplicate M5 step
removed.

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
5. Pair integrity: a positive fixture is only promotable to GATING
   while its paired control passes (detection indistinguishable from
   over-triggering is not a capability). Controls may gate alone.
6. Qualification PASS means: preserved the capabilities encoded by
   the current oracle, under this profile. It NEVER means "the
   reviewer is correct." No corpus size proves general review
   correctness.

## Phase 1 — Engine contract

Status: COMPLETE (2026-08-29; phase PR #11 merged as 40a6bb1 into
this feature branch. 72 tests — contract, regression, timeout
pinning; payload byte-equivalence verified; three external-review
behavior-preservation catches converted into regression coverage)

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

Status: COMPLETE (2026-08-30; phase PR #12 merged after two oracle-
validity review rounds + one hygiene pass; measured baseline
eval/baseline-2026-08-30.json, 48 calls; states recorded in
eval/states.json with rationale in eval/state-log.md — C4/C5/C7
GATING, all others KNOWN_GAP incl. M8 via pair integrity) (phase branch:
phase/reviewer-eval-baseline/02-independent-oracle; corpus grown to
M1–M8/C1–C8 per ledger misses #6–#8)

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

Status: COMPLETE — implementation acceptance (deterministic + local
E2E proof); deployment contract PENDING ACTIVATION per Deviation 1
(post-#10 live demonstrations). Phase branch:
phase/reviewer-eval-baseline/03-qualification.

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

Status: BLOCKED — by a newly measured discrimination prerequisite
(Deviation 2, 2026-08-30). The rule successfully induced M5 detection
(5/5, zero noise) but failed pair integrity in every tested
formulation: paired control C5 was false-blocked 5/5 across three
rubric wordings and two models; the stronger model increased broader
false positives. Rubric reverted to pre-#16 text. Evidence:
`eval/evidence/phase4-discrimination-probe-2026-08-30/`. Resumes only
after the Track 1 exit criteria are met (T1.5, below; see also
ROADMAP.md).

### Scope

- Single PR: rubric amendment — absolute behavioral claims must be
  qualified against exceptions/filters/guards present in the same
  diff; unqualified absolutes are a finding. Oracle untouched.

### Acceptance criteria

- M5 passes routine policy; no GATING regressions; no oracle file
  modified in the PR diff (reviewed).

### Validation

- Qualification run on the merged SHA shows the M5 delta.

## Track 1 — Reviewer discrimination (staged sub-plan)

Status: PLANNED — this section IS the Track 1 implementation plan;
no T1 implementation exists yet. Elaborates Deviation 2 (recorded as
Deviation 4). Stages T1.1–T1.5 are sequential: each is one phase PR
targeting the feature branch, and stage N must be merged before
stage N+1 begins.

### Goal / capability statement

Improve the reviewer's ability to distinguish:

- **real, actionable defects supported by repository/diff evidence**
  from
- **plausible-sounding but insufficiently supported concerns**,

while **preserving defect detection**. The capability is paired
discrimination, not attenuation: detecting M5 while blocking C5 is
not success, and clearing C5 while missing M5 is not success.

### Non-goals

- No fixture-specific, lexical, path-keyed, or special-case rules.
  M5/C5 is the first sharp diagnostic pair; the scope is the measured
  false-blocker population (baseline: C1/C2/C3/C6/C8; contaminated
  positives M1/M2/M3/M7; probe collateral on C7).
- Not "make the reviewer less willing to block": the corpus makes
  that structurally visible — expected findings are severity-matched,
  so downgrading an intended blocking defect to advisory registers as
  a detection failure, not a fix.
- No reviewer-intelligence change and eval-semantics change in the
  same PR (AGENTS.md standing rule; T1 stage boundaries enforce it).

### Grounding evidence (frozen)

- Baseline `eval/baseline-2026-08-30.json` + state-log: 5/8 controls
  false-blocked; M1/M2/M3/M7 detected but contaminated by unexpected
  blockers; M8 withheld by pair integrity (C8).
- Phase-4 probe
  `eval/evidence/phase4-discrimination-probe-2026-08-30/`: M5
  detection inducible, C5 separation not, across three rubric
  wordings × two models; wording steers the blocking narrative, not
  the blocking verdict; rubric edits have global collateral effects
  (C7 0 → 8 blockers); recurring false-block class — immutable
  full-SHA pinning flagged as a blocking security defect with
  floating refs recommended as the "fix" (C1/C2).
- ROADMAP appendix A (#14 self-review false positives): hallucinated
  absence; inverted conclusion from a true premise; asserted test
  gap without reading the tests.

### Hard invariants (bind every T1 stage)

1. **Sensitivity floor:** specificity may improve only without
   materially reducing sensitivity — no positive fixture's
   expected-finding detection may drop below its T1.2 baseline hits
   at the same N.
2. **M1–M8 non-regression:** existing defect detection must not
   regress (invariant 1 applied to the full positive set).
3. **M5 and C5 must both classify correctly** at gate runs (M5
   detected at threshold, C5 zero false blockers).
4. **C1/C2/C3/C6/C8 are inside the no-regression/discrimination
   gate** — a mechanism that separates only M5/C5 does not exit T1.
5. **No special-casing:** no fixture name, lexical pattern keyed to
   a fixture, path-specific rule, or equivalent gaming.
6. **New adversarial examples for the discovered failure families
   must pass** (T1.1 seeds, T1.4 holdout).
7. **Matrix reproduction:** gate runs use N=5 on the model matrix
   haiku-4.5 + one stronger profile (sonnet-4.5 per probe
   precedent), matching the qualification contract's shape.
8. **Evidence frozen before promotion:** every gate run's report +
   raw narratives land under `eval/evidence/track1-*/` before any
   state or promotion decision cites it.
9. **Promotion only after the generalization gate (T1.4) passes** —
   never on development-corpus results alone.

### Stage T1.1 — Failure taxonomy + frozen discrimination corpus
(eval semantics only; no reviewer change in this PR)

Scope:

- Code **every** false blocker in the frozen evidence (baseline
  per-fixture detail, probe runs, appendix A) into failure families;
  anything unclassifiable is bucketed `unclassified`, never forced.
  Taxonomy is derived from evidence and recorded in
  `eval/evidence/track1-taxonomy-<date>.md`, citing report + run for
  each exemplar.
- Family hypotheses to confirm or replace (from current evidence):
  unsupported security boilerplate (risk vocabulary without an
  invariant; C1/C2 pinning); unqualified-absolute consistency
  reading (M5/C5 axis — hyper-literal doc matching without reading
  the qualifiers present); speculative consequence (blocking on what
  could happen, no concrete failing execution path); asserted
  absence / hallucinated context (appendix A); severity inflation
  (advisory-grade material marked blocking).
- For each confirmed family: at least one control exemplar and one
  near-miss positive exemplar, either cited from existing fixtures
  or **newly frozen** adversarial pairs (transformed: renamed paths,
  restructured files, semantically equivalent rewording, other
  domains where the family applies).
- New fixtures carry an additive `family` field; fixture validation
  and deterministic tests extend accordingly. This intentionally
  changes `oracle_version` (fail closed; see Deviation 4).

Acceptance criteria:

- every false blocker in the frozen evidence is classified or
  explicitly bucketed `unclassified`;
- ≥2 frozen pairs per confirmed family not already covered by the
  baseline corpus;
- taxonomy document cites report + run for every exemplar;
- deterministic suite green (fixture validation, corpus loading,
  oracle-input pinning updated to the new corpus).

Validation: `python3 -m pytest tests/ -q`; corpus loads; optional
N=1 smoke run (spend-recorded).

### Stage T1.2 — Measured discrimination baseline (evidence only)

Scope: full-corpus runs on the T1.1 corpus with the unchanged
reviewer (feature-branch subject; exploratory N=3, or N=5 if the
result will be cited as a gate reference), plus human narrative
coding of blocking findings into taxonomy families. Metrics
recorded per fixture and aggregated per family:

- defect detection / recall (expected-finding hits; existing
  policy);
- control preservation: zero-tolerance false blockers per control;
- false-block count and rate per control per run;
- false-clear rate per positive (runs answered CLEAR or
  INCONCLUSIVE while the defect is present);
- paired Mx/Cx discrimination (pair-integrity eligibility);
- grounding quality: human-coded basis for each blocking narrative
  (cited-evidence / inferred / asserted), recorded in the evidence
  bundle; a machine proxy becomes available only if T1.3 introduces
  structured evidence fields.

Acceptance criteria: report bundle frozen under
`eval/evidence/track1-baseline-<date>/` with the per-family table;
this bundle is the non-regression reference for T1.3.

### Stage T1.3 — Smallest general mechanism (reviewer change only)

Development loop, per iteration:

```text
pick failure family (dominant measured first)
        ↓
propose the SMALLEST mechanism, naming its layer
        ↓
implement on a phase branch (reviewer only — no eval files)
        ↓
measure on the T1.2 protocol; compare per family
        ↓
invariants hold?  ── no ──→ revert; record the negative result
        ↓ yes
next family / next mechanism
```

Candidate layers (a mechanism must name its layer and say why it
generalizes beyond one fixture):

- a. rubric / reasoning contract — probe evidence shows wording
  alone steers narratives, not verdicts; a wording-only change is
  admissible only with measured separation;
- b. finding schema + deterministic support validation — blocking
  findings must carry structured support (stated invariant, concrete
  failing execution path, cited diff/context evidence); under-
  supported blocking findings are downgraded to advisory by the
  deterministic layer (parse/engine), keeping the decision auditable;
- c. evidence representation — enrich ReviewInput context/budgeting
  so the model can ground rather than guess;
- d. dedicated discrimination pass — only if the single-pass form is
  measured insufficient; a layer must earn its existence.

Acceptance criteria (stage exit):

- at least one mechanism addressing the dominant measured family,
  generalizing across ≥2 families (not M5/C5 alone);
- M5 detected and C5 clean at N=5 with zero C5 false blockers —
  necessary, explicitly not sufficient;
- all hard invariants hold against the T1.2 reference.

### Stage T1.4 — Generalization gate (holdout corpus)

Scope: author new holdout fixtures per confirmed family from the
family definitions alone — **without reference to mechanism
internals or failure outputs**. Per family: a true-defect variant
(positive), a near-miss control, an ambiguous case (control-kind:
advisory allowed, zero blocking expected), and at least one
transformed variant (rename/restructure/reword/other domain).
Freeze before the first run; evaluate once and record; re-authoring
after a failure is a recorded deviation, not a quiet retry.

Acceptance criteria: the frozen holdout passes the same gates as
T1.5 (below) in a single recorded pass — all controls clean, all
positives detected, no sensitivity loss, on the full matrix.

### Stage T1.5 — Qualification gate + Phase 5 handoff

Track 1 is complete when ALL hold:

1. full corpus (baseline + T1.1 seeds + T1.4 holdout) at N=5 on both
   model profiles: every control zero false blockers; every positive
   ≥4/5 expected-finding detection (severity-matched); zero GATING
   regressions;
2. per-family table green — every confirmed family shows separation;
3. evidence bundles frozen (taxonomy, T1.2 baseline, T1.3 iterations
   incl. negative results, T1.4 holdout);
4. the mechanism PR(s) are human-reviewed and merged into the
   feature branch;
5. boundary honesty: T1 gates are **experimental evaluations on
   feature-branch SHAs** — they carry no deployment authorization;
   deployment-relevant qualification runs on merged-main subjects
   after the umbrella merges (activation gates; Deviations 1/3/4).

Handoff: with T1.5 green, Phase 4 (M5 rule) resumes under its
existing scope and Phase 5 promotion follows its existing criteria,
unchanged.

### Spend and authorization

Model calls run against the directing human's OpenRouter key. Every
evidence bundle records call count and token spend (probe
precedent: 400 calls). Runs at probe scale are pre-authorized by
approval of this plan; larger scales ask first.

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
  (Per Deviation 3: pre-merge implementation acceptance observes a
  LOCAL end-to-end drift run with the full-metadata artifact;
  dispatched + scheduled observations are post-merge activation
  criteria — dispatch, like schedules, only fires for workflows on
  the default branch.)
- Stage 3 plan (when written) references stats by subject+oracle.

### Validation

- Manual inspection of first two scheduled reports.

## Plan deviations

### Deviation 4 — Track 1 elaborated into a staged sub-plan; oracle
lifecycle bounded (PROPOSED in the T1 plan phase PR; maintainer
review of that PR is the approval)

Deviation 2 resequenced Track 1 ahead of the M5 retry with a
one-line pointer to ROADMAP.md. This amendment carries the full
Track 1 implementation plan (stages T1.1–T1.5) inside this document
so the umbrella's lifecycle is self-describing:

```text
Track 1 plan (this section)
  -> T1.1 taxonomy + corpus   -> T1.2 measured baseline
  -> T1.3 smallest mechanism  -> T1.4 generalization holdout
  -> T1.5 exit gate
  -> Phase 4 (M5 retry)  -> Phase 5 (promotion)
  -> Phase 6 (drift)     -> whole-feature review -> merge
  -> post-merge activation gates
```

Two lifecycle boundaries made explicit:

- **Experimental vs qualification:** T1 gates are full-corpus
  experimental evaluations on feature-branch SHAs; under the
  Phase-3 contract they carry no deployment authorization.
  Deployment-relevant qualification runs on merged-main subjects
  after the umbrella merges — the same split class as Deviations 1
  and 3.
- **Oracle identity:** T1.1/T1.4 grow the corpus, intentionally
  changing `oracle_version` and invalidating prior PASS records
  (fail closed). No consumer pin depends on a PASS record today
  (contract PENDING ACTIVATION); Track 1 corpus growth must
  therefore complete before activation.

The acceptance bar is not lowered: T1.5 requires the N=5,
dual-model, no-regression gates in the qualification contract's
shape.

### Deviation 3 — Phase 6 acceptance split across the umbrella merge
boundary (PROPOSED in the reconciliation PR; maintainer review of
that PR is the approval)

Original Phase 6 acceptance requires "one scheduled run observed".
Scheduled workflows run only on the default branch, and the
scheduled drift machinery reaches `main` only through the umbrella
PR (#10) — which cannot complete while a phase requires evidence
only obtainable after the umbrella merges. A manual
`workflow_dispatch` is no escape: GitHub fires dispatch events only
for workflow files present on the default branch, so a pre-merge
dispatch on the feature branch is equally impossible. This is the
same class of lifecycle circularity Deviation 1 resolved for
Phase 3.

Resolution (three lifecycle-feasible layers, not a weakening):

1. **Before the umbrella merge — implementation acceptance:**
   deterministic tests plus a LOCAL end-to-end execution of the
   drift logic, following the Deviation 1 pattern (drive the
   machinery against a local bare origin, exactly as Phase 3's
   acceptance did), with the resulting full-metadata drift artifact
   inspected. No GitHub event of any kind is required.
2. **Post-merge activation gate** (alongside Phase 3's live
   demonstrations): one manually dispatched drift run observed on
   `main`, then the first scheduled run observed.
3. **Production cadence:** the first two scheduled reports manually
   inspected before the deployment contract is declared fully
   active.

The observed-run requirements are not weakened — the local layer
adds machine-checkable evidence before the merge, and both the
dispatched and scheduled observations remain mandatory on `main`.

### Deviation 2 — M5-first sequence falsified by measurement;
Track 1 (discrimination) resequenced ahead (approved by directing
human, 2026-08-30)

The plan sequenced M5 (Phase 4) as the first capability stage on the
assumption that a rubric amendment could pass its own paired control.
Measurement falsified that assumption: five full-corpus N=5 runs
(old rubric; three rule formulations; two models) show M5 detection
is inducible but C5 separation is not — detection indistinguishable
from over-triggering, exactly what pair integrity exists to reject.
The stronger model profile worsened overall false-blocking,
indicating a discrimination/grounding ceiling rather than a wording
or model-selection problem.

Response: rubric reverted (rollback PR), M5 remains KNOWN_GAP,
Phase 4 BLOCKED, and Track 1 (discrimination / false-blocker
reduction, ROADMAP.md) becomes the next active capability stage.
M5 retries under Track 1's outcome. The acceptance criteria are
unchanged — the sequencing was wrong, not the bar.

### Deviation 1 — Phase 3 acceptance split into implementation
acceptance and post-merge activation (approved by directing human,
2026-08-30)

Original Phase 3 acceptance required observing live workflow runs:
a good green qualification, a forced red, an old-subject ×
new-oracle requalification, and consumer verification. Those
workflows do not exist on `main` until the umbrella PR (#10)
merges, and the umbrella must stay draft until all phases are
complete — a circular dependency that could not be resolved by
sequencing alone.

Resolution (explicit, not a weakening): Phase 3 may be marked
COMPLETE on *implementation acceptance* — deterministic tests plus
local end-to-end proof (including real `publish_record.sh` runs
against a bare origin covering bootstrap, same-subject
requalification, and second-subject-from-second-clone). The
deployment contract remains **PENDING ACTIVATION** (README) until
the post-merge *activation gate* passes on `main`: the four live
demonstrations above. Until then, no reviewer SHA may deploy under
the qualification contract, and the dogfood pin-bump continues
under the legacy review-only procedure.

The acceptance criteria are not weakened — they are split across
two lifecycle points, each with its own evidence.

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
