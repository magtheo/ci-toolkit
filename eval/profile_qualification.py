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
import math
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
ORACLE_VERSION = "117b4164e5446f50"
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
                   overrides, post_payload, sink, spend_guard=None,
                   ledger=None, evidence_gate=False):
    """One logical review through the #70 transport semantics.

    post_payload(body) -> (raw_body, http_retries, latency_s); it may
    raise SystemExit on infrastructure exhaustion (the legacy
    fail-closed policy: a dead network never masquerades as a
    generation verdict) — the partial record is sunk first, then the
    exit propagates. In dry-run post_payload is None and only the
    initial request is constructed.

    When `ledger` (SpendLedger) is given, EVERY generation reserves
    its worst-case bound from the shared aggregate ceiling BEFORE the
    request and settles actual usage (or the reserved amount when
    usage is unknown — fail closed) afterwards.
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
        if spend_guard is not None:
            spend_guard.check(fixture["id"], max_tokens)
        if ledger is not None:
            reservation = ledger.reserve(fixture["id"], max_tokens)
        try:
            raw, retries, latency = post_payload(
                transport.build_request_body(
                    model, system, user, profile, max_tokens=max_tokens))
        except SystemExit:
            if ledger is not None:
                # process is about to die on transport exhaustion:
                # settle at the reserved amount (fail closed) so the
                # shared ledger never strands this budget
                ledger.settle(reservation, None)
            record["terminal_state"] = "TRANSPORT_FAILURE"
            record["wall_s"] = round(time.monotonic() - t0, 3)
            sink(record)
            raise
        facts = _classify(raw)
        if spend_guard is not None:
            spend_guard.add(facts)
        if ledger is not None:
            # usage is trusted only when COMPLETE (all required fields
            # present, positive input count) — settle() enforces the
            # same rule; anything partial settles at the reserved
            # amount, never at zero
            required = ("prompt_tokens", "completion_tokens",
                        "reasoning_tokens")
            known = (all(facts.get(k) is not None for k in required)
                     and (facts.get("prompt_tokens") or 0) > 0)
            ledger.settle(reservation, facts if known else None)
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
        # raw model output is preserved next to the normalized result
        # so any evidence-gate decision is auditable after the fact
        record["raw_model_output"] = content
        if evidence_gate:
            import parse_review
            diff_files = {f["path"]: f["patch"]
                          for f in fixture["input"]["files"]}
            result, gate_audit = parse_review.normalize_v2(
                content, diff_files, gate=True)
            record["evidence_gate"] = {"enabled": True,
                                       "audit": gate_audit}
        else:
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


SUBJECT_IDENTITY_FILES = ("engine.py", "parse_review.py", "render.py",
                          "rubric.md")
TRANSPORT_IDENTITY_FILES = ("transport.py", "model_profiles.json",
                            "review_result_schema.json")


def _content_ref(files):
    """Content identity: sha256 over the sorted (name, bytes) of the
    given files. Content hashes, not commit SHAs — valid on any
    checkout including shallow CI, and they move the moment the file
    content moves (provenance constants alone would not)."""
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(rel.encode("utf-8"))
        h.update((ROOT / rel).read_bytes())
    return h.hexdigest()


def subject_content_ref():
    return _content_ref(SUBJECT_IDENTITY_FILES)


def transport_content_ref():
    """Runtime content identity of the transport trio. TRANSPORT_SHA
    is provenance (which PR reviewed this transport); this ref proves
    the CURRENT bytes still are that transport — plan stop-condition
    'transport byte drift' is detectable at resume time."""
    return _content_ref(TRANSPORT_IDENTITY_FILES)


def campaign_identity(model, profile, runs):
    """Everything a persisted evidence set must match to be resumed:
    profile under measurement + oracle/subject/transport identity.
    Written once per output directory BEFORE the first record;
    compared exactly on every resume — a mismatch refuses before any
    provider call, so a low/8k directory can never be silently
    continued as high/8k."""
    fixtures = corpus()
    return {
        "model": model,
        "reasoning_effort": profile["reasoning_effort"],
        "initial_max_tokens": profile["max_tokens"],
        "N": runs,
        "oracle_version": rc.oracle_version(),
        "oracle_checkout_sha": ORACLE_CHECKOUT_SHA,
        "subject_content_ref": subject_content_ref(),
        "transport_sha": TRANSPORT_SHA,
        "transport_content_ref": transport_content_ref(),
        "rubric_sha256": _sha((ROOT / "rubric.md").read_text()),
        "corpus_sha256": rc.corpus_hash(fixtures),
    }


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


class SpendCeilingReached(Exception):
    """Raised BEFORE a provider request when the campaign's hard
    spend ceiling could not be respected within the worst-case bound
    of the next generation. Not a transport failure and not a
    campaign-halt D1 record: the evidence set stays resumable and
    the next move is the human's."""


