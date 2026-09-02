# ci-toolkit

**ci-toolkit** contains shared CI/review logic and governance templates
for magtheo's repositories, starting with an **advisory AI pull-request
reviewer**.

ci-toolkit **stores no consumer credentials and no application
source**. At runtime the caller explicitly supplies an OpenRouter API
key and GitHub supplies a scoped `GITHUB_TOKEN`. The reviewer fetches
PR metadata and textual diffs through the GitHub API, sends review
context to the configured model provider, and posts a `COMMENT`
review. **The consumer repository's PR head is never checked out or
executed.**

**Important:** "not checked out, not executed" does not mean "not
processed externally" — PR diff content is provided to the model API
for review. See [Data flow](#data-flow-and-external-processing).

## AI reviewer at a glance

Reusable workflow: [`.github/workflows/ai-review.yml`](.github/workflows/ai-review.yml)

- advisory only — the current payload builder hard-codes the GitHub
  review event to `COMMENT`; neither the model nor any workflow input
  can request `APPROVE` or `REQUEST_CHANGES`;
- `GITHUB_TOKEN` scoped `pull-requests: write` + `contents: read`;
- the PR diff is fetched as **data** through the GitHub API — the PR
  head is never checked out or executed;
- fork PRs are explicitly skipped before the reviewer is invoked (with
  `pull_request_target` this guard is security-critical — see
  [Integration](#integration-3-steps)).

## Data flow and external processing

What leaves your repository when the reviewer runs:

```text
GitHub PR
   ├── PR title + body (metadata)
   ├── changed filenames
   ├── textual patches (the diff)
   └── base-revision rubric (bundled, or your .ai-review-rubric.md)
          │
          ▼
   ci-toolkit reviewer (API fetch; PR head never checked out)
          │
          ▼
      OpenRouter  ← authenticated with the caller's LLM_API_KEY
          │
          ▼
      model output
          │
          ▼
   deterministic parser (parse_review.py)
          │
          ▼
   GitHub COMMENT review  ← authenticated with GITHUB_TOKEN
```

Explicitly:

- PR text and diff content **are sent to the configured model
  provider** (OpenRouter and whichever model it routes to);
- `LLM_API_KEY` authenticates to OpenRouter; `GITHUB_TOKEN`
  authenticates to GitHub;
- neither credential is intentionally included in the model prompt or
  the posted review;
- repositories whose source must not be transmitted to an external
  model provider should not enable this reviewer without an
  acceptable provider/data-processing arrangement.

## Security guarantees

- **No PR-head execution.** The PR head is never checked out,
  downloaded as a git object, or executed. Only API metadata and diff
  text are fetched, via `jq`-safe data channels.
- **Approvals impossible via this path.** The review event is the
  literal string `COMMENT` in `parse_review.py` — not derived from
  model output, inputs, or environment.
- **Explicit secret mapping.** Callers map `LLM_API_KEY` explicitly
  (never `secrets: inherit`); the reusable workflow's `permissions`
  cannot be elevated through a `uses:` chain.
- **Fork guard.** Fork PRs are skipped before anything runs.
- **Credentials never in process argv** (since the
  credential-transport fix): Authorization headers reach curl via
  private files (`-H @file`). Consumers pinned to older commits retain
  argv transport — hosted runners make that defense-in-depth;
  self-hosted lanes should pin past the fix.

## Threat boundaries (what is NOT guaranteed)

- **Prompt injection is mitigated, not impossible.** PR-derived text
  is never shell-evaluated or executed (a deterministic guarantee).
  In the model prompt the diff is explicitly delimited as untrusted
  data and the model is instructed not to follow directives inside
  it — but an LLM can still be influenced by adversarial text. Treat
  reviewer output as evidence, never as instruction.
- **The model sees your diff.** External processing is the product;
  privacy-segmented code needs a different arrangement.
- **Advisory only.** The reviewer has no merge authority; humans
  decide (see AGENTS.md's Review Model).

## Integration (3 steps)

1. Set an `LLM_API_KEY` secret (OpenRouter key) in your repo.
2. Add a caller workflow. Security posture: trigger with
   `pull_request_target` so the secret-receiving workflow file always
   comes from your trusted default branch (a PR cannot rewrite its own
   reviewer); the `permissions` block is required; secrets are mapped
   EXPLICITLY (never `inherit`); the reusable-workflow ref and
   `toolkit_ref` are both pinned to the same full commit SHA
   (`toolkit_ref` is required — no floating default):

   ```yaml
   # .github/workflows/ai-review.yml
   on:
     pull_request_target:
   permissions:
     pull-requests: write
     contents: read
   jobs:
     ai-review:
       if: ${{ !github.event.pull_request.head.repo.fork }}
       uses: magtheo/ci-toolkit/.github/workflows/ai-review.yml@<full-ci-toolkit-sha>
       with:
         toolkit_ref: <full-ci-toolkit-sha>
       secrets:
         LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
   ```

   The example above is the safe default: **review everything** —
   the reviewer is advisory and cheap relative to what it catches.
   If cost/noise genuinely demands skipping, that is an optional
   optimization (NOT a security control), added deliberately:

   ```yaml
   # Optional cost/noise optimization — a deliberate choice, not a
   # default:
   #   paths-ignore:
   #     - "docs/**"
   #     - "plans/**"
   ```

   Do NOT blanket-ignore `**.md`: `.ai-review-rubric.md` is trusted
   policy, and `AGENTS.md` / security docs / governance templates can
   carry meaningful trust-model changes. If you do skip `docs/**` or
   `plans/**`, policy files living there lose AI review.

   Why **this** `pull_request_target` usage is safe (the event itself
   never is): the reviewer never checks out or executes PR-head code —
   it fetches the diff as data via the GitHub API and takes policy
   from the base revision. Add any step that runs or checks out
   untrusted PR content and you have the classic
   `pull_request_target` exfiltration footgun.

   Fork PRs are skipped (no AI review): with `pull_request_target`
   the token could act on forks, so the guard is load-bearing.

   To upgrade the reviewer later: pick the reviewed ci-toolkit commit,
   replace the SHA in both places, merge — the upgrade PR itself was
   reviewed by the previously pinned version first. See
   [Pin governance](#pin-governance-incident-2026-08-31--evidence-based).

3. Optional overrides: `with: runner: <label>` (single runner label
   string — there is no automatic fallback; see
   [Self-hosted runners](#self-hosted-runner-requirements)),
   `with: model: <openrouter-id>` (thin exposure of the default
   model; no routing or fallback logic), and a repo-local
   `.ai-review-rubric.md` to replace the bundled rubric (resolved
   from the PR **base** ref — it is trusted policy, so it must come
   from reviewed code, never from the branch under review).

   `toolkit_ref` is **not** optional: it is mandatory and must be the
   same full SHA used in `uses:`.

### Pin governance (incident 2026-08-31 — evidence-based)

Observed, same day, for the pinned merge commit `c328fee8` after
branch deletions removed its reachability:

- in-job `actions/checkout` at the SHA failed on a self-hosted lane
  container with `upload-pack: not our ref` (three runs, 08:14–08:20Z);
- local `git fetch origin <sha>` refused consistently from clean
  clones, before and after republishing the commit via
  `archive/pin-c328fee8` / `pins/c328fee8` ref tips;
- a hosted `pull_request_target` ai-review run checked out the SAME
  SHA successfully at 09:20Z (run 33377170635) — the production
  consumption path worked.

Conclusion: SHA-want fetchability for that commit was **divergent
across contexts**; the exact server semantics are UNCONFIRMED, and
this incident alone does not establish them. Rules that hold
regardless:

- anchor long-lived pins with explicit refs (`pins/<sha>` archive
  branches) so reachability never depends on PR branch lifecycles;
- verify a pin's health via a clean clone AND the actual consumer
  path — a single vantage (including local fetch) is not
  authoritative;
- if a pin misbehaves in any context, roll forward to a maintained
  non-merge descendant — precedent `3003cb9` (direct child, only
  delta the toolkit's own dogfood pin text; reviewer
  byte-identical);
- do not generalize GitHub object-serving semantics from one
  incident; if it recurs, capture both failing and succeeding runs
  and escalate to GitHub support.

## Self-hosted runner requirements

If you override `runner`, the reviewer's runtime becomes your
interface. The reviewer needs at least:

- `bash`, `curl`, `jq`, `python3`, `git`
  (`actions/checkout` tooling), plus the GitHub Actions runner's own
  runtime dependencies.

**Trust class:** the review job is a privileged
`pull_request_target` workflow carrying your `LLM_API_KEY`. It must
NOT share persistent runners with PR-controlled test code — state
planted by a test job (toolcache, PATH, dotfiles) would be inherited
by the privileged job. Route it to an isolated, preferably ephemeral
lane; reference implementation: student-platform
`infra/ai-review-lane/` and runbook `self-hosted-runner-setup.md`
Part 9 (one disposable container per job, hostile-user acceptance
tests that scan `/proc` for both credentials). Pin past the
credential-transport fix so Authorization headers never appear in
curl argv.

## Review output semantics

The reviewer produces an **assessment** — evidence, never authority:

- **AI review · Clear** — the review completed and found no blocking
  issues **in the material it reviewed** (see
  [Limitations](#limitations)). Not an approval, not merge-readiness.
- **AI review · Issues found** — one or more validated blocking
  findings, plus any advisory findings, attention-weighted
  (blocking first).
- **AI review · Inconclusive** — no usable assessment; do not treat
  it as clear.

Deterministic classification (the parser, never the model):

1. structurally invalid output (missing/malformed findings, invalid
   severity, unknown assessment) → **Inconclusive**;
2. ≥1 validated blocking finding → **Issues found**;
3. the model labels its output `ISSUES_FOUND` but no validated
   blocking finding survives → **Inconclusive** (never Clear — the
   model's label is a consistency field, not a decision);
4. otherwise → **Clear** (advisory findings are compatible with
   Clear);
5. parser failure can never yield Clear.

Infrastructure failures (network, API) surface as a **red failed
job** — never a fabricated assessment. Details, praise, and metadata
(model, commit, assessment) sit behind `<details>` progressive
disclosure.

## Limitations

- **Clear is scoped to what was reviewed.** Large PRs are truncated:
  the changed-file list caps at `AI_REVIEW_MAX_FILES` (default 200)
  and the diff at `AI_REVIEW_MAX_DIFF` (default 120000 characters);
  the model is told about the truncation, but the assessment can
  still be Clear. A Clear on a huge PR is not a claim about the parts
  that didn't fit. (Open product question, recorded in ROADMAP.md:
  make truncation visibly degrade the assessment toward
  Inconclusive/Partial.)
- **Binary and patch-less files are not semantically reviewed.**
  Files with no textual patch are omitted from the diff; binary-only
  PRs produce no review.
- **Path-filtered PRs produce no AI review at all** (caller
  `paths-ignore`) — skipping is invisible by design.
- **Infrastructure failure yields a red job**, not an assessment.

## Roadmap freshness guard

Anti-rot guard for a repo's `ROADMAP.md` (or `plans/ROADMAP.md`):
the direction document must be re-reviewed at least every 28 days
WHENEVER the repo is being worked on. Shipped as
`templates/roadmap-freshness.sh` (unit-tested; the behavioral
contract) plus `templates/roadmap-freshness.yml` (weekly cron).
ci-toolkit dogfoods it on its own root `ROADMAP.md`.

### What happens when

| condition | result |
|---|---|
| `Last reviewed:` < 28 days old | green, silent (every Monday 10:37 UTC + manual dispatch) |
| >= 28 days old, no commits after the review date | green, silent — an untouched repo is not rotting |
| >= 28 days old, commits landed after it | **run fails** — work happened, the roadmap didn't follow |

Never a rolling window: any commit newer than the review date counts
once the review goes stale, no matter how old that commit is.

### Remedy for a red run

Open a PR that actually re-reads the roadmap, updates it where
direction changed, and bumps `Last reviewed:` to the review date
(same-day commits count as reviewed). Clears on the next scheduled
run or a manual `workflow_dispatch`.

### Installing in a consumer repo

Copy BOTH `templates/roadmap-freshness.yml` (to
`.github/workflows/`) and `templates/roadmap-freshness.sh` (e.g. to
`.github/scripts/`, adjusting the path), or run the script from the
pinned toolkit ref. Ensure the roadmap carries a parseable
`Last reviewed: YYYY-MM-DD` line — the guard fails closed on a
missing or malformed date.

## Governance templates

`templates/` holds copy-templates for the repo-governance practice
(branch model, phase discipline, Review Model, agent rules, plans,
PR template, roadmap + freshness guard). **Copy into your repo and
adapt — never reference governance across repos.** Source of truth is
student-platform's lived-in AGENTS.md; the template generalizes it and
adds the lifecycle invariants (branch from verified `main`, never from
an unmerged PR head; no phase PRs into a feature branch whose parent
has landed).

## Hardening and validation history

- rubric override resolves from the base sha (policy/data boundary);
- direct API calls have connect/request timeouts; the OpenRouter call
  retries network errors, 429, and selected transient 5xx responses
  (500/502/503/504) with backoff; explicit error reporting with HTTP
  codes;
- changed-file list capped (`AI_REVIEW_MAX_FILES`, default 200);
- payload construction extracted with an invariant test suite
  (`tests/`, run by `.github/workflows/tests.yml`): COMMENT-only
  event, diff-addressable inline lines, malformed-output
  degradation. Since the engine-boundary extraction
  (reviewer-eval-baseline Phase 1) the pipeline is
  `review.sh` (thin GitHub transport) → `engine.py`
  (ReviewInput v1 → prompt/model call/normalization → ReviewResult
  v1, shared with the eval harness) → `render.py` (GitHub renderer);
  `parse_review.py` is the deterministic normalization stage.
- credentials transported via private header files, never curl argv
  (source-invariant tested) — in BOTH transports: `review.sh`
  (GitHub token) and `engine.py` (OpenRouter key).

Origin: student-platform feature `ai-pr-review` (plan + validation
history live there). Later hardening rounds are documented in
`plans/reviewer-eval-baseline.md`, `ROADMAP.md` (evidence appendix),
and this repo's PR history.

## Qualification & pin promotion (deployment contract)

**Status: PENDING ACTIVATION** — the contract becomes ACTIVE only after the live post-merge demonstrations (first qualification on main, forced-red, old-subject requalification, dogfood pin-bump verification) pass; until then the review-only pin procedure governs.

Merging to `main` is not deployment. A reviewer version is deployed
only when a consumer pin references it, and pins may only be promoted
to SHAs with machine-verifiable qualification evidence:

```text
qualification run (trusted main x current oracle)
        ↓
record: records/by-subject/<sha>.json  (qualifications branch)
        ↓
consumer pin-bump PR → verify-qualification check (secretless)
        ↓
merge = deploy
```

- **Qualification** (`.github/workflows/qualify.yml`) runs the current
  oracle's corpus against a trusted merged subject (main-ancestry
  verified before any secret is mapped; the subject's engine+rubric,
  main's harness+corpus). Records land on the `qualifications` branch
  with a commit status on the subject.
- **Requalification**: any merged subject can be re-qualified against
  a newer oracle via workflow dispatch — no new toolkit commit needed.
- **Pair integrity is enforced by the machinery**: a positive fixture
  is promotion-eligible only if it passes AND its paired control
  passes (detection indistinguishable from over-triggering is not a
  capability).
- **Verification** (`.github/workflows/verify-qualification.yml`,
  reusable + secretless) checks subject match, PASS, current oracle,
  and model allowlist. Consumers wire it onto their pin-bump PRs (see
  this repo's `review.yml` `verify-pin` job for the pattern). A PR
  description citing qualification is documentation; the check is the
  control.
- Forced-red demonstrations exist for acceptance validation and are
  labeled `forced_red` in records — they can never authorize a
  promotion.
