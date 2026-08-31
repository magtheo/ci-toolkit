# ci-toolkit MATURITY ROADMAP — Platform Reliability & Operations

Authoritative direction for maturing ci-toolkit as a dependable internal
platform component.

This roadmap is intentionally separate from [ROADMAP.md](ROADMAP.md), which
tracks **reviewer capability / intelligence**. This file tracks the maturity of
the **toolkit itself**: release discipline, compatibility, deterministic CI,
consumer contracts, operational visibility, supply-chain posture, and fleet
management.

Last reviewed: 2026-08-31

## Scope boundary

Use the two roadmaps for different questions:

- **ROADMAP.md:** "What semantic review capability should the reviewer gain
  next, and what evidence proves it?"
- **MATURITY_ROADMAP.md:** "What engineering controls must ci-toolkit gain to
  remain dependable as more repositories rely on it?"

Do not duplicate work between them. Reviewer-evaluation machinery belongs in
ROADMAP.md unless the work is specifically about operating, releasing,
versioning, or consuming that machinery as a platform contract.

## Maturity principle

**Do not imitate enterprise tooling for appearance. Add maturity controls only
when they remove a demonstrated failure mode, protect a real contract, or are
cheap enough to be obvious hygiene.**

The anti-pattern is platform theatre: dashboards without a fleet, compatibility
machinery without an API, broad scanners without a concrete defect class, or
release ceremony that does not make upgrades safer.

The target is:

> A small toolkit whose behavior, trust boundaries, upgrades, and failures are
> understandable and mechanically constrained across every consuming repo.

## Current position (2026-08-31)

ci-toolkit has crossed from prototype into an engineered internal component:

- explicit trusted-base / untrusted-head boundary;
- advisory-only review effect (`COMMENT` by construction);
- fail-closed parsing and policy resolution;
- security invariants in tests;
- immutable SHA consumption for the privileged reviewer path;
- documented runner trust classes and credential transport;
- reviewer capability work moving toward measured qualification.

The main maturity gaps are now around the toolkit **as a platform** rather than
around basic reviewer safety:

1. `main` governance is documented but not yet enforced by repository rules;
2. no human-readable release/version layer exists above raw commit SHAs;
3. the public consumer interface is real but not yet declared as a versioned
   compatibility contract;
4. deterministic CI is smaller and less supply-chain-hardened than the
   privileged reviewer path;
5. integration/consumer contract testing is limited;
6. operational health across multiple consumers is not yet observable;
7. upgrade/fleet management is manual.

## Maturity stages

These stages are directional, not marketing labels. A stage is reached only
when its properties are true in practice.

| Stage | Meaning | Position |
|---|---|---|
| 0 | Script / experiment | passed |
| 1 | Reusable internal tool | passed |
| 2 | Engineered component with explicit trust boundaries | **current main** |
| 3 | Measured and governed platform component | next |
| 4 | Mature multi-repo internal platform | later |
| 5 | Broadly reusable/public product surface | only if actually needed |

---

# Stage 3 — Measured and governed platform component

**Goal:** turn existing engineering doctrine into mechanically enforced platform
contracts without expanding scope unnecessarily.

Stage 3 should be completed before investing in fleet dashboards, generalized
provider abstraction, or broad productization.

## 3.1 Repository governance becomes executable

### Evidence / gap

`AGENTS.md` requires reviewed PRs and deterministic validation before changes
reach `main`, but repository settings do not yet enforce that contract.

### Target

Protect `main` mechanically:

- PR required for changes;
- required deterministic CI checks;
- no force-push / branch deletion;
- review conversations resolved where useful;
- AI review remains advisory and is **not** a merge gate;
- qualification may become a required gate only for the specific change classes
  whose deployment contract actually depends on it.

### Acceptance

A direct or insufficiently validated change cannot reach `main` through the
normal GitHub path.

### Non-goal

Do not add heavyweight approval bureaucracy for a single-maintainer repository.
The point is enforcing invariants, not manufacturing process.

---

## 3.2 Deterministic CI baseline

### Evidence / gap

The security-sensitive reusable workflow pins critical actions and has dedicated
source invariants, while the general test workflow is still minimal and uses
floating major action tags.

### Target

Establish a deliberately small deterministic baseline:

- pin third-party GitHub Actions by full commit SHA;
- `pytest` remains the core suite;
- add `actionlint` for workflow syntax/semantic errors;
- add `shellcheck` where its signal is demonstrated useful for maintained shell;
- preserve explicit source-level security invariant tests;
- keep deterministic gates below the AI layer.

Every new deterministic tool must name the failure class it eliminates.

### Acceptance

The repository has one documented deterministic validation command/set that
covers Python tests, workflow validity, and maintained shell at an appropriate
level, and CI runs it consistently.

### Non-goal

No scanner collection, score-chasing, or dependency on tools whose findings are
mostly ignored.

