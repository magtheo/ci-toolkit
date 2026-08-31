# ci-toolkit

Shared CI patterns for magtheo's repos, starting with an **advisory AI
pull-request reviewer**. Logic only — no secrets, no project code.

## AI PR review

Reusable workflow: [`.github/workflows/ai-review.yml`](.github/workflows/ai-review.yml)

Safety model (from `plans/ai-pr-review.md` in student-platform):

- advisory only — posts a `COMMENT` review; approvals are impossible
  by construction (event type is hard-coded, never parameterized);
- `GITHUB_TOKEN` scoped `pull-requests: write` + `contents: read`;
- the PR diff is fetched as **data** through the GitHub API — the PR
  head is never checked out or executed;
- diff content is treated as untrusted input to the model, never as
  instructions;
- fork PRs are explicitly skipped before the reviewer is invoked; with
  `pull_request_target` this guard is security-critical (the
  trusted-base workflow carries the write-capable token and secrets —
  see the caller recipe below);
- no secrets live here; the caller's `LLM_API_KEY` (OpenRouter) is
  injected at run time.

### Integration (3 steps)

1. Set an `LLM_API_KEY` secret (OpenRouter key) in your repo.
2. Add a caller workflow. Security posture: trigger with
   `pull_request_target` so the secret-receiving workflow file always
   comes from your trusted default branch (a PR cannot rewrite its own
   reviewer); the `permissions` block is required (permissions cannot
   be elevated through a `uses:` chain); secrets are mapped
   EXPLICITLY (never `inherit`); the reusable-workflow ref and
   `toolkit_ref` are both pinned to the same full commit SHA
   (`toolkit_ref` is required — no floating default):

   ```yaml
   # .github/workflows/ai-review.yml
   on:
     pull_request_target:
       paths-ignore: ["**.md", "docs/**", "plans/**"]
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

   Why `pull_request_target` is safe HERE (and only here): the
   reviewer never checks out or executes PR-head code — it fetches the
   diff as data via the GitHub API and takes policy from the base
   revision. If you add any step that runs or checks out untrusted PR
   content into this workflow, you create the classic
   `pull_request_target` exfiltration footgun — don't.

   Fork PRs are skipped (no AI review): with `pull_request_target` the
   token could act on forks, so the guard is load-bearing.

   To upgrade the reviewer later: pick the reviewed ci-toolkit commit,
   replace the SHA in both places, merge — the upgrade PR itself was
   reviewed by the previously pinned version first.

3. Optional overrides: `with: runner: <label>` (explicit
   runner label — there is no automatic fallback), `with: model:
   <openrouter-id>` (thin exposure of the default model; no routing
   or fallback logic), and a repo-local `.ai-review-rubric.md` to
   replace the bundled rubric (resolved from the PR **base** ref —
   it is trusted policy, so it must come from reviewed code, never
   from the branch under review).

   `toolkit_ref` is **not** optional: it is mandatory and must be the
   same full SHA used in `uses:`.

   **Trust class when overriding `runner`:** the review job is a
   privileged `pull_request_target` workflow carrying your
   `LLM_API_KEY`. If you route it to self-hosted runners, it must
   NOT share persistent runners with PR-controlled test code (state
   planted by a test job — toolcache, PATH, dotfiles — would be
   inherited by the privileged job). Route it to an isolated,
   preferably ephemeral lane; reference implementation:
   student-platform `infra/ai-review-lane/` and runbook
   `self-hosted-runner-setup.md` Part 9 (one disposable container
   per job, hostile-user acceptance tests included).

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

## Governance templates

`templates/` holds copy-templates for the repo-governance practice
(branch model, phase discipline, Review Model, agent rules, plans,
PR template, roadmap + freshness guard). **Copy into your repo and
adapt — never reference governance across repos.** Source of truth is
student-platform's lived-in AGENTS.md; the template generalizes it and
adds the lifecycle invariants (branch from verified `main`, never from
an unmerged PR head; no phase PRs into a feature branch whose parent
has landed).

## Review output vocabulary

The reviewer produces an **assessment** — it has no authority and
makes no decisions (the GitHub event is always `COMMENT`):

- **AI review · Clear** — the review completed and found no blocking
  issues. Not an approval, not merge-readiness.
- **AI review · Issues found** — blocking and/or advisory findings,
  attention-weighted (blocking first).
- **AI review · Inconclusive** — the response was malformed or
  self-contradictory; do not treat it as clear. Infrastructure
  failures (network, API) surface as a red failed job instead — no
  fabricated assessment.

Deterministic consistency rules (the parser, never the model): the
user-facing assessment is classified from the validated findings —
any blocking finding → Issues found, otherwise Clear (advisories are
compatible with Clear); the model's label is a consistency field, not
a decision. Structurally invalid output (missing/malformed findings,
invalid severity, unknown assessment) is INCONCLUSIVE — bad output can
never become Clear. Parser failure can never yield Clear. Details,
praise, and metadata (model, commit, assessment) sit behind
`<details>` progressive disclosure.

## Hardening (external review round 1, 2026-08-28)

- rubric override resolves from the base sha (policy/data boundary);
- HTTP timeouts everywhere; OpenRouter retry with backoff on
  429/5xx; explicit error reporting with HTTP codes;
- changed-file list capped (`AI_REVIEW_MAX_FILES`, default 200);
- payload construction extracted to `parse_review.py` with an
  invariant test suite (`tests/`, run by `.github/workflows/tests.yml`):
  COMMENT-only event, diff-addressable inline lines, malformed-output
  degradation.

Origin: student-platform feature `ai-pr-review` (plan + validation
history live there).