class SpendGuard:
    """Hard spend ceiling, enforced BEFORE every provider request.

    Cost model (conservative): input = prompt_tokens; output =
    completion_tokens + reasoning_tokens. If a provider already
    includes reasoning in completion_tokens this OVER-counts output
    — safe for a ceiling, never under-counts.

    Pre-request bound per generation: est_input = ceil(prompt_chars
    / 4) x SAFETY (chars/4 heuristic, doubled) + generation budget
    as output. The request is made only if
    cumulative_actual + worst_case_next <= ceiling."""

    SAFETY = 2

    def __init__(self, ceiling_usd, price_in_per_m, price_out_per_m,
                 prompt_chars_by_fixture):
        self.ceiling = float(ceiling_usd)
        self.p_in = float(price_in_per_m)
        self.p_out = float(price_out_per_m)
        self.chars = prompt_chars_by_fixture
        self.in_tokens = 0
        self.out_tokens = 0
        self.generations = 0

    @property
    def cost_usd(self):
        return self.cost_usd_of(self.in_tokens, self.out_tokens)

    def cost_usd_of(self, in_tokens, out_tokens):
        return ((in_tokens * self.p_in
                 + out_tokens * self.p_out) / 1e6)

    def _est_input(self, fixture_id):
        return math.ceil(self.chars[fixture_id] / 4) * self.SAFETY

    def check(self, fixture_id, gen_budget):
        est_in = self._est_input(fixture_id)
        worst = (est_in * self.p_in + gen_budget * self.p_out) / 1e6
        if self.cost_usd + worst > self.ceiling:
            raise SpendCeilingReached(
                "spend ceiling reached: actual $%.4f + worst-case "
                "next generation $%.4f > ceiling $%.2f — halting "
                "BEFORE the request; the campaign is resumable "
                "pending human direction"
                % (self.cost_usd, worst, self.ceiling))

    def add(self, facts):
        self.in_tokens += facts.get("prompt_tokens") or 0
        self.out_tokens += ((facts.get("completion_tokens") or 0)
                            + (facts.get("reasoning_tokens") or 0))
        self.generations += 1

    def state(self):
        return {
            "price_source": getattr(self, "price_source", None),
            "spend_ceiling_usd": self.ceiling,
            "price_input_per_1m": self.p_in,
            "price_output_per_1m": self.p_out,
            "input_tokens": self.in_tokens,
            "output_tokens_incl_reasoning": self.out_tokens,
            "provider_generations_billed": self.generations,
            "actual_cost_usd": round(self.cost_usd, 6),
            "ceiling_remaining_usd": round(self.ceiling - self.cost_usd, 6),
            "cost_model": "input=prompt_tokens; "
                          "output=completion+reasoning (over-counts "
                          "if provider includes reasoning in "
                          "completion); pre-request worst case uses "
                          "ceil(chars/4)x%d input + full generation "
                          "budget output" % self.SAFETY,
        }


def _load_records(records_path):
    if not records_path.exists():
        return []
    return [json.loads(line) for line in
            records_path.read_text().splitlines() if line.strip()]


