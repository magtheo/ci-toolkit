"""Invariant tests for the review payload builder.

These encode the security model, not just behavior:
- event is the literal COMMENT (approval impossible by construction);
- inline comments only land on diff-addressable (file, line) pairs;
- malformed model output degrades to NEEDS_CHANGES, never LGTM.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from parse_review import (  # noqa: E402
    build_payload,
    parse_model_output,
    valid_lines_from_patch,
)

TOOLKIT_ROOT = pathlib.Path(__file__).resolve().parents[1]

PATCH = "@@ -1,2 +1,4 @@\n context\n-old\n+new1\n+new2\n rest"


def test_valid_lines_new_side_numbering():
    # hunk starts at new line 1; context and + lines count, - lines do not
    assert valid_lines_from_patch(PATCH) == {1, 2, 3, 4}


def test_valid_lines_multi_hunk():
    patch = "@@ -10,2 +20,2 @@\n a\n-b\n+c\n@@ -50,1 +60,1 @@\n+d"
    assert valid_lines_from_patch(patch) == {20, 21, 60}


def test_parse_model_output_strips_wrapping_prose():
    assert parse_model_output(
        'Sure! ```json\n{"verdict": "LGTM"}\n```') == {"verdict": "LGTM"}


def test_parse_model_output_malformed_is_empty():
    assert parse_model_output("no json at all") == {}
    assert parse_model_output("{broken json") == {}
    assert parse_model_output('["a", "list"]') == {}


def test_event_is_always_comment_regardless_of_output():
    for content in (
        '{"verdict": "LGTM", "findings": []}',
        '{"verdict": "APPROVE"}',
        '{"verdict": "LGTM", "event": "APPROVE", "findings": []}',
        "complete garbage",
    ):
        assert build_payload(content, [], "sha", "m")["event"] == "COMMENT"


def test_event_is_a_literal_in_source():
    src = (TOOLKIT_ROOT / "parse_review.py").read_text()
    assert '"event": "COMMENT"' in src


def test_malformed_output_degrades_to_needs_changes():
    body = build_payload("garbage", [], "sha", "m")["body"]
    assert "NEEDS_CHANGES" in body
    assert "LGTM" not in body.split("\n")[0]


def test_unknown_verdict_normalizes_to_needs_changes():
    body = build_payload('{"verdict": "SHIP IT"}', [], "sha", "m")["body"]
    assert "NEEDS_CHANGES" in body


def test_inline_comments_only_on_valid_lines():
    files = [{"filename": "a.py",
              "patch": "@@ -0,0 +1,2 @@\n+x = 1\n+y = 2"}]
    content = json.dumps({
        "verdict": "NEEDS_CHANGES",
        "summary": "s",
        "findings": [
            {"file": "a.py", "line": 1, "severity": "blocking",
             "comment": "on-line"},
            {"file": "a.py", "line": 99, "severity": "blocking",
             "comment": "off-line"},
            {"file": "not-in-diff.py", "line": 1, "severity": "blocking",
             "comment": "bad-file"},
        ],
        "good": [],
    })
    payload = build_payload(content, files, "sha", "m")
    assert [c["line"] for c in payload["comments"]] == [1]
    assert "off-line" in payload["body"]
    assert "bad-file" in payload["body"]


def test_suggestion_fenced_inline_and_in_body():
    files = [{"filename": "a.py",
              "patch": "@@ -0,0 +1,1 @@\n+x = 1"}]
    content = json.dumps({
        "verdict": "NEEDS_CHANGES", "summary": "s",
        "findings": [
            {"file": "a.py", "line": 1, "severity": "blocking",
             "comment": "c", "suggestion": "x = 2"},
            {"file": "a.py", "line": 42, "severity": "non-blocking",
             "comment": "c2", "suggestion": "y = 3"},
        ],
        "good": [],
    })
    payload = build_payload(content, files, "sha", "m")
    inline = payload["comments"][0]["body"]
    assert "```suggestion\nx = 2\n```" in inline
    assert "```suggestion\ny = 3\n```" in payload["body"]


def test_findings_not_a_list_is_ignored():
    content = '{"verdict": "LGTM", "findings": "oops"}'
    payload = build_payload(content, [], "sha", "m")
    assert payload["comments"] == []
