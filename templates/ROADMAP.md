<!-- ci-toolkit governance copy-template: plans/ROADMAP.md
     COPY into your repo and ADAPT. Never reference across repos.
     Now/Next/Later/Parked/Done + 'Last reviewed' date. -->

# Roadmap

The overview ABOVE the individual feature plans. One file, always current.

Last reviewed: 2026-08-28

**Contract:**
- **Agents**: read this at the start of every session before proposing work.
  Never edit silently — changes go through a PR like everything else.
- **Humans**: this is the priority list AND the parking lot. When focus
  drifts (it will), park the thing here with a resume note instead of
  losing it. Re-entry = reading, not remembering.

**Layering:** this file says *what and why now* → `plans/<feature>.md`
says *how* (phases, acceptance criteria) → `docs/task-management/` holds
detailed task cards. A roadmap item with a plan file is a commitment;
without one it's an intention.

## Now — active

- **local-ci-and-workflow** (Phase 5, final review): merge #26 → re-ready
  #16 → Lukas merges → protection-context swap to `backend-summary` +
  `mobile-summary` + docs-only scratch PR validation.
  Plan: `plans/local-ci-and-workflow.md` · milestone: `local-ci-and-workflow`

## Next — queued, order matters

1. **ai-pr-review** implementation (approved plan, PR #24): public
   `ci-toolkit` + OpenRouter advisory reviewer, rollout per plan.
   Promoted to first after the Deviation 3 redesign (2026-08-28): the
   AI reviewer is now the load-bearing first-pass layer in the review
   model, so it should exist before routine solo merges pile up.
2. **kode-verket repo transfer** to the personal account + runner
   registration + remote fixes (guide:
   `docs/documentation/tooling/new-repo-ci-checklist.md`).

## Later — intentions, no plan yet

- **ci-toolkit extraction**: shrink per-repo CI setup to a caller +
  inputs; may merge into ai-pr-review's rollout phase.
- **Tighten `enforce_admins`** — trade-off: would make even the
  director's merges wait for green checks, blocking evening merges
  while the self-hosted pool sleeps. Flip when evening-merge tolerance
  exists (e.g. after heavy legs move to hosted or overnight wake).
- **CODEOWNERS targeting for Lukas** — his reviews become
  automatically-requested on paths he knows (web), fresh-eyes value
  without being a universal tollbooth.
- **Machine account pattern** (parked in the redesign discussion):
  a dedicated merge-account would let agents merge under auditable
  non-human identity. Requires GitHub plan/trust decisions first.
- **student_app archive decision** (stale pre-monorepo mirror).
- **Web CI coverage** — Lukas's responsibility, tracked here for
  visibility only.

## Parked — deliberately paused, resume criteria noted

- (empty — first drift goes here: one line + "resume when/how")

## Done — 2026-08

- Self-hosted CI pool (3 runners), branch protection, fast lane,
  workflow/docs overhaul — `local-ci-and-workflow` phases 1–4 (PRs #17,
  #19, #20, #23).
