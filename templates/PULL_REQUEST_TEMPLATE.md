<!-- ci-toolkit governance copy-template: .github/PULL_REQUEST_TEMPLATE.md
     COPY into your repo and ADAPT. Never reference across repos.
     Covers feature/phase and small-change PRs. -->

## Change type

<!-- Delete whichever does not apply. -->

- [ ] Small change (`fix/*`, `chore/*`, `docs/*` -> `main`)
- [ ] Feature phase (`phase/*` -> `feature/*`)

## Phase PR format (delete if small change)

## Plan

`plans/<feature-slug>.md`

## Phase

Phase N — <phase name>

## Parent

Parent: #<feature-PR> · Milestone: `<feature-slug>` (assign on the sidebar)

## What changed

- Summary

## Acceptance criteria

- [ ] Criterion

## Small-change checklist (delete if phase PR)

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
     (see AGENTS.md, "Which Path"). -->

## Validation

- `command`

## Notes

Anything reviewers should know.
