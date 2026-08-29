<!-- ci-toolkit governance copy-template: AGENTS.md
     COPY this file into your repo's root and ADAPT it (repo layout,
     validation commands, docs hubs, CI specifics). Never reference
     shared governance across repos — each repo owns its rules.
     Source of truth: student-platform's AGENTS.md (the lived-in
     version this template generalizes). -->

# AGENTS.md

## Purpose

This repository uses a two-level branch workflow designed for human +
coding-agent collaboration.

The goals are:

- keep `main` stable;
- make every risky change start from an explicit written plan;
- give coding agents small, bounded implementation tasks;
- review each implementation phase independently;
- review the completed feature as a whole before it reaches `main`;
- prevent agents from silently expanding scope or merging unreviewed work.

This file defines the required workflow for humans and agents.
Adapt the repo-specific sections (layout, validation commands,
documentation hubs) to your repository before committing.

---

## Working in this repo

<!-- FILL IN: repository layout, validation commands, CI summary,
     documentation hubs. Keep it short — orientation, not
     documentation. -->

---

## Branch Model

There are three change paths:

```text
main
├── fix/<slug> | chore/<slug> | docs/<slug>          (small changes)
└── feature/<feature-slug>
    └── phase/<feature-slug>/<nn>-<phase-slug>       (planned features)
```

### `main`

`main` is the stable integration branch.

Rules:

- Do not commit directly to `main`.
- Do not push implementation work directly to `main`.
- Agents must never merge into `main`.
- Work reaches `main` only through a reviewed pull request.

### Small-change branches

`fix/<slug>`, `chore/<slug>`, or `docs/<slug>` target `main` directly in a
single PR.

### `feature/*`

A feature branch is the integration branch for one planned feature.

Example:

```text
feature/student-dashboard
```

A feature branch contains:

- the feature plan;
- all completed implementation phases;
- integration fixes that belong to the feature;
- the complete feature diff that will eventually be reviewed against `main`.

A feature branch is created from an up-to-date `main`.

The feature branch should not be used for normal implementation work. Implementation happens on phase branches.

### `phase/*`

A phase branch implements exactly one phase from the feature plan.

Example:

```text
phase/student-dashboard/02-api
```

A phase branch is created from the current feature branch, not from `main`.

A phase branch must target its feature branch in its pull request.

---

## Naming

Use lowercase kebab-case.

Feature branches: `feature/<feature-slug>` (e.g. `feature/course-enrollment`).

Phase branches: `phase/<feature-slug>/<nn>-<phase-slug>`
(e.g. `phase/student-dashboard/01-data-model`).

Phase numbers should match the phase ordering in the plan.

Milestones: one per feature, titled `<feature-slug>` — every PR in the
family (feature PR + all phase PRs) is assigned to it. The milestone
page is the family view GitHub actually indexes; PR numbers alone are
flat and carry no relationship.

---

## Which Path: Small Change or Feature?

A change qualifies as **small** only if ALL of these hold:

- no data model, schema, or migration changes;
- no cross-client contract changes (API shapes shared by mobile/web/ai-server);
- no security or permissions behavior;
- no CI/workflow or build-config changes;
- no new runtime dependencies;
- touches one app or service plus its tests.

Small-change workflow: branch `fix/<slug>`, `chore/<slug>`, or `docs/<slug>` →
single PR to `main` → validation via `./dev/run <app>` and/or CI →
AI review + one human read, then the directing human merges.

Escalation rule: if implementation reveals any criterion no longer holds,
stop, and move the work to the feature workflow instead.

When in doubt, use the feature path.

Everything else is a **feature**: it requires a plan before implementation
begins.

---

## Feature Plans

Every feature must have a plan before implementation begins.

Plans live in:

```text
plans/<feature-slug>.md
```

The plan is the source of truth for feature scope.

Implementation must not begin until the initial plan has been reviewed by a human maintainer.

