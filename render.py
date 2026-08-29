#!/usr/bin/env python3
"""GitHub renderer — the presentation consumer of ReviewResult.

One of two consumers of the engine's ReviewResult (the other is the
future eval scorer). This module OWNS everything GitHub-specific:
- the review event (the literal "COMMENT" — never derived from model
  output; approvals are impossible by construction, source-tested);
- inline comment payloads (only on (file, line) pairs that exist in
  the diff hunks, new-side numbering; anything else degrades
  gracefully into the review body);
- Markdown rendering of the assessment bodies, progressive
  disclosure (<details>), and the metadata block.

It performs no semantic decisions: assessment/findings arrive already
normalized (parse_review.normalize / engine.run_review). Presentation
vocabulary: Clear / Issues found / Inconclusive, Blocking / Advisory.

All inputs are DATA. Nothing in this module executes or evaluates PR
content.
"""

import json
import sys

from parse_review import INCONCLUSIVE, valid_lines_from_patch


def _ref(entry):
    if entry.get("line"):
        return "`{0}:{1}`".format(entry["file"], entry["line"])
    return "`{0}`".format(entry["file"])


def _metadata_block(model, head_sha, assessment):
    return (
        "<details>\n<summary>Review metadata</summary>\n\n"
        "Reviewer: ci-toolkit\n"
        "Model: {0}\n"
        "Commit: {1}\n"
        "Assessment: {2}\n\n"
        "</details>"
    ).format(model, head_sha, assessment)


def _build_clear(summary, advisory, good, model, head_sha):
    n_adv = len(advisory)
    lines = [
        "## AI review · Clear",
        "",
        "No blocking issues found.",
        "",
        "0 blocking · {0} advisory".format(n_adv),
        "",
        "<details>",
        "<summary>Review details</summary>",
        "",
    ]
    if summary:
        lines += [summary, ""]
    if advisory:
        lines += ["### Advisory", ""]
        lines += ["- {0} — {1}".format(_ref(e), e["comment"])
                  for e in advisory]
        lines += [""]
    if good:
        lines += ["### Evidence-backed strengths", ""]
        lines += ["- {0}".format(g) for g in good]
        lines += [""]
    lines += ["</details>", "", _metadata_block(model, head_sha, "CLEAR")]
    return "\n".join(lines), []


def _build_issues(summary, blocking, advisory, good, model, head_sha):
    lines = [
        "## AI review · Issues found",
        "",
        "{0} blocking {1} · {2} advisory".format(
            len(blocking),
            "issue" if len(blocking) == 1 else "issues",
            len(advisory)),
        "",
    ]
    lines += ["### Blocking", ""]
    lines += ["- {0} — {1}".format(_ref(e), e["comment"])
              for e in blocking] or ["- none"]
    lines += [""]
    if advisory:
        lines += ["### Advisory", ""]
        lines += ["- {0} — {1}".format(_ref(e), e["comment"])
                  for e in advisory]
        lines += [""]
    lines += ["<details>", "<summary>Review details</summary>", ""]
    if summary:
        lines += [summary, ""]
    if good:
        lines += ["### Evidence-backed strengths", ""]
        lines += ["- {0}".format(g) for g in good]
        lines += [""]
    lines += ["</details>", "",
              _metadata_block(model, head_sha, "ISSUES_FOUND")]
    return "\n".join(lines), blocking, advisory


def _build_inconclusive(model, head_sha):
    body = "\n".join([
        "## AI review · Inconclusive",
        "",
        "A reliable semantic review could not be produced.",
        "",
        "Do not treat this review as clear.",
        "",
        "<details>",
        "<summary>Technical details</summary>",
        "",
        "Reason: reviewer response was malformed, incomplete, or "
        "self-contradictory (assessment missing/unknown, or issues "
        "claimed without evidence).",
        "",
        "</details>",
        "",
        _metadata_block(model, head_sha, INCONCLUSIVE),
    ])
    return body, []


def build_payload(review_result, files, head_sha, model):
    """ReviewResult (schema v1) + diff file list -> GitHub review payload.

    review_result: dict from parse_review.normalize / engine.run_review
    (assessment, findings, summary, good; schema_version ignored here —
    the engine enforces the contract).
    files: list of {"filename": str, "patch": str|None} dicts.
    """
    assessment = review_result["assessment"]
    findings = review_result.get("findings", [])
    summary = review_result.get("summary", "")
    good = review_result.get("good", [])

    valid = {f["filename"]: valid_lines_from_patch(f["patch"])
             for f in files if f.get("patch")}

    if assessment == INCONCLUSIVE:
        body, _ = _build_inconclusive(model, head_sha)
        return {"commit_id": head_sha, "body": body,
                "event": "COMMENT", "comments": []}

    blocking, advisory, inline = [], [], []
    for fd in findings:
        fname, comment = fd["file"], fd["comment"]
        sev = fd["severity"]
        entry = {"sev": sev, "file": fname, "comment": comment,
                 "line": fd.get("line")}
        (blocking if sev == "blocking" else advisory).append(entry)
        sug = str(fd.get("suggestion") or "").strip()
        ln = fd.get("line")
        if fname in valid and isinstance(ln, int) and ln in valid[fname]:
            body = "**{0}**: {1}".format(
                "Blocking" if sev == "blocking" else "Advisory", comment)
            if sug:
                body += "\n```suggestion\n" + sug + "\n```"
            inline.append({"path": fname, "line": ln, "body": body})
        elif sug:
            entry["comment"] += "\n```suggestion\n" + sug + "\n```"

    if assessment == "CLEAR":
        body, _ = _build_clear(summary, advisory, good, model, head_sha)
    else:
        body, _, _ = _build_issues(
            summary, blocking, advisory, good, model, head_sha)

    return {"commit_id": head_sha, "body": body,
            "event": "COMMENT", "comments": inline}


def main(argv):
    if len(argv) != 5:
        sys.stderr.write(
            "usage: render.py RESULT_FILE FILES_JSONL HEAD_SHA MODEL\n")
        return 2
    result_file, files_jsonl, head_sha, model = argv[1:5]
    with open(result_file) as fh:
        review_result = json.load(fh)
    files = []
    with open(files_jsonl) as fh:
        for line in fh:
            if line.strip():
                files.append(json.loads(line))
    print(json.dumps(build_payload(review_result, files, head_sha, model)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
