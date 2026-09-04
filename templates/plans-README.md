<!-- ci-toolkit governance copy-template: plans/README.md
     COPY into your repo and ADAPT. Never reference across repos.
     Plan structure + PR description templates. -->

# Feature Plans

Every feature must have a plan before implementation begins
(see [`AGENTS.md`](../AGENTS.md) for the full workflow).

Plans live in this directory as:

```text
plans/<feature-slug>.md
```

The plan is the source of truth for feature scope. Implementation must not
begin until the initial plan has been reviewed by a human maintainer.

While a feature is open, the authoritative copy of its plan lives **on the
feature branch** — main's copy may be stale until the umbrella PR merges.

Phases are sequential by default. If any phases are intended to run in
parallel from the same feature head, the plan must explicitly declare them
independent (see AGENTS.md, "Branch Architecture").

Small changes (see `AGENTS.md`, "Which Path: Small Change or Feature?") do
**not** need a feature plan — they go directly to a single PR against `main`
using the small-change checklist in the PR template.

---

## Required plan structure

```md
# Feature Name

## Goal

Short description of the user-facing or system-level outcome.

## Non-goals

What this feature intentionally does not include.

## Constraints

Important architectural, compatibility, security, or product constraints.

## Phase 1 — Name

Status: NOT STARTED

### Scope

- Work item
- Work item

### Acceptance criteria

- Observable requirement
- Testable requirement

### Validation

- Tests to run
- Manual checks if required

## Phase 2 — Name

Status: NOT STARTED

...

## Plan deviations

Record approved material changes to the plan here.
```

Allowed phase statuses:

```text
NOT STARTED
IN PROGRESS
BLOCKED
COMPLETE
```

The plan should describe outcomes and acceptance criteria, not prescribe
unnecessary implementation details.

---

## Milestones — the family view

PR numbers are a flat global counter; they carry no parent/child
information. The relationship is made visible two ways:

- every phase PR's description carries `Parent: #<feature-PR>`, which
  creates a bidirectional link in both PR timelines;
- every PR in the family (feature PR + all phase PRs) is assigned to a
  milestone titled `<feature-slug>`, created when the feature starts —
  the milestone page is the one place GitHub indexes and aggregates the
  whole family with progress.

---

## PR description templates

### Umbrella PR (`feature/*` -> `main`, draft until complete)

```md
## Plan

`plans/<feature-slug>.md` (on this branch)

## Goal

One or two sentences.

## Current state

<!-- At each review boundary: phases complete / in flight / blocked,
     drift assessment vs current `main`, known limitations. -->
```

Keep the umbrella description short — the plan and the milestone
already know the family. Refresh "Current state" at every review
boundary; a description that contradicts the diff is a defect.

### Phase PR (targets the feature branch)

```md
## Plan

`plans/<feature-slug>.md`

## Phase

Phase N — <phase name>

## Parent

Parent: #<feature-PR> · Milestone: `<feature-slug>`

## What changed

- Summary
- Summary

## Acceptance criteria

- [x] Criterion
- [x] Criterion

## Validation

- `command`
- `command`

## Notes

Anything reviewers should know.
```

### Small-change PR (targets `main`)

```md
## What changed

- Summary

## Why

The problem this solves.

## Small-change criteria

- [ ] no data model, schema, or migration changes
- [ ] no cross-client contract changes
- [ ] no security or permissions behavior
- [ ] no CI/workflow or build-config changes
- [ ] no new runtime dependencies
- [ ] touches one app or service plus its tests

## Validation

- `command`
```
