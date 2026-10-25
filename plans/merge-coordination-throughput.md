# Merge coordination and CI throughput — design proposal

Status: **PROPOSED / documentation only** (2026-10-25).
Owner of reusable governance: **ci-toolkit**. First consumer evidence:
[platform-core PR #228](https://github.com/magtheo/platform-core/pull/228).
Related source of authority: [MATURITY_ROADMAP.md §3.7](../MATURITY_ROADMAP.md)
and [AGENTS.md](../AGENTS.md).

**This document does not authorize automated merges, change branch policy,
or introduce a new reusable workflow.** Current ci-toolkit policy says
agents never approve or merge PRs. Any move from human-performed merges to
deterministic execution of human-authorized merges requires a separately
reviewed governance decision and implementation.

## 1. The observed problem

In the 2026-10-24 platform-core #228 merge episode, the operator reported:

- Approximately three hours elapsed, with roughly 15 minutes of direct work.
- A moving `main` and an up-to-date branch requirement repeatedly invalidated
  previously green checks. Other PRs (#235, #237, #238) landed during the
  episode, requiring branch refresh and full validation more than once.
- Full CI attempts took approximately 30–40 minutes, with a serialized
  Docker-smoke tail on a shared runner.
- A previously observed `seed.test.ts` 20-second environment/load timeout
  caused another validation attempt.
- Fixed-interval polling, a stale local ref, and disabled repository
  auto-merge added avoidable operator delay.

These are **reported episode observations**, not a controlled latency
benchmark. The true split between execution, runner queue, check invalidation
and operator delay needs measurement. The branch-protection rule was reported
by the operator; this design note is **not** an independent audit of private
GitHub branch-protection settings.

**Failure mode:** Approved PRs are independently refreshed and requalified
while other agents continue merging to the same trunk. A green test result
can become ineligible for merge before it is used, multiplying expensive CI
attempts. Speeding up each Docker build alone does not resolve this.

## 2. Ownership: three separate responsibilities

| Surface | Responsibility | Must not do |
| --- | --- | --- |
| **ci-toolkit** | Reusable governance, exact-head readiness evidence, stale-result semantics, handoff/coordination contract and metrics definitions | Treat AI `Clear` as approval; hold application secrets; grant itself merge authority |
| **Consumer repository (platform-core)** | CI dependency graph, component-aware smoke selection, fail-open qualification, Docker scheduling and release/publication checks | Weaken required qualification just to accelerate a merge |
| **Project-level coordinator** (initially a human procedure; later possibly an executive/orchestration system) | Order approved candidate PRs, avoid concurrent merge attempts, record status and facilitate handoff | Self-authorize a merge, bypass GitHub protections, or merge under present agent policy |

The CI toolkit reviewer remains **advisory and independent**. A merge
coordinator is not a new feature of the LLM reviewer and should not be
implemented by adding write-to-main credentials to the reviewer workflow.
A future merge executor, if approved, should be a separately secured
component with its own identity, tightly scoped permissions, and audit log.

## 3. Minimal human-operated protocol (proposed)

This is the preferred first experiment. It can begin as an operating
procedure without a service or additional permanent branch.

1. **Collect candidates.** An implementation agent submits a PR, evidence
   and an exact head SHA. CI and AI review are evidence, not authorization.
2. **Human decision.** The maintainer authorizes a *specific reviewed change*
   through the repository's accepted process. The record must identify the
   scope and revision it applies to. New code after that revision requires
   fresh evidence and a new authorization unless an explicit future policy
   allows a narrowly bounded exception.
3. **Single merge slot.** Coordinate so only one approved candidate is
   actively reconciling and qualifying for merge on a given target branch.
   Other agents may continue coding and opening PRs but must not
   independently merge into that branch during the slot. A social/operational
   slot is not an atomic GitHub lock.
4. **Revalidate against current target.** Read authoritative GitHub PR
   head/base, mergeability, required check identities/results and unresolved
   review conditions. Reconcile if branch protection requires it; a new
   head invalidates exact-head readiness evidence and is returned for review
   or bounded approval handling. Never reinterpret stale green checks as
   current approval.
5. **Human executes the merge.** The maintainer performs the protected merge.
   Only recorded, still-current required checks count. On mismatch, missing
   evidence, new findings, or unexpected target movement, stop or requeue;
   do not spin through unlimited refresh cycles.
6. **Verify the landing.** Confirm actual merged SHA and target state.
   For a release-producing consumer, also monitor the main-branch security,
   publisher and release-integrity checks. Main CI is not a substitute for
   missing pre-merge qualification.
7. **Release the slot.** Record outcome and move to the next approved PR.

Initial implementation should be a **runbook and dashboard/queue view**,
not an agent-issued merge command. A queue should present candidates and
decisions; it should not infer authorization from conversational shortcuts,
PR labels, or `AI review · Clear`.

## 4. Safety invariants for any later implementation

Any proposed automation must demonstrate these independently before gaining
merge capabilities:

- **Exact identity:** target repository/branch, PR number, head SHA and
  qualifying base/merge candidate identity are pinned to trusted GitHub data.
- **Authority separation:** implementation agent completion,
  deterministic readiness, human merge authorization, and merge execution
  remain distinct; the reviewer cannot mint authorization.
- **Staleness:** new commits, changed target, failed/expired checks,
  superseded approval, or incomplete review cause revalidation or refusal,
  never optimistic interpretation.
- **Concurrency:** one merge decision at a time per target, atomic
  compare-and-merge behavior and crash/retry idempotency. A locally held
  advisory lock does not guarantee GitHub-side exclusion.
- **No privileged PR-head execution:** any credentials capable of merging
  are isolated from untrusted PR code and from the advisory reviewer.
- **Protection retained:** merge execution cannot skip required GitHub
  checks, approval rules, security gates, or exact-head revalidation.
- **Auditability:** human authorization identity and scope, checked SHAs,
  check-run evidence, final merge SHA, refusals and retries remain inspectable.

**Current status:** design constraints only. AGENTS.md and §3.7 still require
the human to perform merges; neither this document nor a documentation PR
changes that rule.

## 5. What NOT to conflate with coordination

### Faster consumer CI

Component-aware smoke selection, fail-open change classification,
superseded-run early exit, cache scope isolation and build-once/verify/publish
are **platform-core** changes (or reusable consumer patterns later).
They reduce the cost per qualification and runner contention. They do not
provide a safe merge authority.

Do not move all affected Docker tests to a main-only post-merge workflow
merely to shorten PR gates: that can make `main` unqualified at merge time.
Any tiering requires an explicit risk-based dependency audit.

### Integration branch

An always-on `feature → integration → main` branch is **not the default**.
It introduces a second trunk, drift, promotion rules and another
potential collision point. Consider a temporary integration/release branch
only for an explicitly approved batched-soak workflow, with an owner,
entry/exit conditions and deletion criteria (consistent with AGENTS.md).

### GitHub-native queue

Prefer a native merge queue only if it is supported by the consumer repo's
current ownership, plan and protection configuration. Do not assume
availability; repo settings and branch protection must be checked by an
authorized maintainer. Auto-merge alone is not a merge queue and does not
eliminate every mandatory up-to-date revalidation.

## 6. Measurements and acceptance

Before building automation, instrument at least a sample of merged PRs:

| Measure | Why |
| --- | --- |
| Time from human authorization to merge (p50/p90) | User-facing coordination delay |
| Number of full CI attempts per merged PR | Multiplication from target-branch movement |
| Time queued vs actively running on Docker lane | Runner contention vs test cost |
| Forced branch refreshes and exact cause | Measure merge race directly |
| Flaky-test failures/reruns | Prevent unnecessary full attempts |
| Time from latest green required checks to merge | Operator and coordination delay |
| Main-branch release-verification outcome | Ensure throughput gains do not weaken releases |

**Proposed pilot success:** a reduction in forced refresh cycles and
approved-to-merged time, with no missing required checks, no merges without
explicit human authorization, and no release-integrity regressions.
A target such as 45 minutes is a hypothesis, **not** a demonstrated SLA.
Compare against a baseline before assigning a performance claim.

## 7. Phased decision

- **Now:** Document the split of responsibilities and run one human-operated
  single-merge-slot pilot. Keep the existing no-agent-merge policy intact.
- **In platform-core:** Continue component-aware qualification and
  superseded-run skipping as a separate, CI-specific workstream.
- **After evidence:** Decide whether a small read-only coordinator view
  is useful, and whether GitHub-native queue options are available.
- **Only if needed:** Propose a separate governance change and
  security-reviewed merge executor. That would be a new permission and
  authority boundary, not a minor extension of AI review.

**Open decisions:** Who owns the merge slot, how a human records a bounded
authorization, whether an external platform controller should host the
queue, and what existing GitHub protection settings permit. Resolve these
before code that can merge is proposed.