The required plan structure and PR description templates are defined in
[`plans/README.md`](./plans/README.md).

Allowed phase statuses:

```text
NOT STARTED
IN PROGRESS
BLOCKED
COMPLETE
```

The plan should describe outcomes and acceptance criteria, not prescribe unnecessary implementation details.

---

## Starting a Feature

A human maintainer or planning agent may prepare the feature plan.

Required sequence:

1. Update local `main`.
2. Create `feature/<feature-slug>` from `main`.
3. Add `plans/<feature-slug>.md`.
4. Commit the plan.
5. Create a milestone titled `<feature-slug>` and assign the upcoming
   feature PR to it:

   ```bash
   MID=$(gh api -X POST repos/<owner>/<repo>/milestones \
     -f title=<feature-slug> \
     -f description="<one-line goal, plan link>" --jq .number)
   ```

6. Have a human maintainer review the initial plan.
7. Open a draft pull request:

```text
feature/<feature-slug> -> main
```

The draft feature PR is the home for the overall feature.

Its description should link to the plan file and summarize the feature goal.

Do not begin implementation before the plan has been reviewed.

---

## Implementing a Phase

Each implementation phase uses its own branch and pull request.

For the next incomplete phase:

1. Make sure the feature branch is up to date.
2. Read the complete feature plan.
3. Identify the next `NOT STARTED` phase.
4. Change that phase status to `IN PROGRESS` as part of the phase work.
5. Create the phase branch from the feature branch:

```text
phase/<feature-slug>/<nn>-<phase-slug>
```

6. Implement only that phase.
7. Add or update tests required by the phase.
8. Run the required validation.
9. Update the plan if the phase has been completed successfully.
10. Open a pull request:

```text
phase/<feature-slug>/<nn>-<phase-slug>
    ->
feature/<feature-slug>
```

11. Stop and wait for review.

An agent must not automatically continue into the next phase unless it has been explicitly asked to do so after the current phase has been reviewed and merged.

---

## One Phase = One Pull Request

A phase pull request must correspond to exactly one phase in the feature plan.

Do not combine multiple planned phases into one implementation PR.

Do not add unrelated cleanup, refactors, or features to a phase PR.

Small supporting changes are allowed when they are necessary to complete the phase safely.

If additional work is useful but not required for the current phase, record it separately instead of silently expanding scope.

---

## Phase Pull Request Requirements

A phase PR must target the feature branch, never `main`.

Its description must carry `Parent: #<feature-PR>` (creates the
bidirectional GitHub link) and it must be assigned to the feature's
milestone.

Use the pull request template (it covers both feature/phase and small-change
PRs) and follow the phase PR description format from
[`plans/README.md`](./plans/README.md).

Before requesting review, verify:

- the implementation matches the phase scope;
- acceptance criteria are satisfied;
- required tests pass;
- unrelated changes are not included;
- the plan status is accurate;
- no known failure is being hidden.

---

## Phase Review

The purpose of a phase review is:

> Was this phase implemented correctly?

Reviewers should focus on:

- correctness;
- tests;
- edge cases;
- security implications;
- architecture;
- maintainability;
- scope discipline;
- acceptance criteria;
- regressions.

A phase is not complete until its PR has been reviewed and merged into the feature branch.

Phase PRs are merged with a **merge commit** (not squash). The individual
implementation commits — which should each carry their own rationale — remain
visible in the branch history and in contributors' profiles. Squash is the
exception, only when a maintainer explicitly asks for it (e.g. a noisy
fixup-heavy phase).

---

## Plan Changes During Implementation

The plan is authoritative.

Agents may make small clarifications to the plan when they do not change feature scope.

If implementation reveals that the plan requires a material change, stop implementation.

Material changes include:

- adding or removing a phase;
- changing feature scope;
- introducing a new subsystem;
- changing public behavior;
- changing important architecture;
- adding a migration not anticipated by the plan;
- changing security or permission behavior;
- invalidating existing acceptance criteria.

