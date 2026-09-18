#!/usr/bin/env python3
"""Measurement-only reasoning-profile qualification driver (Stage A).

Q0 contract — ZERO model calls by default:
    python3 eval/profile_qualification.py --dry-run --reasoning-effort low
builds and pins every request and the planned-spend bounds without a
single network connection. Live mode additionally requires --live AND
the environment gate PM_QUALIFY_LIVE_AUTHORIZED=1 (explicit human
spend authorization; never implied by a merge).

Boundary discipline (why this file is small):
- ORACLE: the repaired corpus/harness/states are imported, never
  modified; this module is NOT an oracle input (oracle_version hashes
  eval/run_corpus.py + fixtures + states.json only) so adding it must
  not move the oracle identity — asserted by tests.
- SUBJECT: reviewer prompts are engine._build_prompts (imported, one
  source), rubric comes from the subject checkout, normalization is
  the subject parse_review. No prompt/rubric/semantics edits here.
- TRANSPORT: request shape, envelope classification, escalation
  policy and failure taxonomy are transport.py's (imported, one
  source). The only new logic here is measurement plumbing:
  effort/budget overrides, attempt accounting, telemetry.

Measurement-only overrides exist here and in evidence artifacts; they
never touch model_profiles.json or the deployed workflow contract.

ReviewResult shape note: on this branch the oracle consumes
parse_review-shaped ReviewResults. A transport-level generation
failure therefore becomes the parser's INCONCLUSIVE fragment (no
findings — never a detection) with the transport failure_reason
recorded as telemetry, never as review semantics.

Accounting vocabulary (never conflated):
- logical review      — one fixture x one run index: prompts + at
                        most one budget escalation = one verdict;
- provider generation — one HTTP 200 generation (initial or escalated);
- HTTP retry          — one extra raw attempt of the SAME generation
                        under engine._post_with_retries' legacy policy.
"""

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import transport  # noqa: E402
import eval.run_corpus as rc  # noqa: E402

ALLOWED_EFFORTS = ("low", "high", "max")
ORACLE_CHECKOUT_SHA = "4b116a7c7c4e9e78cddd362cd3ca4766aaf6ea25"
TRANSPORT_SHA = "b663bfd3139bb04a70f95d661c96ee150f534513"
ORACLE_VERSION = "9e20730cb0436002"
INCONCLUSIVE = "INCONCLUSIVE"


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def measurement_profile(model, reasoning_effort=None, max_tokens=None):
    """Deployed profile + measurement-only overrides, recorded.

    Overrides are explicit CLI intent, never persisted config. The
    returned record carries the base profile so every artifact shows
    exactly what was measured on top of what is deployed.
    """
    base = transport.load_profile(model)
    profile = dict(base)
    overrides = {}
    if reasoning_effort is not None:
        if reasoning_effort not in ALLOWED_EFFORTS:
            raise SystemExit(
                "--reasoning-effort must be one of %s, got %r"
                % (", ".join(ALLOWED_EFFORTS), reasoning_effort))
        profile["reasoning_effort"] = reasoning_effort
        overrides["reasoning_effort"] = reasoning_effort
    if max_tokens is not None:
        if int(max_tokens) <= 0:
            raise SystemExit("--max-tokens must be positive")
        profile["max_tokens"] = int(max_tokens)
        overrides["max_tokens"] = int(max_tokens)
    return profile, {"base_profile": base, "overrides": overrides}


def build_initial_request(engine, review_input, model, profile):
    """One source of prompts (engine) and request shape (transport)."""
    system, user = engine._build_prompts(review_input)
    body = transport.build_request_body(
        model, system, user, profile, max_tokens=profile["max_tokens"])
    return system, user, body


def _classify(raw_body):
    return transport.classify_response(json.loads(raw_body))


def _tokens(facts):
    return {
        "prompt_tokens": facts.get("prompt_tokens"),
        "completion_tokens": facts.get("completion_tokens"),
        "reasoning_tokens": facts.get("reasoning_tokens"),
    }


def _inconclusive_result():
    """The parser's INCONCLUSIVE ReviewResult fragment (no findings —
    a generation failure must never look like a detection)."""
    return {"schema_version": 1, "assessment": INCONCLUSIVE,
            "findings": [], "summary": "", "good": []}


