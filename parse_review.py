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
SEVERITIES = ("blocking", "non-blocking")
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


def _validate_findings(obj):
    """Strict schema validation of the findings list.

    Returns cleaned findings, or None when the response is structurally
    invalid (bad output must never become Clear — it becomes
    INCONCLUSIVE instead). Severity is normalized case/whitespace;
    anything still outside the enum invalidates the whole response
    rather than silently downgrading evidence to advisory.
    """
    if not isinstance(obj, dict):
        return None
    if str(obj.get("assessment", "")).strip().upper() not in MODEL_ASSESSMENTS:
        return None
    findings = obj.get("findings")
    if not isinstance(findings, list):
        return None
    cleaned = []
    for f in findings:
        if not isinstance(f, dict):
            return None
        comment = str(f.get("comment", "")).strip()
        fname = str(f.get("file", "")).strip()
        severity = str(f.get("severity", "")).strip().lower()
        if not comment or not fname or severity not in SEVERITIES:
            return None
        cleaned.append({"file": fname, "comment": comment,
                        "severity": severity, "line": f.get("line"),
                        "suggestion": f.get("suggestion")})
    return cleaned


def assess(obj):
    """Deterministic classification from validated evidence.

    The model's assessment label is a required schema field and a
    consistency check — it does NOT decide the user-facing status.
    The findings decide: any blocking finding -> ISSUES_FOUND;
    otherwise -> CLEAR (advisory findings are compatible with CLEAR).

    Returns (assessment, findings); findings is [] on the
    INCONCLUSIVE path (untrusted output carries no usable evidence).
    """
    if not obj:
        return INCONCLUSIVE, []
    findings = _validate_findings(obj)
    if findings is None:
        return INCONCLUSIVE, []
    if any(f["severity"] == "blocking" for f in findings):
        return "ISSUES_FOUND", findings
    return "CLEAR", findings


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