Required response to a material plan change:

1. Stop implementation.
2. Mark the current phase `BLOCKED` if appropriate.
3. Propose the plan change.
4. Record the proposed change under `## Plan deviations`.
5. Ask for human review.
6. Continue only after the updated plan has been approved.

Agents must not silently redesign the feature while implementing it.

---

## Keeping the Feature Branch Current

For longer-running features, `main` may move while the feature is under development.

The feature branch is responsible for absorbing changes from `main`.

Preferred direction:

```text
main
  ↓
feature
  ↓
phase
```

Do not independently merge `main` into every phase branch unless there is a specific reason.

Before starting a new phase, ensure the feature branch contains the required recent changes from `main`.

Resolve integration problems at the feature level when practical.

---

## Completing a Feature

A feature is ready for final review when:

- every planned phase is `COMPLETE`;
- every phase PR has been merged;
- all acceptance criteria are satisfied;
- the feature branch is reasonably current with `main`;
- the full relevant test suite passes;
- migrations, configuration, docs, and cleanup required by the plan are complete;
- no unresolved plan deviation remains.

At this point, update the draft feature PR:

```text
feature/<feature-slug> -> main
```

and mark it ready for review.

---

## Final Feature Review

The purpose of the final review is:

> Does this complete feature satisfy the plan and belong on `main`?

This is an integration and acceptance review.

Reviewers should check:

- the completed feature against the original goal;
- every phase and acceptance criterion;
- integration between phases;
- behavior across the whole feature;
- regressions;
- security and permissions;
- migrations and configuration;
- documentation;
- test coverage;
- unexpected scope changes;
- unresolved plan deviations;
- the complete diff from `main`.

The final review does not need to repeat every line-level decision already reviewed in phase PRs, but reviewers may revisit any code when necessary.

The final `feature/* -> main` PR must be reviewed by the human maintainers.

Agents may assist with review, testing, summaries, and finding issues, but agents must not approve or merge the final feature PR.

The feature PR should normally be merged with a **merge commit** so the feature's phase-level history remains visible.

---

## Review Model

Verification is layered (validated during the local-ci-and-workflow
feature, 2026-08):

1. **CI gates** — mechanical truth; every mechanical failure in that
   feature's history was caught here (inherited dependency rot,
   syntax errors, gate semantics).
2. **AI first-pass review** — design-level findings (the review rounds
   on PRs #17/#19/#23 caught gate-skips, premature docs, filter
   mismatches). The standing implementation lives in `ci-toolkit`;
   until it exists, relay the diff through an AI reviewer manually.
3. **Human judgment** — plan approval, deviation decisions, and the
   merge decision itself.

Approving reviews are NOT required by branch protection. The
expectation before any merge: AI review pass + one human read by the
directing human, who clicks merge. Agents never approve or merge.
Collaborator reviews (Lukas) are welcome contributions, fresh-eyes
value — never a tollbooth.

## Agent Roles

An agent may operate in one of these roles.

### Planner

Responsibilities:

- understand the requested feature;
- inspect the existing repository;
- create or update the feature plan;
- divide work into coherent phases;
- define acceptance criteria;
- identify dependencies and risks.

A planner does not begin implementation unless explicitly asked.

### Implementer

Responsibilities:

- read this file;
- read the complete feature plan;
- work on exactly one assigned phase;
- keep changes within scope;
- add tests;
- run validation;
- update phase status;
- prepare the phase PR.

An implementer must stop after preparing or updating the phase PR unless explicitly instructed to continue.

### Reviewer

Responsibilities:

- read the plan;
- inspect the diff;
- inspect relevant existing code;
- evaluate tests and validation;
- identify correctness, security, maintainability, and scope problems;
- verify acceptance criteria.

A reviewer should judge the code independently and should not assume the implementation is correct because another agent produced it.

Where practical, implementation and review should use separate agent sessions or fresh context.

---

## Agent Operating Procedure

