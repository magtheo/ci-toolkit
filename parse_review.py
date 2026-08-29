#!/usr/bin/env python3
"""Build the GitHub review payload from model output + diff data.

Semantic model (2026-08-28, interface-vocabulary redesign):

- the reviewer produces an ASSESSMENT — CLEAR, ISSUES_FOUND, or
  INCONCLUSIVE — never an approval or decision;
- the model may only return CLEAR or ISSUES_FOUND; INCONCLUSIVE is
  produced HERE, deterministically, when the response cannot be
  trusted (malformed, missing, or self-contradictory);
- deterministic consistency rules: CLEAR with a blocking finding
  normalizes to ISSUES_FOUND; ISSUES_FOUND with zero findings is
  INCONCLUSIVE (claims issues, provides none); parser failure can
  never result in CLEAR;
- user-facing language: Clear / Issues found / Inconclusive,
  Blocking / Advisory. No LGTM, no approval vocabulary;
- the review event is the literal "COMMENT" — never derived from
  model output, arguments, or environment (approvals impossible by
  construction);
- inline comments only attach to (file, line) pairs that exist in the
  diff hunks (new-side numbering); anything else degrades gracefully
  into the review body.

All inputs are DATA. Nothing in this module executes or evaluates PR
content.
"""

import json
import re
import sys

MODEL_ASSESSMENTS = ("CLEAR", "ISSUES_FOUND")
INCONCLUSIVE = "INCONCLUSIVE"


def valid_lines_from_patch(patch):
    """New-side line numbers addressable by review comments."""
    nums = set()
    new_ln = None
    for pl in patch.split("\n"):
        hm = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", pl)
        if hm:
            new_ln = int(hm.group(1))
        elif new_ln is not None:
            if pl.startswith("+"):
                nums.add(new_ln)
                new_ln += 1
            elif pl.startswith("-"):
                pass
            else:
                nums.add(new_ln)
                new_ln += 1
    return nums


def parse_model_output(content):
    """Extract the JSON object from model output; {} when absent/broken."""
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        return {}
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _usable_findings(obj):
    findings = obj.get("findings")
    if not isinstance(findings, list):
        return []
    return [f for f in findings
            if isinstance(f, dict) and str(f.get("comment", "")).strip()]


def assess(obj):
    """Deterministic assessment with consistency normalization.

    Returns (assessment, findings) where findings is [] for the
    INCONCLUSIVE path (untrusted output carries no usable evidence).
    """
    if not obj:
        return INCONCLUSIVE, []
    raw = str(obj.get("assessment", "")).upper()
    findings = _usable_findings(obj)
    has_blocking = any(str(f.get("severity")) == "blocking"
                       for f in findings)
    if raw not in MODEL_ASSESSMENTS:
        return INCONCLUSIVE, []
    if raw == "CLEAR":
        if has_blocking:
            # deterministic normalization: model says clear, evidence
            # says otherwise — trust the evidence
            return "ISSUES_FOUND", findings
        return "CLEAR", findings
    # ISSUES_FOUND
    if not findings:
        # claims issues but provides none: cannot fabricate findings,
        # cannot declare clear
        return INCONCLUSIVE, []
    return "ISSUES_FOUND", findings


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


def build_payload(content, files, head_sha, model):
    """files: list of {"filename": str, "patch": str|None} dicts."""
    obj = parse_model_output(content)
    assessment, findings = assess(obj)

    valid = {f["filename"]: valid_lines_from_patch(f["patch"])
             for f in files if f.get("patch")}

    if assessment == INCONCLUSIVE:
        body, _ = _build_inconclusive(model, head_sha)
        return {"commit_id": head_sha, "body": body,
                "event": "COMMENT", "comments": []}

    summary = str(obj.get("summary", "")).strip()
    good = [str(g) for g in obj.get("good", []) if str(g).strip()]

    blocking, advisory, inline = [], [], []
    for fd in findings:
        fname = str(fd.get("file", ""))
        comment = str(fd.get("comment", "")).strip()
        sev = ("blocking"
               if str(fd.get("severity")) == "blocking" else "non-blocking")
        entry = {"sev": sev, "file": fname, "comment": comment,
                 "line": fd.get("line")}
        (blocking if sev == "blocking" else advisory).append(entry)
        sug = str(fd.get("suggestion", "")).strip()
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
            "usage: parse_review.py CONTENT_FILE FILES_JSONL HEAD_SHA MODEL\n")
        return 2
    content_file, files_jsonl, head_sha, model = argv[1:5]
    with open(content_file) as fh:
        content = fh.read()
    files = []
    with open(files_jsonl) as fh:
        for line in fh:
            if line.strip():
                files.append(json.loads(line))
    print(json.dumps(build_payload(content, files, head_sha, model)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
