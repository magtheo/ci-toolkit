"""Layer (b) support contract tests (phase 20b).

Locks the approved design (plans/layer-b-structured-support-design.md,
#47 rev 2) plus the #48 review fixes:

- support corpus is the EXACT model-visible/budgeted input (one
  effective_review_input feeding prompts AND validation; the test-only
  legacy reference pins budget byte-identity);
- segment-local matching (no cross-boundary quotes); policy text,
  engine framing, and GENERATED diff-section headers are never
  matchable — actual patch bytes only;
- anti-vacuity floor (>= 16 normalized chars AND >= 3 lexical tokens),
  boundaries locked; casefold (not lower) is the normalization;
- under-support (missing/null/malformed/non-matching) is deterministic
  DOWNGRADE to the CANONICAL "non-blocking" severity with a truthful
  machine reason — never dropped, never INCONCLUSIVE; structural
  failure and the C7-style label mismatch stay fail-closed;
- engine-derived provenance: the model supplies only the quote, the
  engine annotates the first matching item with engine_match
  {kind, id}; unmatched/vacuous items get no fabricated provenance;
- post-support assessment: >= 1 surviving blocker -> ISSUES_FOUND;
  all blockers demoted -> CLEAR; no blockers ever -> INCONCLUSIVE.
"""

import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import engine  # noqa: E402
from parse_review import normalize, SEVERITIES  # noqa: E402

PATCH_A = "@@ -1 +1 @@\n+return handler.process(cfg)"
PATCH_B = "@@ -1 +1 @@\n+omega handler configuration"
# canonical supported quote (27 normalized chars, 4 tokens)
QUOTE_A = "return handler.process(cfg)"
QUOTE_B = "omega handler configuration"
HEADER_B = "----- b.py (modified) -----\n"  # 28 chars, generated framing


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
    assert engine.SUPPORT_DOWNGRADE_PREFIX not in \
        result["findings"][0]["comment"]

    content = _model_json("CLEAR", _findings(
        severity="non-blocking", support="not-a-list"))
    result = _policy_result(content, _input())
    assert result["assessment"] == "CLEAR"
    assert "support" not in result["findings"][0]


# ---- engine layer: matching semantics ---------------------------------------

def test_supported_blocker_survives_with_provenance():
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": QUOTE_A}]))
    result = _policy_result(content, _input())
    assert result["assessment"] == "ISSUES_FOUND"
    assert result["findings"][0]["severity"] == "blocking"
    assert engine.SUPPORT_DOWNGRADE_PREFIX not in \
        result["findings"][0]["comment"]
    item = result["findings"][0]["support"][0]
    assert item["engine_match"] == {"kind": "diff", "id": "a.py"}


def test_matching_is_case_and_whitespace_insensitive():
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": "  RETURN HANDLER.PROCESS(cfg)  "}]))
    result = _policy_result(content, _input())
    assert result["findings"][0]["severity"] == "blocking"


def test_casefold_not_lower_is_the_normalization():
    # lower() would keep "straße" distinct from "STRASSE"; casefold
    # (the documented contract) unifies them
    review_input = _input(title="die Straße Planung Kontext hier")
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": "STRASSE PLANUNG KONTEXT"}]))
    result = _policy_result(content, review_input)
    assert result["findings"][0]["severity"] == "blocking"


def test_unsupported_only_blocker_is_demoted_with_truthful_reason():
    content = _model_json("ISSUES_FOUND", _findings(support="absent"))
    result = _policy_result(content, _input())
    assert result["assessment"] == "CLEAR"
    f = result["findings"][0]
    assert f["severity"] == "non-blocking"
    assert f["comment"].endswith(
        engine.support_downgrade_note("support_missing"))
    assert f["comment"].startswith("defect")


def test_demoted_severity_is_always_canonical():
    # the machine enum is parse_review.SEVERITIES — "advisory" is
    # presentation vocabulary only and must never appear in a result
    for support in ("absent", None, "not-a-list", [{"quote": ""}],
                    [{"quote": "no such quote exists anywhere here"}]):
        content = _model_json("ISSUES_FOUND", _findings(support=support))
        result = _policy_result(content, _input())
        assert all(f["severity"] in SEVERITIES
                   for f in result["findings"]), support
        assert all(f["severity"] != "advisory"
                   for f in result["findings"]), support


def test_downgrade_reasons_are_truthful_per_path():
    cases = [
        ("absent", "support_missing"),
        (None, "support_missing"),
        ([], "support_missing"),
        ([{"quote": ""}], "support_vacuous"),
        ([{"quote": "if"}], "support_vacuous"),
        ([{"quote": "aa bb ccccccccc"}], "support_vacuous"),  # 15ch/3tok
        ([{"quote": "ab cccccccccccccc"}], "support_vacuous"),  # 16ch/2tok
        ([{"quote": "no such quote exists anywhere here"}],
         "support_not_found"),
        # vacuous + non-vacuous non-matching -> the strongest true code
        ([{"quote": "if"},
          {"quote": "no such quote exists anywhere here"}],
         "support_not_found"),
    ]
    for support, reason in cases:
        content = _model_json("ISSUES_FOUND", _findings(support=support))
        result = _policy_result(content, _input())
        assert result["findings"][0]["comment"].endswith(
            engine.support_downgrade_note(reason)), support
        assert result["assessment"] == "CLEAR"


