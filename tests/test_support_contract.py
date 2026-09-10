"""Layer (b) support contract tests (phase 20b).

Locks the approved design (plans/layer-b-structured-support-design.md,
#47 rev 2):

- support corpus is the EXACT model-visible/budgeted input (one
  effective_review_input feeding prompts AND validation; the test-only
  legacy reference pins budget byte-identity);
- segment-local matching (no cross-boundary quotes); policy text and
  engine framing are never matchable;
- anti-vacuity floor (>= 16 normalized chars AND >= 3 lexical tokens),
  boundaries locked;
- under-support (missing/null/malformed/non-matching) is deterministic
  DOWNGRADE to advisory with a machine reason — never dropped, never
  INCONCLUSIVE; structural failure and the C7-style label mismatch
  stay fail-closed in parse_review;
- post-support assessment: >= 1 surviving blocker -> ISSUES_FOUND;
  all blockers demoted -> CLEAR; no blockers ever -> INCONCLUSIVE.
"""

import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import engine  # noqa: E402
from parse_review import normalize  # noqa: E402

PATCH_A = "@@ -1 +1 @@\n+return handler.process(cfg)"
PATCH_B = "@@ -1 +1 @@\n+omega handler configuration"
# canonical supported quote (27 normalized chars, 4 tokens)
QUOTE_A = "return handler.process(cfg)"
QUOTE_B = "omega handler configuration"


def _input(**over):
    base = {
        "schema_version": 1,
        "title": "t",
        "body": "b",
        "files": [
            {"path": "a.py", "status": "modified", "patch": PATCH_A},
            {"path": "b.py", "status": "modified", "patch": PATCH_B},
        ],
        "policy": "SECRET RUBRIC TEXT NEVER MATCHABLE",
        "model": {"id": "m", "temperature": 0.2, "max_tokens": 2000},
    }
    base.update(over)
    return base


def _findings(severity="blocking", support="absent", file="a.py",
              comment="defect"):
    f = {"file": file, "comment": comment, "severity": severity,
         "line": 1, "suggestion": None}
    if support == "absent":
        pass
    elif support is None or support == "null":
        f["support"] = None
    else:
        f["support"] = support
    return [f]


def _model_json(assessment, findings):
    return json.dumps({"assessment": assessment, "findings": findings,
                       "summary": "s", "good": []})


def _policy_result(content, review_input):
    return engine.apply_support_policy(normalize(content), review_input)


# ---- parse layer: structural extraction, under-support != schema failure ----

def test_support_passes_through_when_wellformed():
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": QUOTE_A}]))
    result = normalize(content)
    assert result["findings"][0]["support"] == [{"quote": QUOTE_A}]


def test_missing_null_or_empty_support_leaves_key_absent():
    for support in ("absent", None, []):
        content = _model_json("ISSUES_FOUND", _findings(support=support))
        result = normalize(content)
        assert result["assessment"] == "ISSUES_FOUND"
        assert "support" not in result["findings"][0]
        assert set(result["findings"][0]) == {
            "file", "comment", "severity", "line", "suggestion"}


def test_malformed_support_shapes_drop_per_item_never_invalidate():
    for support in ("not-a-list", [{"quote": 5}], ["x"], [{"nope": 1}],
                    123):
        content = _model_json("ISSUES_FOUND", _findings(support=support))
        result = normalize(content)
        assert result["assessment"] == "ISSUES_FOUND", support
        assert "support" not in result["findings"][0], support


def test_empty_quote_item_is_structural_but_vacuous():
    # typed correctly (quote: str) so parse carries it; the engine's
    # anti-vacuity floor rejects it -> deterministic downgrade
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": ""}]))
    parsed = normalize(content)
    assert parsed["findings"][0]["support"] == [{"quote": ""}]
    result = _policy_result(content, _input())
    assert result["assessment"] == "CLEAR"
    assert result["findings"][0]["severity"] == "advisory"


