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
V2_SCHEMA_VERSION = 2

# ReviewResult v2 — structured blocking-evidence boundary (Phase 10).
# The model may attach an evidence object to any finding; BLOCKING
# severity is permission-gated by a deterministic parser-side check.
# Two information classes are deliberately separated:
#
#   MECHANICALLY VERIFIED — the parser checks these itself against
#   the diff: cited file exists, quote occurs in that file's patch
#   (normalized), cited line (if present) falls in a changed hunk.
#
#   MODEL-DECLARED SEMANTIC CLASSIFICATION — kind and harm are the
#   model's claims, NOT authoritative facts. The gate refuses
#   out_of_diff_assumption and non-demonstrated harm as a matter of
#   policy, but a lying declaration that passes the mechanical checks
#   is caught only by the honesty audit protocol (see
#   eval/evidence/honesty-audit-protocol-2026-09-21/), never here.
EVIDENCE_KINDS = ("in_diff_behavior", "in_diff_contract_contradiction",
                  "external_fact", "out_of_diff_assumption")
EVIDENCE_HARM = ("demonstrated", "presumed")
MACHINE_DOWNGRADE_REASON = "BLOCKING_EVIDENCE_INSUFFICIENT"

_WORD_RE = re.compile(r"[^a-z0-9{}\"=_\-./:\s]")
_ARTICLE_RE = re.compile(r"\b(a|an|the|this|these|those)\b")


def normalize_quote_text(text):
    """Phase-08 quote normalization: lowercase, unify apostrophes,
    drop stand-alone articles/demonstratives, collapse whitespace,
    preserve code-shaped characters. MUST stay byte-for-byte
    semantically identical to eval.run_corpus._norm_needle_text
    (parity is enforced by test)."""
    t = (text or "").lower().replace("'", "").replace("\u2019", "")
    t = _ARTICLE_RE.sub(" ", t)
    t = _WORD_RE.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()


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


# ---- ReviewResult v2: structured blocking-evidence boundary ----------

def _validate_evidence(raw):
    """Shape-check an evidence object. Returns (evidence, ok):
    (None, True) when absent; (dict, True) when well-formed;
    (None, False) when malformed (wrong type, unknown enum value)."""
    if raw is None:
        return None, True
    if not isinstance(raw, dict):
        return None, False
    kind = str(raw.get("kind", "")).strip()
    harm = str(raw.get("harm", "")).strip()
    quote = raw.get("quote")
    if kind not in EVIDENCE_KINDS or harm not in EVIDENCE_HARM:
        return None, False
    if quote is not None and not isinstance(quote, str):
        return None, False
    return {"kind": kind, "harm": harm,
            "quote": (quote or "").strip()}, True


def _evidence_checks(finding, diff_files):
    """Mechanical checks for one finding. Returns (audit, failed):
    audit records every check with mechanical=True/declared marking;
    failed is the list of failed check names (empty = permitted)."""
    cited = str(finding.get("file", "")).strip()
    line = finding.get("line")
    ev = finding.get("evidence") or {}
    quote = (ev.get("quote") or "").strip()
    audit, failed = [], []
    patch = diff_files.get(cited) if diff_files else None

    # 1. cited file exists in the diff (mechanical)
    file_ok = patch is not None
    audit.append({"check": "file_in_diff", "passed": file_ok,
                  "class": "mechanical"})
    if not file_ok:
        failed.append("file_in_diff")

    # 2. quote occurs in the cited patch (mechanical)
    if quote:
        norm_q = normalize_quote_text(quote)
        norm_p = normalize_quote_text(_patch_content(patch))
        quote_ok = bool(norm_q) and norm_q in norm_p
        audit.append({"check": "quote_in_patch", "passed": quote_ok,
                      "class": "mechanical", "quote": quote})
        if not quote_ok:
            failed.append("quote_in_patch")
    else:
        audit.append({"check": "quote_in_patch", "passed": False,
                      "class": "mechanical", "quote": None})
        failed.append("quote_in_patch")

    # 3. cited line falls in a changed hunk (mechanical; n/a when the
    # finding legitimately spans the whole change and omits line)
    if line is not None:
        try:
            line_ok = int(line) in valid_lines_from_patch(patch or "")
        except (TypeError, ValueError):
            line_ok = False
        audit.append({"check": "line_in_hunk", "passed": line_ok,
                      "class": "mechanical", "line": line})
        if not line_ok:
            failed.append("line_in_hunk")

    # 4+5. declared semantic classification (policy-gated, NOT
    # mechanically verifiable — audited downstream)
    kind_ok = ev.get("kind") != "out_of_diff_assumption"
    harm_ok = ev.get("harm") == "demonstrated"
    audit.append({"check": "kind_not_presumed_assumption",
                  "passed": kind_ok, "class": "declared",
                  "declared_kind": ev.get("kind")})
    audit.append({"check": "harm_declared_demonstrated",
                  "passed": harm_ok, "class": "declared",
                  "declared_harm": ev.get("harm")})
    if not kind_ok:
        failed.append("kind_not_presumed_assumption")
    if not harm_ok:
        failed.append("harm_declared_demonstrated")
    return audit, failed


