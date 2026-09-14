<!-- ci-toolkit governance copy-template: adapt into your repo's CI
     conventions (e.g. AGENTS.md "CI rules" section or a dedicated doc).
     Policy text — adapt names/numbers to your runner fleet; do not
     reference this file across repos at runtime. -->

# Self-hosted runner job hygiene

## Scope

This template governs **workflow-side** behavior of jobs that declare
`runs-on: [self-hosted, ...]` on the shared self-hosted runner fleet.

It does **not** govern host configuration. Host-level guarantees — cgroup
ceilings on runner services, hardware watchdog, earlyoom, dead-man
monitoring — are owned by the host operator, not by any consuming repo.
The split is deliberate and must hold in both directions:

```text
host operator   → host guarantees  (what actually fences a runaway job)
consumer repos  → job hygiene      (per-job budgets; fail loud, fail small)
```

A workflow-side cap is defense-in-depth, not the primary fence. It exists
so that a runaway job **fails visibly in the GitHub UI** instead of
silently degrading a host shared by other runners and services.

## Why this exists

Motivating incident (observed 2026-09): an uncapped "Docker build" job on
a shared self-hosted runner host consumed all RAM, dragged the kernel into
a swap-thrashing livelock (with swap configured, the OOM killer never
fires — reclaim always "progresses"), and froze the host for 18 hours. No
job failed; nothing crashed; the host simply stopped.

The host-side half of the fix belongs to the host operator. This template
is the job-side half.

## Rules

### R1 — Docker builds must cap build memory

Docker-build jobs on self-hosted runners must set an explicit memory
budget on the build itself:

```bash
# classic builder
docker build --memory=6g ...

# buildx, docker-container driver: cap the builder container
docker buildx create --driver docker-container \
  --driver-opt memory=6g,name=capped-builder ...
```

The buildkit container charges its memory to **dockerd's cgroup, not the
job's** — so a runner-service cgroup ceiling alone does not bound a
docker-container build. Workflow-level caps are the only per-job bound
for this path. This is the exact path that caused the motivating
incident.

### R2 — Service containers get budgets too

Jobs that spawn databases/brokers/services must cap each container
(`docker run --memory=...`, compose `mem_limit`, or service-container
`options`). A runaway test dependency is the same blast radius as a
runaway build.

### R3 — Fail loud, fail bounded

- Every self-hosted job sets `timeout-minutes` — a wedged job must die,
  not squat on a runner.
- Matrix jobs that fan out on shared runners set a sensible
  `max-parallel`; the fleet runs multiple runners on one memory-bounded
  host.

### R4 — Budget for a shared host

Write jobs as if the host is fully occupied by others, because it is:
multiple runners, long-lived services, and interactive sessions share it.
A job's declared budget (R1/R2) should assume a fraction of host RAM, not
all of it.

### R5 — Known-lightweight jobs

`ai-review.yml` aimed at a self-hosted runner is acceptable without extra
caps: its footprint is one GitHub API fetch, one model call, and prompt
construction — bounded by the host ceiling. This is documentation of
expectation, not an exemption from host-side limits.

## Reviewer checklist (fold into PR review for CI changes)

- [ ] new/changed self-hosted jobs: `timeout-minutes` present?
- [ ] docker build/buildx steps carry a memory cap?
- [ ] spawned service containers capped?
- [ ] fan-out bounded (`max-parallel`)?
