"""Transport-layer tests: model profiles, request shape, response-
envelope classification, and reason-coded INCONCLUSIVE payloads.

Encodes the transport/semantics boundary (2026-09-17):
- transport.py owns the OpenRouter ENVELOPE (terminal states, request
  shape from reviewed profiles, diagnostics) and never judges review
  content;
- parse_review.py stays the sole owner of INCONCLUSIVE semantics;
  PARSE_REASON on stderr is additive diagnostics;
- the default profile reproduces the legacy request EXACTLY — the
  haiku path is locked byte-for-byte;
- the structured-output schema mirrors the parse contract (no second
  definition of validity);
- terminal-state fixtures are saved from the observed GLM failure
  classes (reasoning-only null content, truncated partial content).
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import transport  # noqa: E402
from parse_review import (  # noqa: E402
    MODEL_ASSESSMENTS,
    SEVERITIES,
    build_payload,
)

TOOLKIT_ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "openrouter"


def fixture(name):
    with open(FIXTURES / name) as fh:
        return json.load(fh)


# ---- profiles: reviewed configuration -------------------------------------

def test_unknown_model_falls_back_to_default_profile():
    p = transport.load_profile("anthropic/claude-haiku-4.5")
    assert p == transport.load_profiles()["default"]


def test_default_profile_is_legacy_request():
    body = transport.build_request_body(
        "anthropic/claude-haiku-4.5", "sys", "user",
        transport.load_profile("anthropic/claude-haiku-4.5"))
    assert set(body) == {"model", "temperature", "max_tokens", "messages"}
    assert body["max_tokens"] == 2000 and body["temperature"] == 0.2


def test_glm_profile_adds_reasoning_schema_and_provider_requirement():
    body = transport.build_request_body(
        "z-ai/glm-5.3-flash", "sys", "user",
        transport.load_profile("z-ai/glm-5.3-flash"))
    # 'low': the slug supports low/high/max — unsupported values fall
    # back to max reasoning and recreate the exhaustion failure.
    assert body["reasoning"] == {"effort": "low"}
    assert body["max_tokens"] == 8000
    assert body["provider"] == {"require_parameters": True}
    rf = body["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["strict"] is True
    assert rf["json_schema"]["name"] == "review_result"


def test_budget_escalation_only_changes_max_tokens():
    body = transport.build_request_body(
        "z-ai/glm-5.3-flash", "sys", "user",
        transport.load_profile("z-ai/glm-5.3-flash"), max_tokens=16000)
    assert body["max_tokens"] == 16000
    assert body["reasoning"] == {"effort": "low"}  # effort stays fixed


# ---- envelope classification ----------------------------------------------

def test_reasoning_only_null_content_is_no_content():
    facts = transport.classify_response(fixture("glm_reasoning_only.json"))
    assert facts["state"] == "NO_CONTENT"
    assert facts["finish_reason"] == "length"
    assert facts["reasoning_tokens"] == 2000
    assert facts["provider"] == "baseten"


def test_truncated_partial_content_classifies_with_length_finish():
    facts = transport.classify_response(fixture("glm_partial_truncated.json"))
    assert facts["state"] == "OK_CONTENT"  # parse_review judges content
    assert facts["finish_reason"] == "length"


def test_valid_response_is_ok_content():
    facts = transport.classify_response(fixture("glm_valid.json"))
    assert facts["state"] == "OK_CONTENT"
    assert facts["finish_reason"] == "stop"


def test_refusal_is_its_own_state():
    facts = transport.classify_response(fixture("refusal.json"))
    assert facts["state"] == "REFUSAL"


def test_error_envelope_is_malformed():
    facts = transport.classify_response(fixture("error_envelope.json"))
    assert facts["state"] == "MALFORMED"


# ---- schema mirrors the parse contract (single source of validity) -----

def test_schema_enums_match_parser_contract():
    schema = transport.load_schema()["schema"]["properties"]
    assert schema["assessment"]["enum"] == list(MODEL_ASSESSMENTS)
    assert schema["findings"]["items"]["properties"]["severity"]["enum"] \
        == list(SEVERITIES)
    item = schema["findings"]["items"]
    assert set(item["required"]) == \
        {"file", "line", "severity", "comment", "suggestion"}


def test_schema_is_strict_closed_world():
    schema = transport.load_schema()
    assert schema["strict"] is True
    inner = schema["schema"]
    assert inner["additionalProperties"] is False
    assert set(inner["required"]) == \
        {"assessment", "summary", "findings", "good"}


# ---- escalation + failure policy (the recovery contract) -----------------

def test_escalation_applies_to_truncated_partial_content():
    """Regression: finish_reason=length WITH partial content is the
    same budget exhaustion as content-null and must get the same 2x
    recovery attempt, not go straight to parse-and-relabel."""
    facts = transport.classify_response(fixture("glm_partial_truncated.json"))
    profile = transport.load_profile("z-ai/glm-5.3-flash")
    assert transport.escalation_decision(facts, profile) is True


def test_escalation_is_length_and_profile_gated():
    profile = transport.load_profile("z-ai/glm-5.3-flash")
    default = transport.load_profiles()["default"]
    assert transport.escalation_decision(
        {"finish_reason": "stop"}, profile) is False
    assert transport.escalation_decision(  # default profile: no escalation
        {"finish_reason": "length"}, default) is False
    assert transport.escalation_decision(
        {"finish_reason": "length", "state": "NO_CONTENT"}, profile) is True


def test_failure_reason_mapping_contract():
    code, _ = transport.failure_reason({"state": "NO_CONTENT",
                                        "finish_reason": "length"})
    assert code == "OUTPUT_BUDGET_EXHAUSTED"
    code, _ = transport.failure_reason({"state": "NO_CONTENT",
                                        "finish_reason": "stop"})
    assert code == "NO_FINAL_CONTENT"
    code, detail = transport.failure_reason({"state": "REFUSAL"})
    assert code == "UPSTREAM_ERROR" and "content_filter" in detail
    # explicit contract: malformed envelope is UPSTREAM_ERROR, folded
    # nowhere else
    code, detail = transport.failure_reason({"state": "MALFORMED"})
    assert code == "UPSTREAM_ERROR" and "malformed" in detail


# ---- reason-coded INCONCLUSIVE (additive; parser stays owner) ----------

def test_transport_inconclusive_payload_is_comment_failclosed():
    payload = transport.inconclusive_payload(
        "z-ai/glm-5.3-flash", "abc123", "OUTPUT_BUDGET_EXHAUSTED",
        "The model exhausted its generation budget.")
    assert payload["event"] == "COMMENT"
    assert payload["comments"] == []
    assert payload["commit_id"] == "abc123"
    assert "## AI review · Inconclusive" in payload["body"]
    assert "Reason code: OUTPUT_BUDGET_EXHAUSTED" in payload["body"]
    assert "Do not treat this review as clear." in payload["body"]


def test_parse_reason_semantic_contradiction(capsys):
    content = json.dumps({
        "assessment": "ISSUES_FOUND",
        "findings": [{"file": "a.py", "comment": "x",
                      "severity": "non-blocking"}]})
    payload = build_payload(content, [], "abc", "m")
    assert "· Inconclusive" in payload["body"]
    assert "PARSE_REASON: SEMANTIC_CONTRADICTION" in capsys.readouterr().err


def test_parse_reason_structured_invalid(capsys):
    payload = build_payload("not json at all", [], "abc", "m")
    assert "· Inconclusive" in payload["body"]
    err = capsys.readouterr().err
    assert "PARSE_REASON: STRUCTURED_OUTPUT_INVALID" in err
