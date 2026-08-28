#!/usr/bin/env python3
"""Build the GitHub review payload from model output + diff data.

Extracted from review.sh so its invariants are unit-testable
(tests/):

- the review event is the literal "COMMENT" — never derived from
  model output, arguments, or environment (approvals impossible by
  construction);
- inline comments only attach to (file, line) pairs that exist in the
  diff hunks (new-side numbering); anything else degrades gracefully
  into the review body;
- malformed model output degrades to a safe NEEDS_CHANGES payload,
  never a crash and never a fabricated LGTM.

All inputs are DATA. Nothing in this module executes or evaluates PR
content.
"""

import json
import re
import sys

VALID_VERDICTS = ("LGTM", "NEEDS_CHANGES")


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


def _block(title, items):
    out = ["### " + title]
    if items:
        out += ["- `{file}` ({sev}): {comment}".format(**i) for i in items]
    else:
        out.append("- none")
    return "\n".join(out)


def build_payload(content, files, head_sha, model):
    """files: list of {"filename": str, "patch": str|None} dicts."""
    obj = parse_model_output(content)

    verdict = str(obj.get("verdict", "")).upper()
    if verdict not in VALID_VERDICTS:
        verdict = "NEEDS_CHANGES"
    summary = str(obj.get("summary", "")).strip()
    good = [str(g) for g in obj.get("good", []) if str(g).strip()]
    findings = obj.get("findings") or []
    if not isinstance(findings, list):
        findings = []

    valid = {f["filename"]: valid_lines_from_patch(f["patch"])
             for f in files if f.get("patch")}

    blocking, nonblocking, inline = [], [], []
    for fd in findings:
        if not isinstance(fd, dict):
            continue
        fname = str(fd.get("file", ""))
        comment = str(fd.get("comment", "")).strip()
        if not comment:
            continue
        sev = ("blocking"
               if str(fd.get("severity")) == "blocking" else "non-blocking")
        entry = {"sev": sev, "file": fname, "comment": comment}
        (blocking if sev == "blocking" else nonblocking).append(entry)
        sug = str(fd.get("suggestion", "")).strip()
        ln = fd.get("line")
        if fname in valid and isinstance(ln, int) and ln in valid[fname]:
            body = "**{0}**: {1}".format(sev, comment)
            if sug:
                body += "\n```suggestion\n" + sug + "\n```"
            inline.append({"path": fname, "line": ln, "body": body})
        elif sug:
            entry["comment"] += "\n```suggestion\n" + sug + "\n```"

    parts = [
        "**Verdict: {0}**".format(verdict),
        summary,
        _block("Blocking findings", blocking),
        _block("Non-blocking findings", nonblocking),
        _block("What looks good",
               [{"file": "-", "sev": "-", "comment": g} for g in good]),
        "_Advisory only — model `{0}` via ci-toolkit; humans decide "
        "merges._".format(model),
    ]
    body = "\n\n".join(p for p in parts if p)

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