def _spend_from_records(records, guard):
    """Authoritative per-effort spend, derived from the PERSISTED
    records — every attempt of every record, because every attempt
    bills (Phase-08 repair of the B1 accounting discrepancy: the
    process-local guard is a fresh accumulator per invocation, so a
    resumed / multi-invocation out_dir made its cumulative totals
    silently wrong — B1's summaries under-reported by ~3x). The guard
    remains the pre-request ceiling checker only; the shared ledger
    stays the authoritative hard-ceiling instrument."""
    in_tok = out_tok = generations = 0
    for r in records:
        for a in r.get("attempts", []):
            generations += 1
            in_tok += a.get("prompt_tokens") or 0
            out_tok += ((a.get("completion_tokens") or 0)
                        + (a.get("reasoning_tokens") or 0))
    cost = guard.cost_usd_of(in_tok, out_tok)
    return {
        "price_source": getattr(guard, "price_source", None),
        "spend_ceiling_usd": guard.ceiling,
        "price_input_per_1m": guard.p_in,
        "price_output_per_1m": guard.p_out,
        "input_tokens": in_tok,
        "output_tokens_incl_reasoning": out_tok,
        "provider_generations_billed": generations,
        "actual_cost_usd": round(cost, 6),
        "ceiling_remaining_usd": round(guard.ceiling - cost, 6),
        "cost_model": "input=prompt_tokens; "
                      "output=completion+reasoning (over-counts "
                      "if provider includes reasoning in "
                      "completion); tokens summed from "
                      "records.jsonl attempts (known usage only — "
                      "usage-unknown attempts settle at reserved "
                      "amounts in the ledger, which stays the "
                      "fail-closed ceiling authority)",
        "source": "records.jsonl (all attempts) — deterministic "
                  "Phase-08 repair; per-invocation guard totals are "
                  "NOT effort totals",
    }


def _write_summary(out_dir, fixtures, runs, model, profile, spend=None,
                   ledger=None):
    records = _load_records(out_dir / "records.jsonl")
    meta = _meta(reduce_records(records), fixtures, runs,
                 model, profile)
    if spend is not None:
        meta["spend"] = (_spend_from_records(records, spend)
                         if records else spend.state())
    if ledger is not None:
        meta.setdefault("spend", {})["aggregate_ledger"] = ledger.state()
    _write_json(out_dir / "summary.json", meta)


AGGREGATE_DETECTION_DEFINITION = (
    "sum over positive fixtures and runs of "
    "run_detects_all_groups(groups, result); denominator is "
    "(number of positive fixtures) x N — 18 x 3 = 54 at Stage A. "
    "The historical 51/90 (haiku) and 66/90 (sonnet) floors are "
    "methodological CONTEXT, not numerically comparable thresholds: "
    "they aggregate different populations/denominators and must not "
    "be normalized onto this metric without a governed rule. "
    "rc.evaluate() remains authoritative for fixture pass/fail: "
    "per-group STABILITY ((N+2)//2 of N) is deliberately a "
    "different, stronger concept than run-level detection.")