def logical_review(engine, fixture, run_index, model, profile,
                   overrides, post_payload, sink):
    """One logical review through the #70 transport semantics.

    post_payload(body) -> (raw_body, http_retries, latency_s); it may
    raise SystemExit on infrastructure exhaustion (the legacy
    fail-closed policy: a dead network never masquerades as a
    generation verdict) — the partial record is sunk first, then the
    exit propagates. In dry-run post_payload is None and only the
    initial request is constructed.
    """
    review_input = rc._review_input(fixture, model, subject_dir=str(ROOT))
    system, user, body = build_initial_request(
        engine, review_input, model, profile)
    record = {
        "fixture": fixture["id"],
        "run_index": run_index,
        "model": model,
        "reasoning_effort": profile["reasoning_effort"],
        "initial_max_tokens": profile["max_tokens"],
        "base_profile": overrides["base_profile"],
        "overrides": overrides["overrides"],
        "prompt_sha256": [_sha(system), _sha(user)],
        "prompt_chars": [len(system), len(user)],
        "attempts": [],
        "http_retries": 0,
        "escalated": False,
        "reason_code": None,
        "failure_detail": None,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0,
                  "reasoning_tokens": 0},
        "wall_s": 0.0,
        "terminal_state": None,
        "result": None,
    }
    t0 = time.monotonic()

    def attempt(kind, max_tokens):
        try:
            raw, retries, latency = post_payload(
                transport.build_request_body(
                    model, system, user, profile, max_tokens=max_tokens))
        except SystemExit:
            record["terminal_state"] = "TRANSPORT_FAILURE"
            record["wall_s"] = round(time.monotonic() - t0, 3)
            sink(record)
            raise
        facts = _classify(raw)
        record["attempts"].append({
            "kind": kind,
            "max_tokens": max_tokens,
            "finish_reason": facts.get("finish_reason"),
            "state": facts.get("state"),
            "provider": facts.get("provider"),
            "latency_s": latency,
            **_tokens(facts),
        })
        record["http_retries"] += retries
        return facts, raw

    if post_payload is None:
        record["terminal_state"] = "DRY_RUN"
        record["escalation_planned"] = bool(
            profile["retry_budget_escalation"])
        record["request_sha256"] = _sha(json.dumps(body, sort_keys=True))
        sink(record)
        return record

    facts, raw = attempt("initial", profile["max_tokens"])
    if transport.escalation_decision(facts, profile):
        record["escalated"] = True
        facts, raw = attempt("escalated", profile["max_tokens"] * 2)
    final = record["attempts"][-1]
    record["usage"] = _tokens(facts)

    if final["state"] == "OK_CONTENT":
        content = json.loads(raw)["choices"][0]["message"]["content"]
        result = engine.normalize(content)
        if result["assessment"] == INCONCLUSIVE \
                and final["finish_reason"] == "length":
            record["reason_code"] = "OUTPUT_BUDGET_EXHAUSTED"
            record["failure_detail"] = (
                "parser rejected truncated output; transport root "
                "cause: finish_reason length (transport.failure_reason "
                "taxonomy; telemetry only)")
    else:
        reason_code, detail = transport.failure_reason(facts)
        record["reason_code"] = reason_code
        record["failure_detail"] = detail
        result = _inconclusive_result()
    record["terminal_state"] = final["state"]
    record["result"] = result
    record["wall_s"] = round(time.monotonic() - t0, 3)
    sink(record)
    return record


_SUBJECT_SHA_CACHE = {}


def subject_sha():
    """The reviewer-subject commit this checkout measures."""
    if "sha" not in _SUBJECT_SHA_CACHE:
        _SUBJECT_SHA_CACHE["sha"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            check=True, cwd=str(ROOT)).stdout.strip()
    return _SUBJECT_SHA_CACHE["sha"]


def load_subject_engine(subject_dir=None):
    """Import the subject's engine (same seam as run_corpus)."""
    base = (pathlib.Path(subject_dir).resolve() if subject_dir
            else ROOT).resolve()
    if base == ROOT:
        import engine
        return engine
    sys.path.insert(0, str(base))
    for mod in ("engine", "parse_review"):
        sys.modules.pop(mod, None)
    import engine  # noqa: F811
    return engine


def corpus():
    return rc.load_corpus(ROOT / "eval" / "fixtures")


def planned_bounds(fixtures, runs, model, profile):
    logical = len(fixtures) * runs
    escalatable = bool(profile["retry_budget_escalation"])
    return {
        "model": model,
        "reasoning_effort": profile["reasoning_effort"],
        "initial_max_tokens": profile["max_tokens"],
        "fixtures": len(fixtures),
        "runs_per_fixture": runs,
        "logical_reviews": logical,
        "max_provider_generations": logical * (2 if escalatable else 1),
        "max_output_tokens": logical * profile["max_tokens"]
                             * (3 if escalatable else 1),
        "note": "output bound is conservative: an escalated generation "
                "doubles its budget and the bound assumes every logical "
                "review escalates",
    }


