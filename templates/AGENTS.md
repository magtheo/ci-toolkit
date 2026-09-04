<!-- ci-toolkit governance copy-template: AGENTS.md
     COPY this file into your repo's root and ADAPT it (repo layout,
     validation commands, docs hubs, CI specifics, repo-specific
     operational exceptions). Never reference shared governance across
     repos — each repo owns its rules.

     This file is the CANONICAL GENERIC BASELINE. Repositories copy it
     and adapt. When a lived incident in any consumer repo reveals a
     broadly useful invariant, backport it here deliberately via a
     reviewed PR. There is no automated cross-repo synchronization. -->

# AGENTS.md

## Purpose

This repository uses a two-level branch workflow designed for human +
coding-agent collaboration.

This file defines the required workflow for humans and agents. Its
goals: keep `main` stable; make every risky change start from an
explicit written plan; give coding agents small, bounded tasks; review
each phase independently; review the completed feature as a whole
before it reaches `main`; prevent agents from silently expanding scope
or merging unreviewed work.

Adapt the repo-specific sections (layout, validation commands,
documentation hubs) to your repository before committing.

---

## Workflow at a glance

Small change:

```text
main -> fix/ | chore/ | docs/ -> PR -> validation -> review -> human merge
```

Feature:

```text
main
  -> feature/<name> + approved plan (draft umbrella PR)
     -> phase/01 -> review -> merge to feature
     -> phase/02 -> review -> merge to feature
     -> ...
     -> drift assessment against current main
     -> whole-feature validation + review
     -> human merges feature -> main
```

Standing rules:

- `main` is the only permanent integration branch.
- One `feature/*` branch = one independently mergeable feature.
- One active phase branch per feature, sequential by default.
- Agents never merge into `main`; agents write only branches they
  created for the current task or branches explicitly assigned to them.

---

## Working in this repo

<!-- FILL IN: repository layout, validation commands, CI summary,
     documentation hubs. Keep it short — orientation, not
     documentation. -->

---

## Branch Architecture

```text
main
├── fix/<slug> | chore/<slug> | docs/<slug>          (small changes)
└── feature/<feature-slug>
    └── phase/<feature-slug>/<nn>-<phase-slug>       (planned features)
```

### `main`

`main` is the repository's **only permanent integration branch**.

- Do not commit or push implementation work directly to `main`.
- Agents must never merge into `main`.
- Work reaches `main` only through a reviewed pull request.

### Architecture invariants

- A `feature/*` branch represents exactly **one coherent outcome**
  that can be independently reviewed and merged to `main`. It is
  temporary and ends when the feature lands. It must not become a
  contributor branch, product-area branch, roadmap initiative, or
  general integration branch holding otherwise-independent features.
- If two outcomes can reasonably reach `main` independently, they are
  two features on two feature branches.
- Do **not** create permanent `develop`, staging, team, contributor,
  product-area, or initiative branches between `main` and `feature/*`.
  A permanent middle integration layer does not remove drift; it hides
  it until it arrives as a larger batch.
- A temporary integration or release branch is an explicit exception:
  it requires a human decision, a concrete reason `main`/`feature`/
  `phase` cannot safely represent the work, and a defined condition
  for deleting the branch.
- Deployment environments (development, staging, production) are not
  Git branches. Promote tested commits through deployment controls;
  do not mirror environments in branch topology.

### Small-change branches

`fix/<slug>`, `chore/<slug>`, or `docs/<slug>` target `main` directly in a
single PR.

### `feature/*`

A feature branch is the integration branch for one planned feature.
It contains the feature plan, all completed implementation phases,
integration fixes that belong to the feature, and the complete diff
that will eventually be reviewed against `main`.

