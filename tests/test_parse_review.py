"""Semantic and presentation tests for the review payload builder.

Encodes the interface-vocabulary model (2026-08-28):
- assessments CLEAR / ISSUES_FOUND / INCONCLUSIVE (never LGTM or
  approval vocabulary);
- deterministic consistency: CLEAR + blocking -> ISSUES_FOUND;
  ISSUES_FOUND without findings -> INCONCLUSIVE; parser failure can
  never yield CLEAR;
- user-facing presentation: "AI review · Clear / Issues found /
  Inconclusive" headings, Blocking/Advisory terminology, progressive
  disclosure;
- authority: event is the literal COMMENT regardless of model output.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from parse_review import (  # noqa: E402
    assess,
    build_payload,
    parse_model_output,
    valid_lines_from_patch,
)

TOOLKIT_ROOT = pathlib.Path(__file__).resolve().parents[1]

PATCH = "@@ -1,2 +1,4 @@\n context\n-old\n+new1\n+new2\n rest"
FILES = [{"filename": "a.py",
          "patch": "@@ -0,0 +1,2 @@\n+x = 1\n+y = 2"}]


def _content(**kw):
    return json.dumps(kw)


# ---- schema ---------------------------------------------------------------

def test_valid_clear():
    p = build_payload(_content(assessment="CLEAR", summary="s",
                               findings=[], good=[]),
                      [], "sha", "m")
    assert "AI review · Clear" in p["body"]


def test_valid_issues_found():
    p = build_payload(
        _content(assessment="ISSUES_FOUND", summary="s",
                 findings=[{"file": "a.py", "line": 1, "severity": "blocking",
                            "comment": "c"}]),
        FILES, "sha", "m")
    assert "AI review · Issues found" in p["body"]
    assert "1 blocking issue" in p["body"]


def test_unknown_assessment_is_inconclusive():
    p = build_payload(_content(assessment="LGTM", findings=[]), [], "sha", "m")
    assert "AI review · Inconclusive" in p["body"]


def test_missing_assessment_is_inconclusive():
    p = build_payload(_content(summary="s", findings=[]), [], "sha", "m")
    assert "AI review · Inconclusive" in p["body"]


def test_malformed_json_is_inconclusive():
    p = build_payload("complete garbage {broken", [], "sha", "m")
    assert "AI review · Inconclusive" in p["body"]
    assert "Do not treat this review as clear." in p["body"]


# ---- deterministic consistency --------------------------------------------

def test_clear_with_blocking_finding_normalizes_to_issues():
    p = build_payload(
        _content(assessment="CLEAR", summary="s",
                 findings=[{"file": "a.py", "line": 1,
                            "severity": "blocking", "comment": "c"}]),
        FILES, "sha", "m")
    assert "AI review · Issues found" in p["body"]
    assert "AI review · Clear" not in p["body"]


def test_clear_with_advisory_only_stays_clear():
    p = build_payload(
        _content(assessment="CLEAR", summary="s",
                 findings=[{"file": "a.py", "line": 2,
                            "severity": "non-blocking", "comment": "c"}]),
        FILES, "sha", "m")
    assert "AI review · Clear" in p["body"]
    assert "0 blocking · 1 advisory" in p["body"]


def test_issues_found_without_findings_is_inconclusive():
    assessment, findings = assess({"assessment": "ISSUES_FOUND",
                                   "findings": []})
    assert assessment == "INCONCLUSIVE"
    assert findings == []


def test_parser_failure_never_clear():
    # note: valid JSON wrapped in trailing prose IS valid (wrapped-output
    # tolerance is a feature) — covered by
    # test_parse_model_output_strips_wrapping_prose
    for content in ("", "no json", "{broken", '["list"]'):
        p = build_payload(content, [], "sha", "m")
        assert "AI review · Clear" not in p["body"], content
        assert "AI review · Inconclusive" in p["body"], content


# ---- presentation ----------------------------------------------------------

def test_no_lgtm_or_verdict_vocabulary():
    for content in (_content(assessment="CLEAR", findings=[]),
                    _content(assessment="ISSUES_FOUND",
                             findings=[{"file": "a.py", "line": 1,
                                        "severity": "blocking",
                                        "comment": "c"}]),
                    "garbage"):
        body = build_payload(content, FILES, "sha", "m")["body"]
        assert "LGTM" not in body
        assert "Verdict:" not in body
        assert "NEEDS_CHANGES" not in body
        assert "approved" not in body.lower()


def test_advisory_terminology_not_non_blocking():
    p = build_payload(
        _content(assessment="ISSUES_FOUND", summary="s",
                 findings=[{"file": "a.py", "line": 2,
                            "severity": "non-blocking", "comment": "c"}]),
        FILES, "sha", "m")
    assert "### Advisory" in p["body"]
    assert "non-blocking" not in p["body"].replace("### Advisory", "")


def test_progressive_disclosure_details_blocks():
    p = build_payload(_content(assessment="CLEAR", summary="s",
                               findings=[], good=["g"]),
                      [], "sha", "m")
    assert "<details>" in p["body"]
    assert "<summary>Review metadata</summary>" in p["body"]
    assert "Model: m" in p["body"]
    assert "Commit: sha" in p["body"]
    assert "Assessment: CLEAR" in p["body"]


# ---- authority -------------------------------------------------------------

def test_event_is_always_comment_regardless_of_output():
    for content in (
        _content(assessment="CLEAR", findings=[]),
        _content(assessment="ISSUES_FOUND", event="APPROVE",
                 findings=[{"file": "a.py", "line": 1,
                            "severity": "blocking", "comment": "c"}]),
        json.dumps({"event": "APPROVE", "assessment": "CLEAR"}),
        "garbage",
    ):
        assert build_payload(content, FILES, "sha", "m")["event"] == "COMMENT"


def test_event_is_a_literal_in_source():
    src = (TOOLKIT_ROOT / "parse_review.py").read_text()
    assert '"event": "COMMENT"' in src


# ---- inline placement (unchanged behavior, new vocabulary) -----------------

def test_valid_lines_new_side_numbering():
    assert valid_lines_from_patch(PATCH) == {1, 2, 3, 4}


def test_inline_comments_only_on_valid_lines():
    content = _content(
        assessment="ISSUES_FOUND", summary="s",
        findings=[
            {"file": "a.py", "line": 1, "severity": "blocking",
             "comment": "on-line", "suggestion": "x = 2"},
            {"file": "a.py", "line": 99, "severity": "blocking",
             "comment": "off-line"},
            {"file": "not-in-diff.py", "line": 1, "severity": "blocking",
             "comment": "bad-file"},
        ])
    p = build_payload(content, FILES, "sha", "m")
    assert [c["line"] for c in p["comments"]] == [1]
    assert "```suggestion\nx = 2\n```" in p["comments"][0]["body"]
    assert "**Blocking**:" in p["comments"][0]["body"]
    assert "off-line" in p["body"]
    assert "bad-file" in p["body"]


def test_parse_model_output_strips_wrapping_prose():
    assert parse_model_output(
        'Sure! ```json\n{"assessment": "CLEAR"}\n```') == {
            "assessment": "CLEAR"}