def _meta(agg, fixtures, runs, model, profile):
    meta = dict(agg or {})
    meta.update({
        "oracle_checkout_sha": ORACLE_CHECKOUT_SHA,
        "oracle_version": rc.oracle_version(),
        "subject_sha": subject_sha(),
        "transport_sha": TRANSPORT_SHA,
        "rubric_sha256": _sha((ROOT / "rubric.md").read_text()),
        "corpus_sha256": rc.corpus_hash(fixtures),
        "model": model,
        "reasoning_effort": profile["reasoning_effort"],
        "budget": profile["max_tokens"],
        "N": runs,
    })
    return meta


def _write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def dry_run(out_dir, fixtures, runs, model, profile, overrides):
    """Q0 mode: construct every unique request; touch no network."""
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = load_subject_engine()
    records = []
    for fixture in fixtures:
        rec = logical_review(engine, fixture, 0, model, profile,
                             overrides, None, sink=lambda r: None)
        records.append(rec)
        if rec["fixture"] != fixture["id"]:
            raise SystemExit("fixture id mismatch during dry run")
    (out_dir / "requests.json").write_text(
        json.dumps({"model": model, "profile": profile,
                    "overrides": overrides, "runs_planned": runs,
                    "records": records}, indent=2, sort_keys=True) + "\n")
    _write_json(out_dir / "planned_bounds.json",
                planned_bounds(fixtures, runs, model, profile))
    _write_json(out_dir / "meta.json",
                _meta({}, fixtures, runs, model, profile))
    return out_dir


def engine_http(engine):
    """Production-faithful HTTP attempt via the subject engine.

    Wraps engine._post_chat ONLY to count raw attempts of THIS
    provider generation; the retry policy itself is
    engine._post_with_retries, unchanged (one source). The counted
    wrapper is installed and restored around EVERY post_payload
    invocation, so escalation generations and later logical reviews
    each count their own raw attempts.
    Returns (raw_body, http_retries, latency_s).
    """
    original = engine._post_chat

    def post_payload(body):
        local = {"attempts": 0}

        def counted(payload):
            local["attempts"] += 1
            return original(payload)

        engine._post_chat = counted
        t0 = time.monotonic()
        try:
            _, _, raw = engine._post_with_retries(body, "qualification")
        finally:
            engine._post_chat = original
        return raw, local["attempts"] - 1, round(time.monotonic() - t0, 3)

    return post_payload


REDUCER_FIELDS = (
    "logical_reviews", "provider_generations", "http_retries",
    "prompt_tokens", "completion_tokens", "reasoning_tokens",
    "length_exhaustions", "escalations", "post_escalation_exhaustions",
    "final_inconclusive", "transport_failures", "wall_s",
)


def reduce_records(records):
    """The ONE aggregation: complete campaign state from persisted
    records (records.jsonl is the source of truth). Used for every
    summary.json — final and intermediate — so a resumed campaign
    reports the whole campaign, not just the suffix. Deterministic:
    pure function of the record list; floats are rounded to defeat
    order-dependent last-ulp drift."""
    agg = {field: 0 for field in REDUCER_FIELDS}
    seen = set()
    halted = False
    for r in records:
        if r.get("terminal_state") == "TRANSPORT_FAILURE":
            agg["transport_failures"] += 1
            halted = True
            continue
        key = (r["fixture"], r["run_index"])
        if key in seen:
            raise SystemExit(
                "duplicate completed review key %r in records.jsonl "
                "(fail closed — evidence integrity)" % (key,))
        seen.add(key)
        agg["logical_reviews"] += 1
        agg["provider_generations"] += len(r["attempts"])
        agg["http_retries"] += r.get("http_retries") or 0
        for a in r["attempts"]:
            for k in ("prompt_tokens", "completion_tokens",
                      "reasoning_tokens"):
                agg[k] += a.get(k) or 0
            if a.get("finish_reason") == "length":
                agg["length_exhaustions"] += 1
                if a.get("kind") == "escalated":
                    agg["post_escalation_exhaustions"] += 1
        if r.get("escalated"):
            agg["escalations"] += 1
        if r.get("result") and \
                r["result"].get("assessment") == INCONCLUSIVE:
            agg["final_inconclusive"] += 1
        agg["wall_s"] += r.get("wall_s") or 0.0
    agg["wall_s"] = round(agg["wall_s"], 3)
    agg["campaign_halted"] = halted
    return agg