A feature branch is created from an up-to-date `main` (see
[Branching From Verified State](#branching-from-verified-state-lifecycle-invariants)).

The feature branch is not used for normal implementation work.
Implementation happens on phase branches.

### `phase/*`

A phase branch implements exactly one phase from the feature plan. It
is created from the current feature branch, not from `main`, and its
pull request targets that feature branch.

### Phase sequencing

- Phases are **sequential by default**:

  ```text
  feature -> phase N -> review -> merge into feature -> phase N+1
  ```

  The normal state is at most one unmerged implementation phase per
  feature.
- **Parallel phases from the same feature head** are allowed only when
  the approved plan explicitly declares those phases independent.
- **Phase-on-phase stacking** (creating phase N+1 from an unmerged
  phase N branch) is an exception requiring explicit human approval
  for a concrete reason. Stacked unmerged phases multiply integration
  work and hide dependency drift.

### Branch ownership

- An agent may write only to branches **it created for the current
  task** or branches **explicitly assigned by the directing human**.
  Every other branch is foreign: read it, never push to it.
- Ownership controls who may *write* a branch. It does not make the
  owner responsible for repository-wide integration: a contributing
  human or agent manages their feature, and the directing human (who
  may explicitly assign an agent to do the Git work) owns integration.
- Typical assigned integration operation: "integrate current `main`
  into `feature/<foo>`" — after that explicit assignment the agent may
  perform exactly that.
- On shared feature branches, prefer merging `main` into the feature
  over rebasing or force-pushing it: shared history must not be
  rewritten.

---

## Naming

Use lowercase kebab-case.

Feature branches: `feature/<feature-slug>` (e.g. `feature/course-enrollment`).

Phase branches: `phase/<feature-slug>/<nn>-<phase-slug>`
(e.g. `phase/student-dashboard/01-data-model`).

Phase numbers should match the phase ordering in the plan.

Milestones: one per feature, titled `<feature-slug>` — every PR in the
family (umbrella PR + all phase PRs) is assigned to it. The milestone
page is the family view GitHub actually indexes; PR numbers alone are
flat and carry no relationship.

---

## Which Path: Small Change or Feature?

A change qualifies as **small** only if ALL of these hold:

- no data model, schema, or migration changes;
- no cross-component contract changes (API/config shapes shared between
  parts of the repo — adapt to your topology);
- no security or permissions behavior;
- no CI/workflow or build-config changes;
- no new runtime dependencies;
- touches one app or service plus its tests.

Small-change workflow: branch `fix/<slug>`, `chore/<slug>`, or `docs/<slug>` →
single PR to `main` → validation via <VALIDATION_COMMAND> and/or CI →
AI review + one human read, then the directing human merges.

Escalation rule: if implementation reveals any criterion no longer holds,
stop, and move the work to the feature workflow instead.

**Narrow human exception:** a human maintainer may explicitly authorize
a small-change path when a failed criterion is narrow and the feature
workflow would not materially increase safety. The PR must name the
failed criterion and record the rationale. Agents may never grant this
exception to themselves.

When in doubt, use the feature path.

Everything else is a **feature**: it requires a plan before implementation
begins.

---

## Feature Plans

Every feature must have a plan before implementation begins.

Plans live in `plans/<feature-slug>.md` and are **read from the feature
branch** while the feature is open — that copy is the authoritative one
(see [Source-of-Truth Hierarchy](#source-of-truth-hierarchy)).

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

If phases are intended to run in parallel, the plan must declare them
independent explicitly (see Phase sequencing).

---

## Starting a Feature

A human maintainer or planning agent may prepare the feature plan.

Required sequence:

1. Update local `main`.
2. Create `feature/<feature-slug>` from `main`.
3. Add `plans/<feature-slug>.md` and commit it.
4. Create a milestone titled `<feature-slug>` (one-line goal + plan
   link) for the whole PR family.
5. Have a human maintainer review the initial plan.
6. Open a **draft umbrella pull request**:

```text
feature/<feature-slug> -> main
```

The umbrella PR is the home for the overall feature: it links the plan,
carries the feature goal, and stays draft until every phase has merged
and final validation is complete.

Do not begin implementation before the plan has been reviewed.

---

## Implementing a Phase

Each implementation phase uses its own branch and pull request.

For the next incomplete phase:

1. Make sure the feature branch is up to date (see
   [Keeping Current with `main`](#keeping-current-with-main-drift-triage)).
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
phase/<feature-slug>/<nn>-<phase-slug> -> feature/<feature-slug>
```

11. Stop and wait for review.

An agent must not automatically continue into the next phase unless it has been explicitly asked to do so after the current phase has been reviewed and merged.

---

## Phase Pull Request Requirements

A phase PR must correspond to exactly one phase in the feature plan:
never combine multiple planned phases into one implementation PR, and
never add unrelated cleanup, refactors, or features to a phase PR.
Small supporting changes are allowed when they are necessary to
complete the phase safely; if additional work is useful but not
required for the current phase, record it separately instead of
silently expanding scope.

A phase PR must target the feature branch, never `main`.

Its description must carry `Parent: #<umbrella-PR>` (creates the
bidirectional GitHub link) and it must be assigned to the feature's
milestone.

Use the pull request template (it covers umbrella, phase, and
small-change PRs) and follow the phase PR description format from
[`plans/README.md`](./plans/README.md).

**PR-description freshness:** before requesting any review, refresh the
PR title and body so its claims, acceptance state, and known
limitations describe the exact current head. A PR description that
contradicts its diff is a defect.

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

Reviewers judge correctness, tests, edge cases, security, architecture,
maintainability, scope discipline, acceptance criteria, and regressions.

A phase is not complete until its PR has been reviewed and merged into the feature branch.

Phase PRs are merged with a **merge commit** (not squash), so the
individual implementation commits — each carrying their own rationale —
remain visible in branch history and contributors' profiles. Squash is
the exception, only when a maintainer explicitly asks for it (e.g. a
noisy fixup-heavy phase).

---

## Plan Changes During Implementation

The plan is authoritative.

Agents may make small clarifications to the plan when they do not change feature scope.

If implementation reveals that the plan requires a material change, stop implementation.

Material changes: adding or removing a phase; changing feature scope;
introducing a new subsystem; changing public behavior or important
architecture; adding an unanticipated migration; changing security or
permission behavior; invalidating existing acceptance criteria.

Required response: stop implementation, mark the current phase
`BLOCKED` if appropriate, propose the change under `## Plan
deviations`, ask for human review, and continue only after approval.

Agents must not silently redesign the feature while implementing it.

---

## Keeping Current with `main` (drift triage)

For longer-running features, `main` may move while the feature is under
development. The feature branch — not every phase branch — absorbs
changes from `main`:

```text
main -> feature -> phase
```

Do not merge `main` into phase branches without a specific reason, and
do not synchronize just because `main` has more commits.
**Commit count alone is never a reason to synchronize** — relevance is.

Triage `main` drift by what changed:

| `main` drift | response |
| --- | --- |
| Unrelated to this feature (docs, CI polish, other apps/services, orthogonal infrastructure) | Ignore during the current phase. |
| Shared code or dependency, but no direct contract overlap | Integrate at the next phase boundary. |
| Same files, or an API/schema/security/data-model contract this feature depends on | Coordinate and integrate before continuing. |
| Feature ready for whole-feature review | Mandatory drift assessment — see below. |

**Before whole-feature review**, assess the feature against current
`main`. The assessment is mandatory; the merge is not unconditional:

- if the drift is relevant, integrate `main` into the feature branch
  and resolve;
- if it is clearly unrelated, **record that judgment** (a sentence in
  the umbrella PR) and proceed.

Reviewing something close to what will actually land is the point; a
ritual merge of unrelated drift is not.

Resolve integration problems at the feature level when practical.

---

## Completing a Feature

A feature is ready for final review when:

- every planned phase is `COMPLETE`;
- every phase PR has been merged;
- all acceptance criteria are satisfied;
- the mandatory drift assessment against current `main` has been made
  (and relevant drift integrated);
- the full relevant test suite passes;
- migrations, configuration, docs, and cleanup required by the plan are complete;
- no unresolved plan deviation remains.

At this point, update the umbrella PR:

```text
feature/<feature-slug> -> main
```

refresh its description to describe the exact current state, and mark
it ready for review.

---

## Final Feature Review

The purpose of the final review is:

> Does this complete feature satisfy the plan and belong on `main`?

This is an integration and acceptance review. Reviewers check the
completed feature against the original goal; every phase and
acceptance criterion; integration between phases; whole-feature
behavior and regressions; security and permissions; migrations and
configuration; documentation and test coverage; unexpected scope
changes; unresolved plan deviations; and the complete diff from
`main`. The final review does not need to repeat every line-level
decision already reviewed in phase PRs, but reviewers may revisit any
code when necessary.

The final `feature/* -> main` PR must be reviewed by the human maintainers.

Agents may assist with review, testing, summaries, and finding issues, but agents must not approve or merge the final feature PR.

The umbrella PR should normally be merged with a **merge commit** so the feature's phase-level history remains visible.

---

## Source-of-Truth Hierarchy

| Question | Authority |
| --- | --- |
| What is actually open / merged / green right now? | GitHub (derive it; never duplicate it into documents) |
| What workflow rules apply? | this file (`AGENTS.md`) |
| What must this feature accomplish? | `plans/<feature-slug>.md` **on the feature branch** while the feature is open |
| What should we work on next? | the repository roadmap (priorities only, not live PR state) |
| What does this subsystem require? | nested docs, where present |

A roadmap or plan that duplicates live GitHub state (open/closed,
head SHAs, phase-PR inventories) will rot; GitHub already knows. Agents
should read documents for intent and query GitHub for state.

---

## Review Model

Verification is layered (cite your own repo's evidence here when you
adopt this model — e.g. "validated during <FEATURE>, <DATE>:"):

1. **CI gates** — mechanical truth; every mechanical failure in that
   feature's history was caught here (inherited dependency rot,
   syntax errors, gate semantics).
2. **AI first-pass review** — design-level findings. The standing
   implementation lives in `ci-toolkit` (reusable advisory reviewer);
   until a repo installs it, relay the diff through an AI reviewer
   manually.
3. **Human judgment** — plan approval, deviation decisions, and the
   merge decision itself.

Approving reviews are NOT required by branch protection. The
expectation before any merge: AI review pass + one human read by
the directing human, who clicks merge. Agents never approve or merge.
Collaborator reviews are welcome contributions, fresh-eyes
value — never a tollbooth.

---

## Agent Roles

An agent may operate in one of these roles.

**Planner** — understand the requested feature; inspect the existing
repository; create or update the feature plan; divide work into
coherent phases; define acceptance criteria; identify dependencies
and risks. A planner does not begin implementation unless explicitly
asked.

**Implementer** — read this file and the complete feature plan; work
on exactly one assigned phase; keep changes within scope; add tests;
run validation; update phase status; prepare the phase PR. An
implementer must stop after preparing or updating the phase PR unless
explicitly instructed to continue.

**Reviewer** — read the plan; inspect the diff and relevant existing
code; evaluate tests and validation; identify correctness, security,
maintainability, and scope problems; verify acceptance criteria. A
reviewer judges independently and does not assume correctness because
another agent produced the implementation. Where practical,
implementation and review use separate agent sessions or fresh
context.

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
8. My PR description describes the exact current head.

---

## Stop Conditions

An agent must stop and ask for human input when:

- the requested work conflicts with the plan, or the plan requires a
  material change;
- the current branch does not match the expected workflow, or the
  agent is unsure which branch should receive the work — including
  when the work would require writing to a foreign (not
  created-for-this-task, not explicitly assigned) branch;
- there is no approved plan for feature-scale work;
- acceptance criteria are ambiguous or contradictory;
- required credentials, secrets, or external access are missing;
- a migration or destructive operation was not anticipated;
- security or permission behavior is unclear;
- the agent discovers unrelated failures that materially affect the phase;
- continuing would require implementing another phase.

Stopping is preferred to guessing.

---

## Prohibited Agent Actions

Unless a human explicitly overrides this file for a specific task, agents must not:

- commit, push, or merge directly to `main`, or approve or merge PRs
  (phase PRs merge only after review; agents never approve the final
  feature PR);
- implement multiple phases in one PR;
- silently expand feature scope, or silently rewrite an approved plan;
- skip required tests to make a PR appear complete; hide failing
  tests or known regressions; or remove tests merely because they
  fail after a change;
- perform unrelated repository-wide refactors inside a feature phase;
- introduce secrets or credentials into the repository;
- push to, rebase, or otherwise rewrite any branch that is not theirs
  for the current task or explicitly assigned to them;
- delete remote branches belonging to active work without approval.

---

## Branching From Verified State (lifecycle invariants)

Lessons from real failures, 2026-08:

1. **Branch from verified `main`** (or from the feature branch, for
   phases) — never from an unmerged PR head. Before branching, fetch
   and confirm the base actually landed:
   `gh pr view <n> --json state,mergedAt` — require `mergedAt` to be
   non-null (`state` alone says OPEN/CLOSED; closed is not merged).
   Branching off an unmerged PR head silently drags unrelated work
   into your PR's diff.
2. **A phase PR must never merge into a feature branch whose parent
   feature PR has already landed.** If the parent merges early, close
   the feature branch and target `main` directly with the remaining
   work.
3. **Verify what your PR actually carries** before declaring it ready:
   `gh pr diff <n> --name-only` must match the intended scope. A PR
   description that contradicts its diff is a defect.

---

## Default Decision Rule

When the correct next action is unclear, use this priority order:

1. Protect `main`.
2. Follow the approved plan.
3. Keep the current PR limited to one phase.
4. Prefer explicit human review over assumptions.
5. Stop rather than silently expanding scope.

The workflow is successful when small implementation decisions can be delegated to agents while feature scope, integration, and release decisions remain explicit and reviewable.
