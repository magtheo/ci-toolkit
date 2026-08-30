<!-- Adapted from ci-toolkit templates/AGENTS.md (which generalized
     student-platform's lived-in version) — this repo now dogs its own
     food. -->

# AGENTS.md

## Purpose

This repository (ci-toolkit) provides shared CI patterns for magtheo's
repos — currently the **advisory AI pull-request reviewer** and the
**reviewer evaluation / qualification infrastructure** — under a
two-level branch workflow for human + coding-agent collaboration.

Goals:

- keep `main` stable;
- make every risky change start from an explicit written plan;
- give coding agents small, bounded implementation tasks;
- review each implementation phase independently;
- review the completed feature as a whole before it reaches `main`;
- prevent agents from silently expanding scope or merging unreviewed
  work.

---

## Working in this repo

Shared CI patterns for magtheo's repos. Logic only — no secrets, no
project code. Primary consumers: student-platform, platform-core,
and future repos.

(`engine.py`, `render.py`, and `eval/` reach `main` with the
umbrella `feature/reviewer-eval-baseline` merge; until then they live
on that branch.)

```
engine.py        Reviewer kernel — ReviewInput v1 -> ReviewResult v1.
                 Semantically pure: no GitHub concepts, no transport.
render.py        GitHub renderer — the presentation consumer of
                 ReviewResult (review event, inline payloads,
                 Markdown; no semantic decisions).
parse_review.py  Pure normalization: model output -> ReviewResult.
                 Parser owns INCONCLUSIVE; never guesses.
review.sh        Thin transport (curl -> engine -> post review).
rubric.md        Reviewer instructions (pinned with the engine).
eval/            Reviewer evaluation: fixtures (misses + paired
                 controls), harness, GATING states, qualification
                 records branch.
tests/           Deterministic suite (engine contract, corpus,
                 qualification, security invariants).
templates/       Governance copy-templates for consumer repos.
plans/           Feature plans (see plans/ + plans/README.md pattern
                 from student-platform).
ROADMAP.md       The reviewer capability roadmap — authoritative
                 direction for reviewer intelligence work.
```

Validation:

```bash
python3 -m pytest tests/ -q   # full deterministic suite
bash -n <script.sh>           # shell syntax for touched scripts
```

CI: PRs run the test suite plus the advisory AI reviewer (dogfood).
The reviewer is **advisory evidence, never an authority**: expect
`AI review · Clear / Issues found / Inconclusive`, triage its findings
on the merits (it produces false blockers — see ROADMAP evidence
appendix), and never let it gate a merge by itself.

---

## Branch Model

Three change paths (same model as student-platform; full detail lives
in `templates/AGENTS.md`, which this file adapts):

```text
main
├── fix/<slug> | chore/<slug> | docs/<slug>          (small changes)
└── feature/<feature-slug>
    └── phase/<feature-slug>/<nn>-<phase-slug>       (planned features)
```

- Never commit or push implementation work directly to `main`; work
  reaches `main` only through a reviewed PR. Agents never merge.
- Phase branches target their feature branch, never `main`.
- One phase = one PR. No unrelated cleanup inside a phase PR.

### What counts as small here

A change is small only if ALL hold: no engine contract change
(`ReviewInput`/`ReviewResult` schema or semantics), no eval-semantics
change (harness, fixtures, GATING states, `oracle_version` inputs),
no deployment-contract change (qualification, pin verification), no
new runtime dependency, no reviewer-rubric behavior change, and it
touches the toolkit plus its tests only.

Everything else is a feature and needs a plan first. **When in doubt,
use the feature path.** If implementation reveals a small-change
criterion no longer holds, stop and escalate to the feature workflow.

---

## Reviewer Evaluation — standing rules

These are the methodology invariants from
`plans/reviewer-eval-baseline.md`; they bind all future work:

1. Every confirmed reviewer miss becomes a frozen fixture BEFORE the
   intelligence fix, with a paired near-miss control.
2. Capabilities are promoted to GATING only through measured
   qualification (N=5, ≥4/5, paired control clean, zero GATING
   regressions). Promotion is permanent.
3. `oracle_version` identifies everything that determines oracle
   semantics (harness + corpus + GATING states). Changing any of them
   invalidates prior PASS records — fail closed.
4. Qualification PASS is scoped to the oracle, not a correctness
   claim about the subject (humility rule).
5. PR descriptions must match contents (applies to our own PRs).
6. Pair integrity: a positive's own pass is necessary but not
   sufficient — it is **promotion-eligible** only if its paired
   control also passes (detection indistinguishable from
   over-triggering is not a capability). Mechanically enforced;
   controls may gate alone.

Reviewer intelligence work follows ROADMAP.md: capabilities are
expanded through measured evidence, never ad-hoc rubric stuffing.

---

## Deployment contract

Consumer repos pin reviewer commits; the pin is the deployment
surface. A pinned SHA should have a PASS qualification record against
the current oracle on the `qualifications` branch. The contract is
**PENDING ACTIVATION** until the umbrella
`feature/reviewer-eval-baseline` merge and the live activation-gate
demonstrations (see the plan's Deviation 1 and README). After
activation, dogfood pin changes in this repo's `review.yml` are
verified by the fail-closed `verify-pin` job; until then, the
legacy review-only procedure remains in force.

---

## Review Model

1. **Deterministic gates** — mechanical truth (tests, syntax checks;
   expanding per ROADMAP's deterministic track).
2. **AI first-pass review** — advisory design-level evidence, triaged
   on the merits.
3. **Human judgment** — plan approval, deviation decisions, and the
   merge decision itself. Agents never approve or merge.

---

## Agent Operating Procedure

Before making code changes, answer from repository state: which
branch am I on (small change or which feature/phase)? Where is the
plan? Which phase? What are the acceptance criteria? What is out of
scope? What validation is required? Which branch does the PR target?

If any cannot be determined reliably, stop and ask.

Stop conditions and prohibited actions: as in `templates/AGENTS.md`
(no direct commits/merges to `main`, no silent scope expansion, no
silently rewriting approved plans, no hiding failures, no force-push
to shared branches). One addition specific to this repo: **never
change eval semantics (fixtures, states, harness thresholds) and
reviewer intelligence (rubric, engine) in the same PR** — that
combination is exactly what the oracle/subject separation exists to
prevent.
