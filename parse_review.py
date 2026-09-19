#!/usr/bin/env python3
"""Semantic normalization of reviewer model output (engine stage).

Semantic model (2026-08-28, interface-vocabulary redesign; engine
boundary extraction 2026-08-29, reviewer-eval-baseline Phase 1):

- the reviewer produces an ASSESSMENT — CLEAR, ISSUES_FOUND, or
  INCONCLUSIVE — never an approval or decision;
- the model may only return CLEAR or ISSUES_FOUND; INCONCLUSIVE is
  produced HERE, deterministically, when the response cannot be
  trusted (malformed, missing, or self-contradictory);
- deterministic consistency rules are ASYMMETRIC and fail-closed:
  blocking evidence overrides an optimistic label (CLEAR + blocking
  finding -> ISSUES_FOUND), but a contradictory ISSUES_FOUND label
  with no validated blocking finding is INCONCLUSIVE — never Clear;
  parser failure can never result in CLEAR;
- user-facing language: Clear / Issues found / Inconclusive,
  Blocking / Advisory. No LGTM, no approval vocabulary.

This module is transport-free: it knows nothing about GitHub, HTTP
posting, or presentation. Rendering lives in render.py; the model
call and prompt construction live in engine.py.

All inputs are DATA. Nothing in this module executes or evaluates PR
content.
"""

import json
import re

MODEL_ASSESSMENTS = ("CLEAR", "ISSUES_FOUND")
SEVERITIES = ("blocking", "non-blocking")
INCONCLUSIVE = "INCONCLUSIVE"

RESULT_SCHEMA_VERSION = 1


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
    """Asymmetric, fail-closed classification from validated evidence.

    - concrete blocking evidence overrides an optimistic label
      (CLEAR + blocking -> ISSUES_FOUND);
    - but contradictory negative intent never normalizes downward:
      an ISSUES_FOUND label with no validated blocking finding is
      INCONCLUSIVE (the model reports issues that did not survive
      validation — possibly truncation or schema failure — and that
      must never become the strongest positive state);
    - advisory findings are compatible with CLEAR.

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
    if str(obj.get("assessment", "")).strip().upper() == "ISSUES_FOUND":
        return INCONCLUSIVE, []
    return "CLEAR", findings


def normalize(content):
    """Model output text -> ReviewResult fragment (schema v1).

    The deterministic normalization stage of the engine: parse,
    validate, classify. Untrusted (INCONCLUSIVE) output carries no
    summary, strengths, or findings. The engine (engine.py) adds
    usage/raw_output; render.py consumes the full ReviewResult.
    """
    obj = parse_model_output(content)
    assessment, findings = assess(obj)
    if assessment == INCONCLUSIVE:
        summary, good = "", []
    else:
        summary = str(obj.get("summary", "")).strip()
        good = [str(g) for g in obj.get("good", []) if str(g).strip()]
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "assessment": assessment,
        "findings": findings,
        "summary": summary,
        "good": good,
    }