def _load_records(records_path):
    if not records_path.exists():
        return []
    return [json.loads(line) for line in
            records_path.read_text().splitlines() if line.strip()]


def _write_summary(out_dir, fixtures, runs, model, profile):
    records = _load_records(out_dir / "records.jsonl")
    _write_json(out_dir / "summary.json",
                _meta(reduce_records(records), fixtures, runs,
                      model, profile))


def live(out_dir, fixtures, runs, model, profile, overrides):
    if os.environ.get("PM_QUALIFY_LIVE_AUTHORIZED") != "1":
        raise SystemExit(
            "live measurement refused: set PM_QUALIFY_LIVE_AUTHORIZED=1 "
            "(explicit human spend authorization) and pass --live")
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = load_subject_engine()
    post_payload = engine_http(engine)
    records_path = out_dir / "records.jsonl"

    # Fail closed on evidence-integrity problems BEFORE running
    # anything: a persisted TRANSPORT_FAILURE is a campaign halt
    # under preregistered D1 — it is reported and stops pending
    # human direction, never silently retried; duplicate completed
    # (fixture, run_index) keys mean the log was tampered or
    # double-written — refuse.
    existing = _load_records(records_path)
    for r in existing:
        if r.get("terminal_state") == "TRANSPORT_FAILURE":
            raise SystemExit(
                "campaign halted: records.jsonl carries a "
                "TRANSPORT_FAILURE for (%s, run %s) — preregistered "
                "disqualifier D1 territory. Report and stop pending "
                "human direction; do not silently resume."
                % (r.get("fixture"), r.get("run_index")))
    done = set()
    for r in existing:
        key = (r["fixture"], r["run_index"])
        if key in done:
            raise SystemExit(
                "duplicate completed review key %r in records.jsonl "
                "(fail closed — evidence integrity)" % (key,))
        done.add(key)

    def sink(record):
        with records_path.open("a") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

    try:
        for fixture in fixtures:
            for run_index in range(runs):
                if (fixture["id"], run_index) in done:
                    continue
                logical_review(
                    engine, fixture, run_index, model, profile,
                    overrides, post_payload, sink)
    except SystemExit:
        _write_summary(out_dir, fixtures, runs, model, profile)
        raise
    _write_summary(out_dir, fixtures, runs, model, profile)
    return out_dir


def resolve_mode(args):
    """The mode gate — decided BEFORE any output or network exists.

    dry-run: --dry-run present, --live absent (no authorization
    needed — zero calls by construction);
    live:    --live present, --dry-run absent, AND
             PM_QUALIFY_LIVE_AUTHORIZED=1 (both gates required;
             the env var alone is NEVER sufficient);
    anything else: refused.
    """
    if args.dry_run and args.live:
        raise SystemExit("--dry-run and --live are mutually exclusive")
    if args.dry_run:
        return "dry-run"
    if args.live:
        if os.environ.get("PM_QUALIFY_LIVE_AUTHORIZED") != "1":
            raise SystemExit(
                "live measurement refused: --live requires "
                "PM_QUALIFY_LIVE_AUTHORIZED=1 (explicit human spend "
                "authorization)")
        return "live"
    raise SystemExit(
        "no mode selected: pass --dry-run (zero model calls) or "
        "--live together with PM_QUALIFY_LIVE_AUTHORIZED=1; an "
        "authorized env var without --live is deliberately NOT a "
        "live invocation")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default="z-ai/glm-5.3-flash")
    ap.add_argument("--reasoning-effort", choices=ALLOWED_EFFORTS,
                    default=None)
    ap.add_argument("--max-tokens", type=int, default=None)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--fixtures", default=None,
                    help="comma-separated fixture ids; default all")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true",
                    help="Q0: construct requests only; zero model calls")
    ap.add_argument("--live", action="store_true",
                    help="live mode; requires PM_QUALIFY_LIVE_AUTHORIZED=1")
    args = ap.parse_args(argv)
    mode = resolve_mode(args)
    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")
    profile, overrides = measurement_profile(
        args.model, args.reasoning_effort, args.max_tokens)
    fixtures = corpus()
    if args.fixtures:
        wanted = set(args.fixtures.split(","))
        fixtures = [f for f in fixtures if f["id"] in wanted]
        if not fixtures:
            raise SystemExit("no fixtures matched --fixtures")
    out_dir = pathlib.Path(args.out)
    if mode == "dry-run":
        dry_run(out_dir, fixtures, args.runs, args.model, profile, overrides)
    else:
        live(out_dir, fixtures, args.runs, args.model, profile, overrides)
    return 0


if __name__ == "__main__":
    sys.exit(main())
