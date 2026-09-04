<!-- ci-toolkit governance copy-template: .github/PULL_REQUEST_TEMPLATE.md
     COPY into your repo and ADAPT. Never reference across repos.
     Covers feature-umbrella, feature-phase, and small-change PRs. -->

## Change type

<!-- Delete whichever does not apply. -->

- [ ] Small change (`fix/*`, `chore/*`, `docs/*` -> `main`)
- [ ] Feature umbrella (`feature/*` -> `main`)
- [ ] Feature phase (`phase/*` -> `feature/*`)

## Umbrella PR format (delete if not the umbrella)

<!-- Open as draft; stays draft until every phase has merged and final
     validation is complete. Keep this section short — the plan and the
     milestone already know the family. -->

## Plan

`plans/<feature-slug>.md` (on this branch)

## Goal

One or two sentences.

## Current state

<!-- At each review boundary, update to the exact current head:
     phases complete / in flight / blocked, drift assessment vs
     current `main`, known limitations. A description that
     contradicts the diff is a defect. -->

## Phase PR format (delete if not a phase PR)

## Plan

`plans/<feature-slug>.md`

## Phase

Phase N — <phase name>

## Parent

Parent: #<umbrella-PR> · Milestone: `<feature-slug>` (assign on the sidebar)

## What changed

- Summary

## Acceptance criteria

- [ ] Criterion

## Small-change checklist (delete if umbrella or phase PR)

## What changed

- Summary

## Why

The problem this solves.

- [ ] no data model, schema, or migration changes
- [ ] no cross-client contract changes
- [ ] no security or permissions behavior
- [ ] no CI/workflow or build-config changes
- [ ] no new runtime dependencies
- [ ] touches one app or service plus its tests

<!-- If any box is unchecked, this belongs on the feature path instead
     (see AGENTS.md, "Which Path"), unless the directing human recorded
     a narrow-exception rationale here. -->

## Validation

- `command`

## Notes

Anything reviewers should know.
