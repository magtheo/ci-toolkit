#!/usr/bin/env bash
# Advisory AI PR review — ci-toolkit. Thin GitHub TRANSPORT.
#
# Pipeline (reviewer-eval-baseline Phase 1, engine boundary):
#   GitHub API -> ReviewInput v1 -> engine.py (prompt, model call,
#   normalization -> ReviewResult v1) -> render.py (GitHub payload)
#   -> POST one COMMENT review. The engine is shared with the eval
#   harness; this script owns ONLY fetch + post.
#
# Security model (plans/ai-pr-review.md, student-platform):
#   - the PR diff is fetched as DATA via the GitHub API; the PR head is
#     never checked out or executed;
#   - the review event is hard-coded to COMMENT in render.py —
#     approvals are impossible by construction and covered by tests;
#   - fork PRs are skipped: the pull_request_target caller is a
#     privileged trusted-base workflow carrying the secret, and
#     fork-authored diffs get no AI review (policy decision);
#   - the repo rubric override (.ai-review-rubric.md) resolves from the
#     PR BASE sha — it is trusted POLICY, so it must come from reviewed
#     code, not from the branch under review;
#   - OPENROUTER_API_KEY arrives from the caller's secrets at run time,
#     never stored in this repo;
#   - credentials reach curl via private header files (-H @file),
#     never argv — process command lines are observable by
#     co-located users on self-hosted runners. The GitHub token's
#     header file lives here; the OpenRouter key's header file is
#     created inside engine.py (same invariant);
#   - all PR-derived text stays data: it is passed through jq --arg /
#     temp files into JSON payloads, never through shell evaluation.

set -euo pipefail

: "${PR_NUMBER:?PR_NUMBER must be set}"
: "${TOKEN:?TOKEN must be set}"
: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY must be set}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY must be set}"

API="${GITHUB_API_URL:-https://api.github.com}"
MODEL="${AI_REVIEW_MODEL:-anthropic/claude-haiku-4.5}"
REPO_API="$API/repos/$GITHUB_REPOSITORY"
TOOLKIT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Credential transport: Authorization headers are passed to curl via
# private files (-H @file), never via argv — process command lines are
# observable by co-located users on self-hosted runners (the same
# /proc/<pid>/cmdline threat the ephemeral-lane design addresses).
# The OpenRouter header file is created inside engine.py, under the
# same invariant.
HDR_DIR="$(mktemp -d)"

# ONE cleanup for everything: a second `trap ... EXIT` would silently
# REPLACE this one (bash traps do not append) — add new artifacts to
# cleanup(), never a new trap. Unset-safe for early exits.
cleanup() {
    rm -rf "$HDR_DIR"
    rm -f "${files_jsonl:-}" review_input.json review_result.json \
          review.json
}
trap cleanup EXIT
( umask 077
  printf 'Authorization: Bearer %s' "$TOKEN" > "$HDR_DIR/gh" )

curl_gh() { curl -sS -f --connect-timeout 10 --max-time 60 \
  -H @"$HDR_DIR/gh" \
  -H "Accept: application/vnd.github+json" "$@"; }

pr=$(curl_gh "$REPO_API/pulls/$PR_NUMBER")

if [ "$(jq -r '.head.repo.fork // false' <<<"$pr")" = "true" ]; then
  echo "fork PR: no AI review (privileged trusted-base workflow; fork policy: skip)" \
    | tee -a "${GITHUB_STEP_SUMMARY:-/dev/null}"
  exit 0
fi

head_sha=$(jq -r .head.sha <<<"$pr")
base_sha=$(jq -r .base.sha <<<"$pr")
pr_title=$(jq -r .title <<<"$pr")

# ---- changed files, paginated, capped ------------------------------------
files_jsonl=$(mktemp)
page=1
while :; do
  batch=$(curl_gh "$REPO_API/pulls/$PR_NUMBER/files?per_page=100&page=$page")
  jq -c '.[]' <<<"$batch" >>"$files_jsonl"
  [ "$(jq 'length' <<<"$batch")" -lt 100 ] && break
  page=$((page + 1))