def test_malformed_item_does_not_poison_valid_sibling():
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": 5}, {"quote": QUOTE_A}]))
    result = normalize(content)
    assert result["findings"][0]["support"] == [{"quote": QUOTE_A}]


def test_advisory_support_is_carried_but_never_gating():
    content = _model_json("CLEAR", _findings(
        severity="non-blocking", support=[{"quote": QUOTE_A}]))
    result = _policy_result(content, _input())
    assert result["assessment"] == "CLEAR"
    assert result["findings"][0]["support"] == [{"quote": QUOTE_A}]
    assert engine.SUPPORT_DOWNGRADE_NOTE not in result["findings"][0]["comment"]

    content = _model_json("CLEAR", _findings(
        severity="non-blocking", support="not-a-list"))
    result = _policy_result(content, _input())
    assert result["assessment"] == "CLEAR"
    assert "support" not in result["findings"][0]


# ---- engine layer: matching semantics ---------------------------------------

def test_supported_blocker_survives():
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": QUOTE_A}]))
    result = _policy_result(content, _input())
    assert result["assessment"] == "ISSUES_FOUND"
    assert result["findings"][0]["severity"] == "blocking"
    assert engine.SUPPORT_DOWNGRADE_NOTE not in result["findings"][0]["comment"]


def test_matching_is_case_and_whitespace_insensitive():
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": "  RETURN HANDLER.PROCESS(cfg)  "}]))
    result = _policy_result(content, _input())
    assert result["findings"][0]["severity"] == "blocking"


def test_unsupported_only_blocker_is_demoted_to_clear_with_reason():
    content = _model_json("ISSUES_FOUND", _findings(support="absent"))
    result = _policy_result(content, _input())
    assert result["assessment"] == "CLEAR"
    f = result["findings"][0]
    assert f["severity"] == "advisory"
    assert f["comment"].endswith(engine.SUPPORT_DOWNGRADE_NOTE)
    assert f["comment"].startswith("defect")


def test_partial_demotion_keeps_issues_found():
    content = _model_json("ISSUES_FOUND", _findings(support="absent") +
                          _findings(file="b.py",
                                    support=[{"quote": QUOTE_B}]))
    result = _policy_result(content, _input())
    assert result["assessment"] == "ISSUES_FOUND"
    assert [f["severity"] for f in result["findings"]] == \
        ["advisory", "blocking"]


def test_c7_style_label_mismatch_without_demotion_stays_inconclusive():
    # ISSUES_FOUND label, advisory findings only, nothing demoted:
    # parse-layer fail-closed semantics are untouched by the policy
    content = _model_json("ISSUES_FOUND", _findings(
        severity="non-blocking", support=[{"quote": QUOTE_A}]))
    result = _policy_result(content, _input())
    assert result["assessment"] == "INCONCLUSIVE"
    assert result["findings"] == []


def test_clear_label_with_unsupported_blockers_is_clear_after_demotion():
    # normalize elevates CLEAR+blocking -> ISSUES_FOUND; policy demotes
    # the unsupported blockers back to a CLEAR with reasons
    content = _model_json("CLEAR", _findings(support="absent"))
    result = _policy_result(content, _input())
    assert result["assessment"] == "CLEAR"
    assert result["findings"][0]["severity"] == "advisory"


def test_inconclusive_fragment_is_a_no_op():
    result = _policy_result("not json at all", _input())
    assert result["assessment"] == "INCONCLUSIVE"
    assert result["findings"] == []


# ---- segment locality + exclusions ------------------------------------------

def test_quote_spanning_body_and_diff_never_matches():
    tail = "grounding evidence inside body text"
    review_input = _input(body="body text " + tail)
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": tail + " return handler.process(cfg)"}]))
    result = _policy_result(content, review_input)
    assert result["findings"][0]["severity"] == "advisory"


def test_quote_spanning_two_files_never_matches():
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": QUOTE_A + " " + QUOTE_B}]))
    result = _policy_result(content, _input())
    assert result["findings"][0]["severity"] == "advisory"


