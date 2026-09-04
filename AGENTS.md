<!-- Adapted from ci-toolkit templates/AGENTS.md (the canonical baseline
     this repo maintains) — this repo dogs its own food. Repo-specific
     additions: reviewer-eval standing rules, deployment contract, and
     the pin-reachability branch exception. -->

# AGENTS.md

## Purpose

This repository (ci-toolkit) provides shared CI patterns for magtheo's
repos — currently the **advisory AI pull-request reviewer** and the
**reviewer evaluation / qualification infrastructure** — under a
two-level branch workflow for human + coding-agent collaboration.

Goals: keep `main` stable; make every risky change start from an
explicit written plan; give coding agents small, bounded tasks; review
each phase independently; review the completed feature as a whole
before it reaches `main`; prevent agents from silently expanding scope
or merging unreviewed work.

---

## Working in this repo

Shared CI patterns for magtheo's repos. Logic only — no secrets, no
project code. Primary consumers: student-platform, platform-core,
and future repos.

(`engine.py`, `render.py`, and `eval/` reach `main` with the
umbrella `feature/reviewer-eval-baseline` merge; until then they live
on that branch — read the plan from the feature branch, not `main`.)

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
plans/           Feature plans (plans/README.md pattern).
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

## Branch Architecture

```text
main
├── fix/<slug> | chore/<slug> | docs/<slug>          (small changes)
└── feature/<feature-slug>
    └── phase/<feature-slug>/<nn>-<phase-slug>       (planned features)
```

Full detail lives in `templates/AGENTS.md` (the canonical baseline this
file adapts). The invariants, in short:

- `main` is the **only permanent integration branch**. No permanent
  middle layers (develop/staging/team/product-area) between `main` and
  `feature/*`; a temporary integration or release branch is an explicit
  human exception with a deletion condition. Deployment environments
  are not Git branches.
- One `feature/*` = one independently mergeable outcome. If two
  outcomes can reach `main` independently, they are two features.
- Phases are **sequential by default**: one unmerged phase per feature;
  parallel phases from the same feature head only when the approved
  plan declares them independent; phase-on-phase stacking only by
  explicit human exception.
- **Branch ownership:** agents write only branches they created for the
  current task or branches the directing human explicitly assigned.
  Every other branch is foreign. Ownership is about writing, not about
  who owes integration — integration of `main` into a feature branch
  happens by explicit assignment (e.g. the #26 reconciliation merge).
- Never commit or push implementation work directly to `main`; work
  reaches `main` only through a reviewed PR. Phase branches target
  their feature branch, never `main`. One phase = one PR, no unrelated
  cleanup inside a phase PR.
- **Repo-specific exception — do not rely on automatic branch
  deletion:** consumer pins reference merge SHAs whose reachability
  must not depend on PR-branch lifecycles (2026-08-31 pin incident).
  Long-lived pins are anchored under `pins/<sha>` refs.

### Keeping current with `main` (drift triage)

Synchronize the feature branch by **relevance**, never by commit
count: unrelated changes → ignore during the current phase; shared
code without contract overlap → integrate at the next phase boundary;
same files or an engine/eval/deployment-contract dependency →
coordinate and integrate before continuing. Before any whole-feature
review, assess against current `main` — integrate if relevant, or
**record the assessment** ("drift unrelated: docs + consumer README")
and proceed.

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
A human maintainer may explicitly authorize the small path for a
narrow failed criterion with recorded rationale; agents may never
grant that exception to themselves.

---

## Source-of-truth hierarchy

GitHub owns live state (open/merged/CI — derive it, never duplicate
it). This file owns workflow rules. The open feature's plan, on the
**feature branch**, owns feature intent. ROADMAP.md owns capability
priorities, not PR state. PR descriptions must describe their exact
current head at every review boundary — a description that
contradicts its diff is a defect.

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
Is the branch mine for this task or explicitly assigned?

If any cannot be determined reliably, stop and ask.

Stop conditions and prohibited actions: as in `templates/AGENTS.md`
(no direct commits/merges to `main`, no writing to foreign branches,
no silent scope expansion, no silently rewriting approved plans, no
hiding failures). One addition specific to this repo: **never change
eval semantics (fixtures, states, harness thresholds) and reviewer
intelligence (rubric, engine) in the same PR** — that combination is
exactly what the oracle/subject separation exists to prevent.
