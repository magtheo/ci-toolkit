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
- fork PRs are skipped silently (their workflow runs token-read-only);
- no secrets live here; the caller's `LLM_API_KEY` (OpenRouter) is
  injected at run time.

### Integration (3 steps)

1. Set an `LLM_API_KEY` secret (OpenRouter key) in your repo.
2. Add a caller workflow:

   ```yaml
   # .github/workflows/ai-review.yml
   on:
     pull_request:
       paths-ignore: ["**.md"]
   jobs:
     ai-review:
       if: ${{ !github.event.pull_request.head.repo.fork }}
       uses: magtheo/ci-toolkit/.github/workflows/ai-review.yml@main
       secrets: inherit
   ```

3. Optional overrides: `with: runner: [self-hosted, ci]` (explicit
   runner label — there is no automatic fallback), `with:
   toolkit_ref: <sha>` to pin; repo-local `.ai-review-rubric.md` to
   replace the bundled rubric; `AI_REVIEW_MODEL` env in the caller for
   a cheaper model.

Origin: student-platform feature `ai-pr-review` (plan + validation
history live there).