def _patch_content(patch):
    """Patch text without headers/hunk markers, +/- stripped."""
    out = []
    for line in (patch or "").splitlines():
        if line.startswith("@@") or line.startswith("+++ ") \
                or line.startswith("--- "):
            continue
        out.append(line[1:] if line.startswith(("+", "-")) else line)
    return "\n".join(out)


def apply_evidence_gate(result, diff_files):
    """Deterministic, fail-closed severity gate over a parsed result.

    Every BLOCKING finding must pass all mechanical checks and carry
    declarations that satisfy policy (kind != out_of_diff_assumption,
    harm == demonstrated). Any failure converts the finding to
    non-blocking with machine_reason=BLOCKING_EVIDENCE_INSUFFICIENT
    and preserves the evidence object for audit. The overall
    assessment is then RECOMPUTED deterministically — machine
    downgrades are validated decisions, not untrusted contradictions,
    so zero surviving blockers resolves to CLEAR (never INCONCLUSIVE;
    that path is reserved for untrusted output in assess()).

    Returns (result', audit) where audit is one entry per blocking
    finding: {file, permitted, failed_checks, checks, finding_class}
    with mechanical vs declared classes marked per check.
    """
    findings = result.get("findings", [])
    audit = []
    for f in findings:
        if f.get("severity") != "blocking":
            continue
        checks, failed = _evidence_checks(f, diff_files)
        entry = {"file": f.get("file"),
                 "permitted": not failed,
                 "failed_checks": failed,
                 "checks": checks}
        if failed:
            f["severity"] = "non-blocking"
            f["machine_reason"] = MACHINE_DOWNGRADE_REASON
        audit.append(entry)
    blocking = any(f["severity"] == "blocking" for f in findings)
    if result.get("assessment") == "ISSUES_FOUND" and not blocking:
        result["assessment"] = "CLEAR"
        result["assessment_recomputed"] = True
    return result, audit


def normalize_v2(content, diff_files=None, gate=True):
    """Model output text -> (ReviewResult, gate_audit).

    ReviewResult is schema v2 when evidence fields are in play, v1
    shape otherwise. Accepts everything normalize() accepts, plus
    optional per-finding evidence objects. When gate is enabled,
    blocking findings are permission-checked against diff_files
    ({path: patch}); with gate enabled and diff_files missing, every
    blocker fails closed (no checks can run). With gate disabled the
    result equals normalize() plus preserved, validated evidence
    objects, and the audit is empty.
    """
    result = normalize(content)
    audit = []
    if result["assessment"] == INCONCLUSIVE:
        return result, audit
    obj = parse_model_output(content)
    raw_findings = obj.get("findings") if isinstance(obj, dict) else None
    has_evidence = isinstance(raw_findings, list) and any(
        isinstance(f, dict) and f.get("evidence") is not None
        for f in raw_findings)
    if not has_evidence and not gate:
        return result, audit
    # attach validated evidence objects (shape-invalid evidence is
    # dropped from advisory findings; on blocking findings it simply
    # fails the gate below)
    raw_by_index = {i: f for i, f in enumerate(raw_findings or [])
                    if isinstance(f, dict)}
    for i, f in enumerate(result["findings"]):
        raw_ev = (raw_by_index.get(i) or {}).get("evidence")
        ev, ok = _validate_evidence(raw_ev)
        if ok and ev is not None:
            f["evidence"] = ev
        elif not ok and f.get("severity") == "blocking":
            f["evidence"] = None
    if gate:
        result, audit = apply_evidence_gate(
            result, diff_files if diff_files is not None else {})
    schema = V2_SCHEMA_VERSION if (has_evidence or audit) \
        else RESULT_SCHEMA_VERSION
    result["schema_version"] = schema
    return result, audit