def test_policy_system_prompt_and_framing_never_match():
    for quote in ("SECRET RUBRIC TEXT NEVER MATCHABLE",
                  "you are an advisory code reviewer. follow this rubric",
                  "pull request title:"):
        content = _model_json("ISSUES_FOUND", _findings(
            support=[{"quote": quote}]))
        result = _policy_result(content, _input())
        assert result["findings"][0]["severity"] == "advisory", quote


def test_engine_notes_never_match(monkeypatch):
    monkeypatch.setenv("AI_REVIEW_MAX_FILES", "1")
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": "file list capped at 1 of 2 changed files"}]))
    result = _policy_result(content, _input())
    assert result["findings"][0]["severity"] == "advisory"


# ---- budget identity: the validator sees exactly what the model sees --------

def test_quote_beyond_body_budget_never_matches():
    tail = "tail sentinel beyond body budget"
    review_input = _input(body="x" * 2000 + tail)
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": tail}]))
    result = _policy_result(content, review_input)
    assert result["findings"][0]["severity"] == "advisory"


def test_quote_beyond_file_cap_never_matches(monkeypatch):
    monkeypatch.setenv("AI_REVIEW_MAX_FILES", "1")
    content = _model_json("ISSUES_FOUND", _findings(
        file="b.py", support=[{"quote": QUOTE_B}]))
    result = _policy_result(content, _input())
    assert result["findings"][0]["severity"] == "advisory"


def test_quote_beyond_diff_truncation_never_matches(monkeypatch):
    # section a.py is 68 chars; max_diff 91 keeps exactly 21 chars of
    # b.py ("----- b.py (modified)") — QUOTE_B lies beyond the cut
    monkeypatch.setenv("AI_REVIEW_MAX_DIFF", "91")
    content = _model_json("ISSUES_FOUND", _findings(
        file="b.py", support=[{"quote": QUOTE_B}]))
    result = _policy_result(content, _input())
    assert result["findings"][0]["severity"] == "advisory"


def test_quote_inside_kept_prefix_of_truncated_section_matches(monkeypatch):
    monkeypatch.setenv("AI_REVIEW_MAX_DIFF", "91")
    content = _model_json("ISSUES_FOUND", _findings(
        file="b.py", support=[{"quote": "----- b.py (modified)"}]))
    result = _policy_result(content, _input())
    assert result["findings"][0]["severity"] == "blocking"


# ---- anti-vacuity floor (frozen: >= 16 normalized chars, >= 3 tokens) --------

def test_vacuous_quotes_never_certify():
    for quote in ("if", "a", "!!!", "return", "aa bb ccccccccc",  # 15 ch/3 tok
                  "ab cccccccccccccc"):                           # 16 ch/2 tok
        content = _model_json("ISSUES_FOUND", _findings(
            support=[{"quote": quote}]))
        result = _policy_result(content, _input())
        assert result["findings"][0]["severity"] == "advisory", quote


def test_boundary_conforming_quote_certifies():
    # exactly 16 normalized chars and exactly 3 tokens, occurring in the title
    review_input = _input(title="aa bb cccccccccc context")
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": "AA \tBB\nCCCCCCCCCC"}]))
    result = _policy_result(content, review_input)
    assert result["findings"][0]["severity"] == "blocking"


def test_constants_are_frozen():
    assert engine._SUPPORT_MIN_CHARS == 16
    assert engine._SUPPORT_MIN_TOKENS == 3


# ---- budget byte-identity: effective_review_input == legacy reference --------
# Test-only independent reference (the runtime haystack is never rebuilt
# elsewhere — this pins that the refactor changed nothing).