Before making code changes, an implementation agent must answer these questions from repository state:

1. What feature branch am I working under (or is this a small change)?
2. Where is the feature plan?
3. Which phase am I implementing?
4. What are the acceptance criteria?
5. What is explicitly outside the phase scope?
6. What tests or validation are required?
7. What branch will the PR target?

If any of these cannot be determined reliably, stop and ask for clarification.

Before finishing, the agent must verify:

1. I changed only what this phase or small change requires.
2. I did not silently change the feature plan.
3. I added or updated appropriate tests.
4. I ran the required validation.
5. I documented any known limitation.
6. I updated the plan status correctly.
7. My PR targets the correct branch, never `main` directly for phases.

---

## Stop Conditions

An agent must stop and ask for human input when:

- the requested work conflicts with the plan;
- the current branch does not match the expected workflow;
- there is no approved plan for feature-scale work;
- a material plan change is required;
- acceptance criteria are ambiguous or contradictory;
- required credentials, secrets, or external access are missing;
- a migration or destructive operation was not anticipated;
- security or permission behavior is unclear;
- the agent discovers unrelated failures that materially affect the phase;
- continuing would require implementing another phase;
- the agent is unsure which branch should receive the work.

Stopping is preferred to guessing.

---

## Prohibited Agent Actions

Unless a human explicitly overrides this file for a specific task, agents must not:

- commit directly to `main`;
- push directly to `main`;
- merge into `main`;
- approve the final feature PR;
- merge a phase PR without review;
- implement multiple phases in one PR;
- silently expand feature scope;
- silently rewrite an approved plan;
- skip required tests to make a PR appear complete;
- hide failing tests or known regressions;
- remove tests merely because they fail after a change;
- perform unrelated repository-wide refactors inside a feature phase;
- introduce secrets or credentials into the repository;
- force-push shared integration branches;
- delete remote branches belonging to active work without approval.

---

## Git Workflow Summary

### Start feature

```bash
git checkout main
git pull
git checkout -b feature/<feature-slug>
```

Create and commit:

```text
plans/<feature-slug>.md
```

Open:

```text
feature/<feature-slug> -> main
```

as a draft PR.

### Start phase

```bash
git checkout feature/<feature-slug>
git pull
git checkout -b phase/<feature-slug>/<nn>-<phase-slug>
```

Implement and open:

```text
phase/<feature-slug>/<nn>-<phase-slug>
    ->
feature/<feature-slug>
```

Review and merge with a merge commit.

### Small change

```bash
git checkout main
git pull
git checkout -b fix/<slug>   # or chore/<slug> | docs/<slug>
```

Implement, validate (`./dev/run <app>`), open one PR to `main`, review, merge.

### Finish feature

When all phases are complete:

```text
feature/<feature-slug>
    ->
main
```

Run final integration review.

Human maintainers review and merge.

---

## Default Decision Rule

When the correct next action is unclear, use this priority order:

1. Protect `main`.
2. Follow the approved plan.
3. Keep the current PR limited to one phase.
4. Prefer explicit human review over assumptions.
5. Stop rather than silently expanding scope.

The workflow is successful when small implementation decisions can be delegated to agents while feature scope, integration, and release decisions remain explicit and reviewable.


---

## Branching From Verified State (lifecycle invariants)

Lessons from real failures, 2026-08:

1. **Branch from verified `main`** (or from the feature branch, for
   phases) — never from an unmerged PR head. Before branching, fetch
   and confirm the base's merge state (`gh pr view <n> --json state`).
   Branching off an unmerged PR head silently drags unrelated work
   into your PR's diff.
2. **A phase PR must never merge into a feature branch whose parent
   feature PR has already landed.** If the parent merges early, close
   the feature branch and target `main` directly with the remaining
   work.
3. **Verify what your PR actually carries** before declaring it ready:
   `gh pr diff <n> --name-only` must match the intended scope. A PR
   description that contradicts its diff is a defect.