---

## 3.3 Declare the consumer contract

### Evidence / gap

ci-toolkit already exposes a public interface (`workflow_call` inputs, secrets,
runtime requirements, rubric override, review semantics), but compatibility is
implicit.

### Target

Document **Consumer Contract v1** covering at minimum:

- reusable workflow inputs and defaults;
- required secrets and permissions;
- supported runner requirements / trust assumptions;
- repo-local policy override behavior;
- observable outcomes (`Clear`, `Issues found`, `Inconclusive`, no-review,
  infrastructure failure);
- pinning rules;
- which changes are breaking vs compatible.

Treat these surfaces as an API even though they are YAML/shell rather than an
HTTP library.

### Breaking-change examples

- renaming/removing a workflow input;
- changing required permissions;
- changing required runtime dependencies;
- changing rubric lookup semantics;
- changing output-state meaning;
- changing the trust model of the caller trigger.

### Acceptance

A maintainer reviewing a PR can determine whether the PR changes Consumer
Contract v1 and therefore requires release/migration handling.

---

## 3.4 Human-readable releases above immutable SHAs

### Evidence / gap

Raw SHA pinning provides machine immutability but poor human upgrade semantics.
There are currently no releases.

### Target

Introduce lightweight releases once the reviewer-evaluation/deployment contract
has landed and stabilized enough to name a baseline.

Recommended model:

```text
v0.x.y        human release identity
  └── SHA     immutable deployed identity
```

Consumers continue pinning full SHAs. Releases provide:

- version name;
- exact SHA;
- short change summary;
- compatibility impact;
- migration notes if needed;
- qualification status where relevant.

Use semantic-version-like intent pragmatically during `0.x`:

- patch: behavior-preserving/hardening/docs-compatible fixes;
- minor: backwards-compatible capability or interface additions;
- explicitly marked breaking release when Consumer Contract v1 changes
  incompatibly.

### Acceptance

A consumer upgrade can be discussed as "v0.3.0 -> v0.4.0" while still being
implemented by reviewed SHA pin replacement.

### Non-goal

Do not introduce packaging or artifact registries solely to have releases.

---

## 3.5 Consumer contract / integration tests

### Evidence / gap

Unit and source-invariant tests protect important components, but the real
product is the assembled consumer workflow across GitHub API, model boundary,
parser, renderer, and review posting.

### Target

Build a small integration harness around representative scenarios. Prefer mocked
or local protocol fixtures before expensive live tests.

Initial fixture candidates:

- ordinary textual PR;
- repo-local rubric from base revision;
- malformed model output -> Inconclusive;
- model says issues but evidence does not validate -> Inconclusive;
- invalid inline line -> body fallback;
- fork PR skip;
- binary / patch-less PR;
- changed-file and diff truncation;
- transient provider failure / retry exhaustion;
- pin mismatch or invalid toolkit ref;
- consumer using supported self-hosted runtime.

Tests should assert **observable contract behavior**, not internal implementation
shape unless the implementation shape is itself a security invariant.

### Acceptance

At least the critical Consumer Contract v1 paths can be exercised without a real
consumer repo and without spending model tokens.

---

## 3.6 Close known ambiguity around partial review

### Evidence / gap

A large PR may be truncated yet still receive `Clear`; the README correctly
scopes the claim, but this is operationally easy to misread.

### Target

Resolve the product contract for incomplete material. Candidate states include:

- deterministic `Partial` / `Inconclusive` when truncation prevents full review;
- a machine-visible coverage marker carried alongside the semantic assessment;
- explicit reviewed/omitted counts.

This decision belongs here because it changes the **consumer-visible reliability
contract**; semantic detection quality for the reviewed material remains in
ROADMAP.md.

### Acceptance

A consumer cannot reasonably interpret a truncated assessment as coverage of the
whole PR.

---

# Stage 4 — Mature multi-repo internal platform

**Entry condition:** Stage 3 contracts are stable and multiple active consumer
repos create enough operational surface to justify fleet-level machinery.

Do not start Stage 4 because the architecture looks attractive. Start individual
items when consumer count or incidents create evidence.

## 4.1 Fleet inventory and upgrade state

Maintain a machine-readable answer to:

- which repos consume ci-toolkit;
- which SHA/release each uses;
- which consumers are behind;
- which consumers have incompatible local overrides;
- which pins are qualified/current.

Prefer deriving this from repositories rather than maintaining a second manual
source of truth.

### Trigger

Manual pin tracking becomes error-prone across several active consumers.

---

## 4.2 Safe automated upgrade PRs

Automate discovery/proposal, not authority.

A future updater may:

1. detect a newer eligible release/SHA;
2. verify qualification / compatibility evidence;
3. open the consumer pin-bump PR;
4. run consumer deterministic checks and review;
5. leave merge to the normal human-controlled process.

