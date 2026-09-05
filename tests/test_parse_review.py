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
    normalize,
    parse_model_output,
    valid_lines_from_patch,
)
from render import build_payload  # noqa: E402

TOOLKIT_ROOT = pathlib.Path(__file__).resolve().parents[1]

PATCH = "@@ -1,2 +1,4 @@\n context\n-old\n+new1\n+new2\n rest"
FILES = [{"filename": "a.py",
          "patch": "@@ -0,0 +1,2 @@\n+x = 1\n+y = 2"}]


def _content(**kw):
    return json.dumps(kw)


def _payload(content, files):
    """The split pipeline: normalize (engine stage) -> render."""
    return build_payload(normalize(content), files, "sha", "m")


# ---- schema ---------------------------------------------------------------

def test_valid_clear():
    p = _payload(_content(assessment="CLEAR", summary="s",
                               findings=[], good=[]), [])
    assert "AI review · Clear" in p["body"]


def test_valid_issues_found():
    p = _payload(_content(assessment="ISSUES_FOUND", summary="s",
                 findings=[{"file": "a.py", "line": 1, "severity": "blocking",
                            "comment": "c"}]), FILES)
    assert "AI review · Issues found" in p["body"]
    assert "1 blocking issue" in p["body"]


def test_unknown_assessment_is_inconclusive():
    p = _payload(_content(assessment="LGTM", findings=[]), [])
    assert "AI review · Inconclusive" in p["body"]


def test_missing_assessment_is_inconclusive():
    p = _payload(_content(summary="s", findings=[]), [])
    assert "AI review · Inconclusive" in p["body"]


def test_malformed_json_is_inconclusive():
    p = _payload("complete garbage {broken", [])
    assert "AI review · Inconclusive" in p["body"]
    assert "Do not treat this review as clear." in p["body"]


# ---- deterministic consistency --------------------------------------------

def test_clear_with_blocking_finding_normalizes_to_issues():
    p = _payload(_content(assessment="CLEAR", summary="s",
                 findings=[{"file": "a.py", "line": 1,
                            "severity": "blocking", "comment": "c"}]), FILES)
    assert "AI review · Issues found" in p["body"]
    assert "AI review · Clear" not in p["body"]


def test_clear_with_advisory_only_stays_clear():
    p = _payload(_content(assessment="CLEAR", summary="s",
                 findings=[{"file": "a.py", "line": 2,
                            "severity": "non-blocking", "comment": "c"}]), FILES)
    assert "AI review · Clear" in p["body"]
    assert "0 blocking · 1 advisory" in p["body"]


# ---- strict schema validation (fail closed) --------------------------------

def test_clear_with_findings_not_a_list_is_inconclusive():
    p = _payload(_content(assessment="CLEAR", findings="oops"), [])
    assert "AI review · Inconclusive" in p["body"]
    assert "AI review · Clear" not in p["body"]


def test_clear_with_findings_missing_is_inconclusive():
    p = _payload(_content(assessment="CLEAR"), [])
    assert "AI review · Inconclusive" in p["body"]


def test_malformed_finding_is_inconclusive():
    for bad in (
        [{"comment": "no file"}],
        [{"file": "a.py", "severity": "blocking"}],  # no comment
        [{"file": "", "severity": "blocking", "comment": "c"}],
        ["not-a-dict"],
    ):
        p = _payload(_content(assessment="CLEAR", findings=bad), [])
        assert "AI review · Inconclusive" in p["body"], bad


def test_severity_case_whitespace_normalized():
    p = _payload(_content(assessment="CLEAR", summary="s",
                 findings=[{"file": "a.py", "line": 1,
                            "severity": " BLOCKING ", "comment": "c"}]), FILES)
    assert "AI review · Issues found" in p["body"]
    assert "1 blocking issue" in p["body"]


def test_unknown_severity_is_inconclusive():
    p = _payload(_content(assessment="ISSUES_FOUND",
                 findings=[{"file": "a.py", "severity": "critical",
                            "comment": "c"}]), FILES)
    assert "AI review · Inconclusive" in p["body"]


# ---- classification is asymmetric + fail-closed -----------------------------

def test_contradictory_issues_found_label_with_advisory_only_is_inconclusive():
    # the model reports issues, but no blocking finding survived
    # validation — contradictory output must never become Clear
    p = _payload(_content(assessment="ISSUES_FOUND", summary="s",
                 findings=[{"file": "a.py", "line": 2,
                            "severity": "non-blocking", "comment": "c"}]), FILES)
    assert "AI review · Inconclusive" in p["body"]
    assert "AI review · Clear" not in p["body"]


def test_contradictory_issues_found_label_with_zero_findings_is_inconclusive():
    p = _payload(_content(assessment="ISSUES_FOUND", findings=[]), [])
    assert "AI review · Inconclusive" in p["body"]


def test_clear_label_with_advisory_only_stays_clear():
    p = _payload(_content(assessment="CLEAR", summary="s",
                 findings=[{"file": "a.py", "line": 2,
                            "severity": "non-blocking", "comment": "c"}]), FILES)
    assert "AI review · Clear" in p["body"]
    assert "0 blocking · 1 advisory" in p["body"]


def test_blocking_evidence_overrides_optimistic_label():
    for label in ("CLEAR", "ISSUES_FOUND"):
        p = _payload(_content(assessment=label,
                     findings=[{"file": "a.py", "line": 1,
                                "severity": "blocking", "comment": "c"}]), FILES)
        assert "AI review · Issues found" in p["body"], label


def test_parser_failure_never_clear():
    # note: valid JSON wrapped in trailing prose IS valid (wrapped-output
    # tolerance is a feature) — covered by
    # test_parse_model_output_strips_wrapping_prose
    for content in ("", "no json", "{broken", '["list"]'):
        p = _payload(content, [])
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
        body = _payload(content, FILES)["body"]
        assert "LGTM" not in body
        assert "Verdict:" not in body
        assert "NEEDS_CHANGES" not in body
        assert "approved" not in body.lower()


def test_advisory_terminology_not_non_blocking():
    # advisory-only + CLEAR label renders advisories under details
    p = _payload(_content(assessment="CLEAR", summary="s",
                 findings=[{"file": "a.py", "line": 2,
                            "severity": "non-blocking", "comment": "c"}]), FILES)
    assert "### Advisory" in p["body"]
    assert "non-blocking" not in p["body"].replace("### Advisory", "")


def test_progressive_disclosure_details_blocks():
    p = _payload(_content(assessment="CLEAR", summary="s",
                               findings=[], good=["g"]), [])
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
        assert _payload(content, FILES)["event"] == "COMMENT"


def test_event_is_a_literal_in_source():
    src = (TOOLKIT_ROOT / "render.py").read_text()
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
    p = _payload(content, FILES)
    assert [c["line"] for c in p["comments"]] == [1]
    assert "```suggestion\nx = 2\n```" in p["comments"][0]["body"]
    assert "**Blocking**:" in p["comments"][0]["body"]
    assert "off-line" in p["body"]
    assert "bad-file" in p["body"]


def test_parse_model_output_strips_wrapping_prose():
    assert parse_model_output(
        'Sure! ```json\n{"assessment": "CLEAR"}\n```') == {
            "assessment": "CLEAR"}