def _legacy_budget(review_input):
    max_files = int(os.environ.get("AI_REVIEW_MAX_FILES", "200"))
    max_diff = int(os.environ.get("AI_REVIEW_MAX_DIFF", "120000"))
    files = review_input["files"]
    files_note = ""
    if len(files) > max_files:
        files = files[:max_files]
        files_note = "\n[file list capped at {0} of {1} changed files]".format(
            max_files, len(review_input["files"]))
    changed_list = "\n".join(f["path"] for f in files)
    diff_text = "\n\n".join(
        "----- {0} ({1}) -----\n{2}".format(f["path"], f["status"], f["patch"])
        for f in files if f.get("patch") is not None)
    trunc_note = ""
    if len(diff_text) > max_diff:
        diff_text = diff_text[:max_diff]
        trunc_note = "\n[diff truncated at {0} characters]".format(max_diff)
    return changed_list, diff_text, files_note, trunc_note


def test_budget_tuple_is_byte_identical_to_legacy_reference(monkeypatch):
    third = ("----- c.py (modified) -----\n@@ -1 +1 @@\n+third section text")
    base = [
        {"path": "a.py", "status": "modified", "patch": PATCH_A},
        {"path": "b.py", "status": "modified", "patch": PATCH_B},
        {"path": "c.py", "status": "modified", "patch": third},
    ]
    cases = [
        ({}, _input(files=base)),                                   # no cap
        ({"AI_REVIEW_MAX_DIFF": "91"}, _input(files=base)),         # kept b hdr
        ({"AI_REVIEW_MAX_DIFF": "70"}, _input(files=base)),         # cut in joiner
        ({"AI_REVIEW_MAX_DIFF": "69"}, _input(files=base)),         # cut in joiner
        ({"AI_REVIEW_MAX_DIFF": "46"}, _input(files=base)),         # cut mid-a
        ({"AI_REVIEW_MAX_DIFF": "28"}, _input(files=base)),         # a header+1
        ({"AI_REVIEW_MAX_DIFF": "27"}, _input(files=base)),         # exact hdr
        ({"AI_REVIEW_MAX_DIFF": "26"}, _input(files=base)),         # hdr cut
        ({"AI_REVIEW_MAX_DIFF": "5"}, _input(files=base)),          # tiny
        ({"AI_REVIEW_MAX_DIFF": "0"}, _input(files=base)),          # zero
        ({"AI_REVIEW_MAX_FILES": "2"}, _input(files=base)),         # file cap
        ({"AI_REVIEW_MAX_FILES": "0"}, _input(files=base)),         # all capped
    ]
    for env, review_input in cases:
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        got = engine.effective_review_input(review_input)
        want = _legacy_budget(review_input)
        assert (got["changed_list"], got["diff_text"], got["files_note"],
                got["trunc_note"]) == want, env
        assert engine._budget(review_input) == want, env
        # every segment the validator may match is literally inside the
        # model-visible diff text (budget identity, containment form)
        for name, text in got["segments"]:
            if name.startswith("diff:"):
                assert text in want[1], (env, name)
        for k in env:
            monkeypatch.delenv(k)


# ---- end-to-end wiring through run_review (model call stubbed) ---------------

def _stub(monkeypatch, content):
    import json as _json

    def fake_post(payload):
        return (200, _json.dumps({
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2,
                      "total_tokens": 3},
        }).encode())

    monkeypatch.setattr(engine, "_post_chat", fake_post)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")


def test_run_review_applies_support_policy_supported(monkeypatch):
    _stub(monkeypatch, _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": QUOTE_A}])))
    result = engine.run_review(_input())
    assert result["assessment"] == "ISSUES_FOUND"
    assert result["findings"][0]["severity"] == "blocking"
    assert set(result) == {"schema_version", "assessment", "findings",
                           "summary", "good", "usage", "raw_output"}


def test_run_review_applies_support_policy_demoted(monkeypatch):
    _stub(monkeypatch, _model_json("ISSUES_FOUND", _findings(
        support="absent")))
    result = engine.run_review(_input())
    assert result["assessment"] == "CLEAR"
    assert result["findings"][0]["severity"] == "advisory"
    assert result["findings"][0]["comment"].endswith(
        engine.SUPPORT_DOWNGRADE_NOTE)
