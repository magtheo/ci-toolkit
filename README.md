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

3. Optional overrides: `with: runner: [self-hosted, ci]` (explicit
   runner label — there is no automatic fallback) and a repo-local
   `.ai-review-rubric.md` to replace the bundled rubric (resolved from
   the PR **base** ref — it is trusted policy, so it must come from
   reviewed code, never from the branch under review).

   `toolkit_ref` is **not** optional: it is mandatory and must be the
   same full SHA used in `uses:`.

   Model override is not currently available (a plain caller `env`
   does not cross the reusable-workflow boundary — recorded as a
   follow-up: an explicit `model` workflow input).

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
