#!/usr/bin/env python3
"""Inference transport helpers: model profiles, request shape, and
OpenRouter response-envelope classification.

Boundary (transport vs semantics):
- THIS module owns the OpenRouter response ENVELOPE: terminal states
  (complete / no final content / refusal / malformed envelope), the
  request shape derived from reviewed model profiles, and operational
  diagnostics (provider, finish_reason, token usage);
- parse_review.py owns SEMANTIC trust: whether model content is a
  usable review, and the INCONCLUSIVE verdict for malformed or
  self-contradictory output. This module never judges review content.
  A transport-level generation failure (no final content to parse)
  produces an explicit INCONCLUSIVE payload with a reason code — a
  mechanical observation about generation, not a semantic judgment.

Model profiles are REVIEWED CONFIGURATION, not runtime discovery:
model_profiles.json is versioned in this repo and travels with the
pinned toolkit_ref. Unknown model slugs resolve to the default
profile, which reproduces the legacy request exactly (max_tokens
2000, no reasoning control, no structured output) — the default
reviewer path is unchanged byte-for-byte.
"""

import json
import pathlib
import sys

TOOLKIT_DIR = pathlib.Path(__file__).resolve().parent


def load_profiles():
    with open(TOOLKIT_DIR / "model_profiles.json") as fh:
        return json.load(fh)["profiles"]


def load_profile(model):
    """Resolve a model slug to its profile; unknown slugs -> default."""
    profiles = load_profiles()
    profile = profiles.get(model, profiles["default"])
    for key in ("max_tokens", "reasoning_effort",
                "structured_output", "retry_budget_escalation"):
        if key not in profile:
            raise SystemExit("profile for %s missing key '%s'" % (model, key))
    return profile


def load_schema():
    with open(TOOLKIT_DIR / "review_result_schema.json") as fh:
        return json.load(fh)


def build_request_body(model, system, user, profile, max_tokens=None):
    """OpenRouter chat-completions body; legacy path when default."""
    body = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": int(max_tokens if max_tokens is not None
                          else profile["max_tokens"]),
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }
    if profile.get("reasoning_effort"):
        body["reasoning"] = {"effort": profile["reasoning_effort"]}
    if profile.get("structured_output"):
        body["response_format"] = {"type": "json_schema",
                                   "json_schema": load_schema()}
        body["provider"] = {"require_parameters": True}
    return body


def classify_response(resp):
    """Classify the OpenRouter response envelope into a terminal state.

    Returns a facts dict; never inspects or judges message content
    beyond its presence. States:
      OK_CONTENT — final content present (parse_review judges it);
      NO_CONTENT — 200 but no usable final content (e.g. reasoning
                   exhausted the completion budget: finish_reason
                   "length", content null);
      REFUSAL    — provider refused (finish_reason "content_filter");
      MALFORMED  — no choices array (error envelope).
    """
    choices = resp.get("choices") or []
    usage = resp.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    facts = {
        "finish_reason": None,
        "provider": resp.get("provider"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": details.get("reasoning_tokens"),
    }
    if not choices:
        facts["state"] = "MALFORMED"
        return facts
    choice = choices[0]
    message = choice.get("message") or {}
    content = message.get("content")
    facts["finish_reason"] = choice.get("finish_reason")
    if facts["finish_reason"] == "content_filter":
        facts["state"] = "REFUSAL"
    elif isinstance(content, str) and content.strip():
        facts["state"] = "OK_CONTENT"
    else:
        facts["state"] = "NO_CONTENT"
    return facts


def inconclusive_payload(model, head_sha, reason_code, detail):
    """Transport-generated INCONCLUSIVE review payload.

    Same external contract as parse_review's INCONCLUSIVE: COMMENT
    event, no inline comments, fail-closed wording. Carries a reason
    code so operational failures are distinguishable without dumping
    the model's reasoning trace.
    """
    body = "\n".join([
        "## AI review · Inconclusive",
        "",
        "A reliable semantic review could not be produced.",
        "",
        detail,
        "",
        "Do not treat this review as clear.",
        "",
        "<details>",
        "<summary>Technical details</summary>",
        "",
        "Reason code: %s" % reason_code,
        "",
        "</details>",
        "",
        "<details>\n<summary>Review metadata</summary>\n\n"
        "Reviewer: ci-toolkit\n"
        "Model: {0}\n"
        "Commit: {1}\n"
        "Assessment: INCONCLUSIVE\n\n"
        "</details>".format(model, head_sha),
    ])
    return {"commit_id": head_sha, "body": body,
            "event": "COMMENT", "comments": []}


def main(argv):
    usage = ("usage: transport.py profile MODEL\n"
             "       transport.py request MODEL SYSTEM_FILE USER_FILE"
             " [--max-tokens N]\n"
             "       transport.py classify RESPONSE_FILE\n"
             "       transport.py inconclusive HEAD_SHA MODEL"
             " REASON_CODE DETAIL\n")
    if len(argv) < 2:
        sys.stderr.write(usage)
        return 2
    cmd = argv[1]
    if cmd == "profile" and len(argv) == 3:
        print(json.dumps(load_profile(argv[2])))
        return 0
    if cmd == "request" and len(argv) in (5, 7):
        max_tokens = None
        if len(argv) == 7:
            if argv[5] != "--max-tokens":
                sys.stderr.write(usage)
                return 2
            max_tokens = int(argv[6])
        with open(argv[3]) as fh:
            system = fh.read()
        with open(argv[4]) as fh:
            user = fh.read()
        print(json.dumps(build_request_body(
            argv[2], system, user, load_profile(argv[2]), max_tokens)))
        return 0
    if cmd == "classify" and len(argv) == 3:
        with open(argv[2]) as fh:
            print(json.dumps(classify_response(json.load(fh))))
        return 0
    if cmd == "inconclusive" and len(argv) == 6:
        print(json.dumps(inconclusive_payload(argv[3], argv[2],
                                              argv[4], argv[5])))
        return 0
    sys.stderr.write(usage)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
