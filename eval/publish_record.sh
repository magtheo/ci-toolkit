#!/usr/bin/env bash
# Publish a qualification record to the `qualifications` branch.
#
# Called by .github/workflows/qualify.yml after a run. Extracted into
# a script so the trickiest path — REQUALIFICATION (the by-subject
# record already exists on the branch) — is locally testable: records
# are copied into a WORKTREE of the qualifications branch, never into
# the oracle checkout, so an existing tracked by-subject record can
# never collide with an untracked copy (the classic
# "switch would overwrite untracked file" failure).
#
# usage: publish_record.sh <subject_sha> <record.json> <repo_dir>
set -euo pipefail

SUBJECT="${1:?subject sha required}"
RECORD="${2:?record path required}"
REPO_DIR="${3:?repo dir required}"
ORACLE_VERSION="$(cd "$REPO_DIR" && python3 eval/run_corpus.py --print-oracle-version)"

cd "$REPO_DIR"
git config user.name "qualification-bot" || true
git config user.email "noreply@users.noreply.github.com" || true

WORK="$(mktemp -d)"
trap 'git worktree remove --force "$WORK/wt" >/dev/null 2>&1 || true' EXIT

if git fetch origin qualifications 2>/dev/null \
   && git rev-parse --verify origin/qualifications >/dev/null 2>&1; then
  # detach at the REMOTE tip: a stale local qualifications branch in
  # this clone must never make a requalification land behind the tip
  git worktree add --detach "$WORK/wt" origin/qualifications
else
  # first record ever: bootstrap an empty orphan branch
  git worktree add --detach "$WORK/wt" HEAD
  git -C "$WORK/wt" switch --orphan qualifications
fi

mkdir -p "$WORK/wt/records/by-subject"
cp "$RECORD" "$WORK/wt/records/by-subject/$SUBJECT.json"
cp "$RECORD" "$WORK/wt/records/$SUBJECT-$ORACLE_VERSION.json"

git -C "$WORK/wt" add records
git -C "$WORK/wt" commit -m "qualification: $SUBJECT @ oracle $ORACLE_VERSION" || true
git -C "$WORK/wt" push origin HEAD:qualifications
echo "published records/by-subject/$SUBJECT.json @ oracle $ORACLE_VERSION"
