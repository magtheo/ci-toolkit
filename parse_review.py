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

# ---- iteration-4 plumbing: strict verifier-result parsing (25b) ----------
# The pass-2 verification verdict object (design §2.2). Parsing is
# fail-closed in the same direction as the assessment parser: unusable
# verification must never confirm a blocker. The exception (not a
# verdict) is the contract — the caller (25c activation) converts a
# VerificationParseError into an INCONCLUSIVE review.

VERIFICATION_VERDICTS = ("confirmed", "refuted")
VERDICT_FIELDS = ("evidence_establishes", "applicable_requirement",
                  "contradiction", "unstated_assumption",
                  "correct_implementation_possible", "verdict")


class VerificationParseError(ValueError):
    """Verifier output is unusable — the review becomes INCONCLUSIVE."""


def extract_verdicts(content, expected_ids):
    """Verifier output text -> {candidate_id: verdict record}.

    Strict: every expected id exactly once; verdict in the enum; every
    reconstruction field present and typed (non-empty strings; bool
    for correct_implementation_possible). Anything else raises
    VerificationParseError — malformed verification is semantic
    failure (INCONCLUSIVE), never a silent keep.
    """
    obj = parse_model_output(content)
    verdicts = obj.get("verdicts") if obj else None
    if not isinstance(verdicts, dict):
        raise VerificationParseError("no verdicts object in verifier output")
    got = set(verdicts)
    want = set(expected_ids)
    if got != want:
        raise VerificationParseError(
            "candidate id mismatch: missing={0} extra={1}".format(
                sorted(want - got), sorted(got - want)))
    out = {}
    for cid in expected_ids:
        v = verdicts[cid]
        if not isinstance(v, dict):
            raise VerificationParseError(
                "verdict for {0} is not an object".format(cid))
        if set(v) != set(VERDICT_FIELDS):
            raise VerificationParseError(
                "verdict fields for {0}: missing={1} extra={2}".format(
                    cid,
                    sorted(set(VERDICT_FIELDS) - set(v)),
                    sorted(set(v) - set(VERDICT_FIELDS))))
        if v["verdict"] not in VERIFICATION_VERDICTS:
            raise VerificationParseError(
                "invalid verdict for {0}: {1!r}".format(cid, v["verdict"]))
        for field in VERDICT_FIELDS[:4]:
            if not isinstance(v[field], str) or not v[field].strip():
                raise VerificationParseError(
                    "field {0} for {1} must be a non-empty string".format(
                        field, cid))
        if not isinstance(v["correct_implementation_possible"], bool):
            raise VerificationParseError(
                "correct_implementation_possible for {0} must be "
                "boolean".format(cid))
        out[cid] = dict(v)
    return out


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