def test_partial_demotion_keeps_issues_found():
    content = _model_json("ISSUES_FOUND", _findings(support="absent") +
                          _findings(file="b.py",
                                    support=[{"quote": QUOTE_B}]))
    result = _policy_result(content, _input())
    assert result["assessment"] == "ISSUES_FOUND"
    assert [f["severity"] for f in result["findings"]] == \
        ["non-blocking", "blocking"]


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
    assert result["findings"][0]["severity"] == "non-blocking"


def test_inconclusive_fragment_is_a_no_op():
    result = _policy_result("not json at all", _input())
    assert result["assessment"] == "INCONCLUSIVE"
    assert result["findings"] == []


# ---- provenance: engine-derived, never fabricated ---------------------------

def test_provenance_first_match_is_deterministic():
    # the same phrase present in body AND diff resolves to the body —
    # effective_review_input segment order (title, body, changed_files,
    # files) is the documented deterministic order
    phrase = "shared evidence phrase here"
    review_input = _input(body="intro " + phrase,
                          files=[{"path": "a.py", "status": "modified",
                                  "patch": "@@ -1 +1 @@\n+" + phrase},
                                 {"path": "b.py", "status": "modified",
                                  "patch": PATCH_B}])
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": phrase}]))
    result = _policy_result(content, review_input)
    assert result["findings"][0]["severity"] == "blocking"
    assert result["findings"][0]["support"][0]["engine_match"] == \
        {"kind": "body", "id": ""}


def test_title_match_provenance():
    review_input = _input(title="aa bb cccccccccc context")
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": "AA \tBB\nCCCCCCCCCC"}]))
    result = _policy_result(content, review_input)
    assert result["findings"][0]["severity"] == "blocking"
    assert result["findings"][0]["support"][0]["engine_match"] == \
        {"kind": "title", "id": ""}


def test_unmatched_and_vacuous_items_get_no_provenance():
    content = _model_json("ISSUES_FOUND", _findings(support=[
        {"quote": "if"},                                # vacuous
        {"quote": "no such quote exists anywhere here"},  # non-matching
        {"quote": QUOTE_A},                             # the matching one
    ]))
    result = _policy_result(content, _input())
    items = result["findings"][0]["support"]
    assert "engine_match" not in items[0]
    assert "engine_match" not in items[1]
    assert items[2]["engine_match"] == {"kind": "diff", "id": "a.py"}
    assert result["findings"][0]["severity"] == "blocking"


def test_demoted_support_carries_no_engine_match():
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": "no such quote exists anywhere here"}]))
    result = _policy_result(content, _input())
    assert "engine_match" not in result["findings"][0]["support"][0]


# ---- segment locality + exclusions ------------------------------------------

def test_quote_spanning_body_and_diff_never_matches():
    tail = "grounding evidence inside body text"
    review_input = _input(body="body text " + tail)
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": tail + " return handler.process(cfg)"}]))
    result = _policy_result(content, review_input)
    assert result["findings"][0]["severity"] == "non-blocking"


def test_quote_spanning_two_files_never_matches():
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": QUOTE_A + " " + QUOTE_B}]))
    result = _policy_result(content, _input())
    assert result["findings"][0]["severity"] == "non-blocking"


def test_policy_system_prompt_framing_and_headers_never_match():
    for quote in ("SECRET RUBRIC TEXT NEVER MATCHABLE",
                  "you are an advisory code reviewer. follow this rubric",
                  "pull request title:",
                  HEADER_B.strip(),          # generated section header
                  "----- a.py (modified)"):
        content = _model_json("ISSUES_FOUND", _findings(
            support=[{"quote": quote}]))
        result = _policy_result(content, _input())
        assert result["findings"][0]["severity"] == "non-blocking", quote
        assert result["findings"][0]["comment"].endswith(
            engine.support_downgrade_note("support_not_found")), quote


def test_engine_notes_never_match(monkeypatch):
    monkeypatch.setenv("AI_REVIEW_MAX_FILES", "1")
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": "file list capped at 1 of 2 changed files"}]))
    result = _policy_result(content, _input())
    assert result["findings"][0]["severity"] == "non-blocking"


# ---- budget identity: the validator sees exactly what the model sees --------

def test_quote_beyond_body_budget_never_matches():
    tail = "tail sentinel beyond body budget"
    review_input = _input(body="x" * 2000 + tail)
    content = _model_json("ISSUES_FOUND", _findings(
        support=[{"quote": tail}]))
    result = _policy_result(content, review_input)
    assert result["findings"][0]["severity"] == "non-blocking"


def test_quote_beyond_file_cap_never_matches(monkeypatch):
    monkeypatch.setenv("AI_REVIEW_MAX_FILES", "1")
    content = _model_json("ISSUES_FOUND", _findings(
        file="b.py", support=[{"quote": QUOTE_B}]))
    result = _policy_result(content, _input())
    assert result["findings"][0]["severity"] == "non-blocking"