### Trigger

Routine pin bumps consume meaningful repeated effort or consumers regularly
remain stale.

### Non-goal

No central bot silently changing production consumers.

---

## 4.3 Operational telemetry

### Goal

Answer whether the reviewer is healthy in real use, not merely whether its test
corpus passes.

Potential metrics:

- review count and success rate;
- Inconclusive rate;
- infrastructure/provider failure rate;
- latency distribution;
- truncation/partial-review frequency;
- model/profile + toolkit version distribution;
- cost per review / repo;
- blocking finding count;
- where feasible, human disposition of blocking findings (accepted vs rejected)
  as evidence for production false-blocker drift.

Keep privacy boundaries explicit: telemetry should prefer counts/metadata, not
central copies of consumer source or prompts.

### Trigger

Enough reviews occur that regressions could be systematic rather than obvious
from individual PRs.

---

## 4.4 Production drift / health detection

Evaluation qualification measures known fixture behavior. Production monitoring
must catch different failure modes:

- provider/model behavior changes;
- rising Inconclusive/error rate;
- latency/cost regressions;
- new false-blocker patterns;
- a consumer contract behaving differently on one runner class.

Any alert must correspond to an actionable response; avoid vanity alarms.

### Trigger

Operational telemetry exists and has enough baseline history to define useful
bounds.

---

## 4.5 Compatibility matrix where reality requires it

Possible dimensions:

- GitHub-hosted vs supported self-hosted runner classes;
- Python/runtime versions;
- multiple model profiles;
- optional provider implementations;
- Consumer Contract versions.

### Trigger

A second genuinely supported variant exists. Never create a compatibility matrix
for hypothetical configurations.

---

## 4.6 Supply-chain automation

Once the dependency/action surface is large enough to justify it:

- automated pinned-action update PRs;
- provenance/review evidence for dependency bumps;
- dependency inventory;
- vulnerability response policy proportional to actual dependencies.

### Trigger

Manual SHA maintenance becomes a recurring source of staleness or security risk.

---

# Stage 5 — Broadly reusable product surface (conditional)

This stage is **not a current objective**. It exists to stop Stage-3/4 design
from accidentally assuming every future consumer is one of Theo's repositories.

Only pursue it if ci-toolkit develops real external users or organizational
requirements.

Potential work then includes:

- stable documented public API/support policy;
- formal deprecation windows;
- multiple provider adapters;
- organization-level policy distribution;
- install/upgrade tooling;
- broader privacy/data-processing modes;
- support for different Git hosting / enterprise environments if demanded;
- formal security disclosure/release process.

Do not pre-build these abstractions.

---

# Cross-cutting maturity rules

## 1. Evidence before machinery

Every non-trivial maturity feature should cite one of:

- a concrete incident;
- a repeated manual burden;
- a real consumer requirement;
- a security/control gap;
- an accepted platform contract that lacks enforcement.

"Mature projects usually have this" is insufficient by itself.

## 2. Deterministic before probabilistic

Exact validation belongs in deterministic CI. The AI reviewer should never be
used to approximate a property that a stable parser, linter, schema validator,
or direct API check can prove.

## 3. Consumer-visible behavior is an API

Workflow inputs, permissions, output semantics, failure states, runtime
requirements, pin rules, and policy resolution are contract surfaces even when
implemented in shell/YAML.

## 4. Immutable deployment, readable releases

Human-readable versions do not replace SHA pinning. They explain and organize
immutable deployments.

## 5. Dogfood without circular trust

ci-toolkit should consume its own patterns where doing so tests the real
contract, but no self-check may become the sole evidence for its own correctness.

## 6. Prefer deletion and simplification

A maturity mechanism that stops providing signal should be removed. The goal is
not monotonically increasing process/tool count.

## 7. Separate reviewer intelligence from platform maturity

A reviewer miss belongs in ROADMAP.md and the evaluation loop. A deployment,
compatibility, release, CI, fleet, or operational failure belongs here. Some
incidents may create work in both roadmaps; record each consequence in the
appropriate place rather than merging the concerns.

---

# Near-term sequence

Unless new evidence changes priority, the recommended order is:

1. **Finish and activate the reviewer-eval/deployment baseline** already in
   progress; do not derail it with broad platform work.
2. **Repository protection + deterministic CI hygiene** (small, independent
   changes).
3. **Consumer Contract v1** documentation.
4. **First human-readable release** after the deployment/qualification contract
   is stable enough to name.
5. **Consumer integration harness**, built from the highest-value real failure
   modes already observed.
6. **Resolve partial/truncated review semantics.**
7. Move into Stage 4 items only as consumer count and operational evidence earn
   them.

This ordering deliberately postpones dashboards, generalized orchestration,
multi-provider abstraction, and fleet automation until there is enough real
surface area for them to pay for their complexity.