def stage_a_report(records, runs):
    """Deterministic Stage-A reduction: records.jsonl -> oracle
    metrics + hard-disqualifier results + the lexicographic
    selection tuple. NO oracle semantics are reimplemented — each
    fixture's ReviewResults are reconstructed from the persisted
    records and fed through eval.run_corpus's evaluate(),
    pair_integrity() and the 25k group helpers, the same functions
    the harness and every frozen replay use."""
    fixtures = {f["id"]: f for f in corpus()}
    states = json.loads((ROOT / "eval" / "states.json").read_text())

    by_fixture = {}
    for r in records:
        if r.get("terminal_state") in (None, "TRANSPORT_FAILURE",
                                       "DRY_RUN"):
            continue
        by_fixture.setdefault(r["fixture"], {})[r["run_index"]] = \
            r["result"]
    per_fixture, missing_runs, fixtures_absent = [], [], []
    ordered_results = {}
    for fid in sorted(fixtures):
        runs_by_idx = by_fixture.get(fid, {})
        results = [runs_by_idx[i] for i in sorted(runs_by_idx)]
        ordered_results[fid] = results
        if not runs_by_idx:
            fixtures_absent.append(fid)
        elif set(runs_by_idx) != set(range(runs)):
            missing_runs.append({"fixture": fid,
                                 "present": sorted(runs_by_idx)})
        if results:
            per_fixture.append(rc.evaluate(fixtures[fid], results))

    gating_violations = [r["id"] for r in per_fixture
                         if states.get(r["id"]) == "GATING"
                         and not r["passes_policy"]]
    control_false_blocks = [
        {"id": r["id"], "false_blockers": r["false_blockers"],
         "assessments": r["assessments"]}
        for r in per_fixture
        if r["kind"] == "control" and r["false_blockers"]]
    pi_violations, promotion_eligible = rc.pair_integrity(per_fixture)

    positives = [f for f in fixtures.values() if f["kind"] == "positive"]
    detected = 0
    per_positive = {}
    per_group_hits = {}
    for fid in sorted(fixtures):
        f = fixtures[fid]
        results = ordered_results[fid]
        if not results:
            continue
        groups = f["expected"]["groups"]
        per_group_hits[fid] = rc.per_group_hits(groups, results)
        if f["kind"] == "positive":
            n_det = sum(1 for res in results
                        if rc.run_detects_all_groups(groups, res))
            per_positive[fid] = n_det
            detected += n_det

    fb_on_positives = sum(r["false_blockers"] for r in per_fixture
                          if r["kind"] == "positive")
    stability = {"CLEAR": 0, "ISSUES_FOUND": 0, "INCONCLUSIVE": 0}
    for r in per_fixture:
        for k in stability:
            stability[k] += r["assessment_stability"][k]

    transport = reduce_records(records)
    logical = transport["logical_reviews"]
    d1 = {
        "fired": bool(transport["transport_failures"])
                 or (logical > 0 and transport["final_inconclusive"]
                     / logical > 0.10),
        "final_inconclusive": transport["final_inconclusive"],
        "logical_reviews": logical,
        "transport_failures": transport["transport_failures"],
    }
    d2 = {"fired": bool(gating_violations),
          "gating_violations": gating_violations}
    d3 = {"fired": bool(control_false_blocks),
          "zero_tolerance": "any unexpected blocking finding on any "
                            "control run disqualifies (repaired-oracle "
                            "control semantics; no tolerance was "
                            "invented here)",
          "violations": control_false_blocks}
    esc = transport["escalations"]
    post_esc = transport["post_escalation_exhaustions"]
    d4 = {"fired": bool(esc and post_esc / esc > 0.05),
          "escalations": esc, "post_escalation_exhaustions": post_esc}

    output_tokens = (transport["completion_tokens"]
                     + transport["reasoning_tokens"])
    selection_tuple = [
        -detected, fb_on_positives, -len(promotion_eligible),
        output_tokens, transport["wall_s"]]

    return {
        "runs_requested": runs,
        "complete": not missing_runs and not fixtures_absent,
        "missing_runs": missing_runs,
        "fixtures_absent": fixtures_absent,
        "aggregate_positive_detection": {
            "definition": AGGREGATE_DETECTION_DEFINITION,
            "detected": detected,
            "denominator": len(positives) * runs,
            "per_positive": per_positive},
        "per_group_hits": per_group_hits,
        "false_blockers_on_positives": fb_on_positives,
        "assessment_stability": stability,
        "inconclusive_runs": stability["INCONCLUSIVE"],
        "gating_violations": gating_violations,
        "pair_integrity_violations": pi_violations,
        "promotion_eligible": promotion_eligible,
        "control_false_blocks": control_false_blocks,
        "transport": transport,
        "hard_disqualifiers": {"D1_transport_viability": d1,
                               "D2_gating_regression": d2,
                               "D3_control_false_block": d3,
                               "D4_post_escalation_exhaustion": d4},
        "selection_tuple": selection_tuple,
        "selection_tuple_order": (
            "[-aggregate_positive_detection, false_blockers_on_positives,"
            " -promotion_eligible, output_tokens, wall_s]; "
            "lexicographic among non-disqualified profiles"),
    }