def test_quote_beyond_diff_truncation_never_matches(monkeypatch):
    # section a.py is 68 chars (28 header + 40 patch); max_diff 91
    # leaves 21 chars of b.py — inside the generated header — so b.py
    # contributes NO matchable segment and QUOTE_B cannot certify
    monkeypatch.setenv("AI_REVIEW_MAX_DIFF", "91")
    content = _model_json("ISSUES_FOUND", _findings(
        file="b.py", support=[{"quote": QUOTE_B}]))
    result = _policy_result(content, _input())
    assert result["findings"][0]["severity"] == "non-blocking"
    assert result["findings"][0]["comment"].endswith(
        engine.support_downgrade_note("support_not_found"))


def test_header_cut_contributes_no_segment_but_patch_prefix_survives(
        monkeypatch):
    # inverse pair pinned per #48 review: generated header alone ->
    # downgrade; actual patch bytes visible before truncation -> support
    monkeypatch.setenv("AI_REVIEW_MAX_DIFF", "133")  # 35 patch bytes visible
    content = _model_json("ISSUES_FOUND", _findings(file="b.py", support=[
        {"quote": HEADER_B.strip()},            # framing -> downgrade
        {"quote": "omega handler configu"},     # visible prefix -> survives
    ]))
    result = _policy_result(content, _input())
    items = result["findings"][0]["support"]
    assert "engine_match" not in items[0]
    assert items[1]["engine_match"] == {"kind": "diff", "id": "b.py"}
    assert result["findings"][0]["severity"] == "blocking"


def test_quote_inside_cut_header_matches_nothing(monkeypatch):
    monkeypatch.setenv("AI_REVIEW_MAX_DIFF", "91")  # kept 21 <= header 28
    content = _model_json("ISSUES_FOUND", _findings(
        file="b.py", support=[{"quote": "----- b.py (modified)"}]))
    result = _policy_result(content, _input())
    assert result["findings"][0]["severity"] == "non-blocking"


# ---- anti-vacuity floor (frozen: >= 16 normalized chars, >= 3 tokens) --------

def test_vacuous_quotes_never_certify():
    for quote in ("if", "a", "!!!", "return", "aa bb ccccccccc",  # 15 ch/3 tok
                  "ab cccccccccccccc"):                           # 16 ch/2 tok
        content = _model_json("ISSUES_FOUND", _findings(
            support=[{"quote": quote}]))
        result = _policy_result(content, _input())
        assert result["findings"][0]["severity"] == "non-blocking", quote


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
    third = "@@ -1 +1 @@\n+third section text"
    base = [
        {"path": "a.py", "status": "modified", "patch": PATCH_A},
        {"path": "b.py", "status": "modified", "patch": PATCH_B},
        {"path": "c.py", "status": "modified", "patch": third},
    ]
    cases = [
        ({}, _input(files=base)),                                   # no cap
        ({"AI_REVIEW_MAX_DIFF": "91"}, _input(files=base)),         # cut in hdr
        ({"AI_REVIEW_MAX_DIFF": "133"}, _input(files=base)),        # cut mid-b
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
        # model-visible diff text (budget identity, containment form);
        # segments are patch bytes only — no generated headers
        for kind, ident, text in got["segments"]:
            if kind == "diff":
                assert text in want[1], (env, ident)
                assert text.startswith("----- ") is False, (env, ident)
        # drift regression: the title/body MATCHABLE segments are the
        # exact effective fields the prompt is built from — a future
        # budget change cannot update one consumer without the other
        by_kind = {kind: text for kind, _, text in got["segments"]}
        assert by_kind["title"] == got["title"], env
        assert by_kind["body"] == got["body"], env
        assert got["body"] == review_input["body"][:2000], env


def test_prompt_title_and_body_come_from_effective_input():
    # the prompt embeds exactly the effective title/body — the same
    # fields the validator matches against (single source of truth)
    review_input = _input(
        title="The title",
        body="short line " * 180 + "TAILSENTINEL beyond budget")
    eff = engine.effective_review_input(review_input)
    _, user_prompt = engine._build_prompts(review_input)
    assert ("title", "", eff["title"]) in eff["segments"]
    assert ("body", "", eff["body"]) in eff["segments"]
    assert eff["body"] == review_input["body"][:2000]
    assert eff["title"] in user_prompt
    assert eff["body"] in user_prompt
    assert "TAILSENTINEL beyond budget" not in user_prompt


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
    assert all(f["severity"] in SEVERITIES for f in result["findings"])
    assert set(result) == {"schema_version", "assessment", "findings",
                           "summary", "good", "usage", "raw_output"}


def test_run_review_applies_support_policy_demoted(monkeypatch):
    _stub(monkeypatch, _model_json("ISSUES_FOUND", _findings(
        support="absent")))
    result = engine.run_review(_input())
    assert result["assessment"] == "CLEAR"
    assert result["findings"][0]["severity"] == "non-blocking"
    assert all(f["severity"] in SEVERITIES for f in result["findings"])
    assert result["findings"][0]["comment"].endswith(
        engine.support_downgrade_note("support_missing"))