done

# Fast path on the FULL file set (strict superset of the engine's
# budgeted set, so it can never disagree with the engine's final
# skip decision): no file anywhere carries a patch -> skip now,
# before the rubric probe. The budget-aware decision (cap boundary:
# first N files patchless, N+1 textual) is the ENGINE's, signaled
# via exit 3 below.
if ! jq -se 'any(.[]; .patch != null)' "$files_jsonl" >/dev/null; then
  echo "no textual changes to review (docs/binary-only?)" \
    | tee -a "${GITHUB_STEP_SUMMARY:-/dev/null}"
  exit 0
fi

# ---- rubric: override from BASE (trusted policy), else bundled -----------
# Fail CLOSED: 200 -> repo policy from base; 404 -> genuinely absent,
# bundled fallback; anything else (network, 403, 429, 5xx) -> hard fail.
# A repo that declares policy must not be silently reviewed under a
# weaker rubric because of a transient GitHub error.
rubric=""
code=$(curl -sS --connect-timeout 10 --max-time 60 \
  -H @"$HDR_DIR/gh" \
  -H "Accept: application/vnd.github+json" -o /dev/null -w '%{http_code}' \
  "$REPO_API/contents/.ai-review-rubric.md?ref=$base_sha" || true)
case "$code" in
  200)
    rubric=$(curl_gh "$REPO_API/contents/.ai-review-rubric.md?ref=$base_sha" \
      | jq -r .content | base64 -d)
    ;;
  404)
    rubric=$(<"$TOOLKIT_DIR/rubric.md")
    ;;
  *)
    echo "FAIL CLOSED: rubric override probe returned http '$code'" \
      "(expected 200 or 404) — refusing to review under the bundled" \
      "rubric when repo policy may exist" >&2
    exit 1
    ;;
esac

# ---- ReviewInput v1 (data only; jq --arg keeps every byte as data) ---------
pr_body=$(jq -r '(.body // "")' <<<"$pr")

jq -s --arg title "$pr_title" --arg body "$pr_body" \
  --arg policy "$rubric" --arg model "$MODEL" \
  '{schema_version: 1,
    title: $title,
    body: $body,
    files: [.[] | {path: .filename, status: .status, patch: (.patch // null)}],
    policy: $policy,
    model: {id: $model, temperature: 0.2, max_tokens: 2000}}' \
  <"$files_jsonl" > review_input.json

# ---- engine: ReviewInput -> ReviewResult (prompt, model call, normalize) ---
# exit 3 = budgeted input has no textual changes (skip, old behavior)
set +e
python3 "$TOOLKIT_DIR/engine.py" review_input.json > review_result.json
engine_rc=$?
set -e
if [ "$engine_rc" -eq 3 ]; then
  echo "no textual changes to review (docs/binary-only?)" \
    | tee -a "${GITHUB_STEP_SUMMARY:-/dev/null}"
  exit 0
elif [ "$engine_rc" -ne 0 ]; then
  exit "$engine_rc"
fi

# ---- render: ReviewResult -> GitHub review payload -------------------------
python3 "$TOOLKIT_DIR/render.py" review_result.json "$files_jsonl" \
  "$head_sha" "$MODEL" > review.json

# ---- post exactly one COMMENT review -------------------------------------
posted=$(curl_gh -X POST "$REPO_API/pulls/$PR_NUMBER/reviews" \
  -H "Content-Type: application/json" -d @review.json)

{
  echo "### AI review posted"
  echo "- model: \`$MODEL\`"
  echo "- assessment: $(jq -r .body <<<"$posted" | head -1 | sed 's/^## AI review · //')"
  echo "- inline comments: $(jq '.comments | length' <<<"$posted")"
} | tee -a "${GITHUB_STEP_SUMMARY:-/dev/null}"