def live(out_dir, fixtures, runs, model, profile, overrides,
         run_index=None, spend=None, ledger=None, evidence_gate=False):
    if os.environ.get("PM_QUALIFY_LIVE_AUTHORIZED") != "1":
        raise SystemExit(
            "live measurement refused: set PM_QUALIFY_LIVE_AUTHORIZED=1 "
            "(explicit human spend authorization) and pass --live")
    if spend is not None and not isinstance(spend, SpendGuard):
        raise SystemExit("spend must be a SpendGuard")
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = load_subject_engine()
    records_path = out_dir / "records.jsonl"
    existing = _load_records(records_path)

    # Campaign identity — READ the evidence set's history BEFORE
    # creating anything. An existing records.jsonl without
    # campaign.json must never be rebound to a freshly generated
    # identity (that would let old-subject/old-oracle records
    # acquire today's identity retroactively): refuse. Identity is
    # created only for an evidence set with zero records, and then
    # compared exactly on every resume — all before any provider
    # call.
    identity = campaign_identity(model, profile, runs)
    campaign_path = out_dir / "campaign.json"
    if campaign_path.exists():
        persisted = json.loads(campaign_path.read_text())
        if persisted != identity:
            diff = [k for k in sorted(set(persisted) | set(identity))
                    if persisted.get(k) != identity.get(k)]
            raise SystemExit(
                "campaign identity mismatch in %s (differing fields: "
                "%s) — refusing to mix profiles in one evidence set; "
                "use a fresh --out directory for the new profile"
                % (campaign_path, ", ".join(diff)))
    elif existing:
        raise SystemExit(
            "records.jsonl exists without campaign.json — refusing to "
            "rebind an existing evidence set to a freshly generated "
            "campaign identity (fail closed); restore the original "
            "campaign.json or use a fresh --out directory")
    else:
        _write_json(campaign_path, identity)

    if run_index is not None and not 0 <= run_index < runs:
        raise SystemExit(
            "--run-index must satisfy 0 <= run-index < N (N=%d)" % runs)

    # Fail closed on evidence-integrity problems BEFORE running
    # anything: a persisted TRANSPORT_FAILURE is a campaign halt
    # under preregistered D1 — it is reported and stops pending
    # human direction, never silently retried; duplicate completed
    # (fixture, run_index) keys mean the log was tampered or
    # double-written — refuse; records from another profile must
    # never blend into this evidence set.
    done = set()
    for r in existing:
        if r.get("terminal_state") == "TRANSPORT_FAILURE":
            raise SystemExit(
                "campaign halted: records.jsonl carries a "
                "TRANSPORT_FAILURE for (%s, run %s) — preregistered "
                "disqualifier D1 territory. Report and stop pending "
                "human direction; do not silently resume."
                % (r.get("fixture"), r.get("run_index")))
        if (r.get("model"), r.get("reasoning_effort"),
                r.get("initial_max_tokens")) != \
                (identity["model"], identity["reasoning_effort"],
                 identity["initial_max_tokens"]):
            raise SystemExit(
                "records.jsonl carries a record from a different "
                "campaign profile (%s/%s/%s) — refusing to blend "
                "evidence sets"
                % (r.get("model"), r.get("reasoning_effort"),
                   r.get("initial_max_tokens")))
        key = (r["fixture"], r["run_index"])
        if key in done:
            raise SystemExit(
                "duplicate completed review key %r in records.jsonl "
                "(fail closed — evidence integrity)" % (key,))
        done.add(key)

    def sink(record):
        with records_path.open("a") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

    if ledger is not None:
        # aggregate ceiling (Stage B1): recover orphans from prior
        # crashes before anything else — settled + outstanding <=
        # ceiling is the invariant, liveness is the only recovery
        # criterion
        ledger.sweep()
    elif spend is not None:
        # legacy per-out_dir ceiling: seed the cumulative cost from
        # the persisted records of THIS output directory only, so
        # every run-index invocation of the balanced schedule
        # inherits the spend of prior invocations under the same
        # identity (tokens are in the records; cost is recomputed
        # under the identity protected prices). The ceiling is
        # enforced per out_dir, not across separate campaign
        # directories.
        for r in existing:
            for a in r.get("attempts") or []:
                spend.add(a)

    post_payload = engine_http(engine)
    indices = range(runs) if run_index is None else [run_index]
    try:
        for fixture in fixtures:
            for ri in indices:
                if (fixture["id"], ri) in done:
                    continue
                logical_review(
                    engine, fixture, ri, model, profile,
                    overrides, post_payload, sink, spend_guard=spend,
                    ledger=ledger, evidence_gate=evidence_gate)
    except SystemExit:
        _write_summary(out_dir, fixtures, runs, model, profile,
                       spend=spend, ledger=ledger)
        raise
    except SpendCeilingReached as e:
        # ceiling enforced BEFORE the request: no record for the
        # halted review, evidence set resumable, decision is human's
        _write_summary(out_dir, fixtures, runs, model, profile,
                       spend=spend, ledger=ledger)
        raise SystemExit(str(e))
    _write_summary(out_dir, fixtures, runs, model, profile,
                   spend=spend, ledger=ledger)
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
    ap.add_argument("--out", default=None,
                    help="output directory (required for --dry-run/--live)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Q0: construct requests only; zero model calls")
    ap.add_argument("--live", action="store_true",
                    help="live mode; requires PM_QUALIFY_LIVE_AUTHORIZED=1")
    ap.add_argument("--spend-ceiling-usd", type=float, default=None,
                    help="hard campaign ceiling; each provider request "
                         "is pre-checked against worst-case cost")
    ap.add_argument("--spend-ledger", default=None,
                    help="path to the shared campaign ledger: enables "
                         "AGGREGATE ceiling enforcement with atomic "
                         "reserve/settle across concurrent invocations "
                         "(Stage B1 mechanism)")
    ap.add_argument("--spend-seed-dir", action="append", default=None,
                    help="records directory seeded into a NEW ledger's "
                         "settled totals (repeatable; used when a "
                         "crash predated the ledger)")
    ap.add_argument("--price-input-per-m", type=float, default=None,
                    help="USD per 1M input tokens (record source!)")
    ap.add_argument("--price-output-per-m", type=float, default=None,
                    help="USD per 1M output tokens (record source!)")
    ap.add_argument("--evidence-gate", choices=("off", "on"),
                    default="off",
                    help="Phase-10 ReviewResult v2 evidence gate: "
                         "blocking findings must carry evidence that "
                         "passes the deterministic checks; default "
                         "off (no behavior change until preregistered)")
    ap.add_argument("--price-source", default=None,
                    help="pricing provenance, e.g. 'openrouter.ai "
                         "z-ai/glm-5.3-flash 2026-09-18 discounted'")
    ap.add_argument("--run-index", type=int, default=None, metavar="I",
                    help="live only: execute ONLY run index I of the "
                         "campaign (N stays fixed in campaign.json); the "
                         "balanced low/high/max schedule is orchestrated "
                         "with repeated single-run-index invocations")
    ap.add_argument("--report", default=None, metavar="RECORDS_JSONL",
                    help="deterministic Stage-A reduction of a "
                         "records.jsonl (read-only; zero calls)")
    args = ap.parse_args(argv)
    if args.report:
        recs_path = pathlib.Path(args.report)
        records = _load_records(recs_path)
        camp_path = recs_path.parent / "campaign.json"
        campaign = (json.loads(camp_path.read_text())
                    if camp_path.exists() else {})
        report = stage_a_report(records, campaign.get("N", 3))
        report["campaign"] = campaign
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    mode = resolve_mode(args)
    if not args.report:
        if not args.out:
            raise SystemExit("--out is required for --dry-run/--live")
        if args.runs < 1:
            raise SystemExit("--runs must be >= 1")
        if args.run_index is not None:
            if args.dry_run:
                raise SystemExit("--run-index applies to --live only")
            if not 0 <= args.run_index < args.runs:
                raise SystemExit(
                    "--run-index must satisfy 0 <= run-index < N "
                    "(N=%d)" % args.runs)
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
        spend = None
        ledger = None
        if (args.spend_ceiling_usd is not None
                or args.price_input_per_m is not None
                or args.price_output_per_m is not None
                or args.price_source is not None):
            if (args.spend_ceiling_usd is None
                    or args.price_input_per_m is None
                    or args.price_output_per_m is None):
                raise SystemExit(
                    "--spend-ceiling-usd requires --price-input-per-m "
                    "and --price-output-per-m (a ceiling cannot be "
                    "reliably enforced without recorded prices)")
            if not args.price_source:
                raise SystemExit(
                    "--price-source is required with prices (pricing "
                    "provenance must be recorded: source + date)")
            engine = load_subject_engine()
            chars = {}
            for f in fixtures:
                ri = rc._review_input(f, args.model, subject_dir=str(ROOT))
                sy, us = engine._build_prompts(ri)
                chars[f["id"]] = len(sy) + len(us)
            spend = SpendGuard(args.spend_ceiling_usd,
                               args.price_input_per_m,
                               args.price_output_per_m, chars)
            spend.price_source = args.price_source
            ledger = None
            evidence_gate = False
            if args.evidence_gate == "on":
                evidence_gate = True
            if args.spend_ledger:
                from eval.spend_ledger import SpendLedger
                ledger = SpendLedger(
                    args.spend_ledger, spend,
                    seed_dirs=args.spend_seed_dir or [])
        live(out_dir, fixtures, args.runs, args.model, profile, overrides,
             run_index=args.run_index, spend=spend, ledger=ledger,
             evidence_gate=evidence_gate)
    return 0


if __name__ == "__main__":
    sys.exit(main())
