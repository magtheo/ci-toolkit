"""Phase-10 ReviewResult v2 + parser-owned evidence gate.

Zero provider calls. Pins:
- v1 normalize() is byte-compatible (existing suite covers; explicit
  spot check here);
- the evidence gate is deterministic, fail-closed, and separates
  MECHANICALLY VERIFIED checks from MODEL-DECLARED classification;
- adversarial fixtures on C3/C12/C13 show the gate's honest limit:
  a model quoting real code and falsely declaring harm=demonstrated
  PASSES the gate — that residue belongs to the honesty audit
  protocol, never to the parser;
- the Phase-08 oracle clarification composes with the gate (C12
  blockers quoting the removed contract phrase fail quote-in-patch);
- the harness persists raw model output and the gate audit.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import parse_review as pr  # noqa: E402
import eval.run_corpus as rc  # noqa: E402

FIXTURES = {f["id"]: f for f in
            rc.load_corpus(REPO / "eval" / "fixtures")}


def _diff(fid):
    return {f["path"]: f["patch"]
            for f in FIXTURES[fid]["input"]["files"]}


def _finding(fid, quote, kind, harm, line=None, file=None,
             severity="blocking", comment="machine fixture"):
    f = file or FIXTURES[fid]["input"]["files"][0]["path"]
    out = {"file": f, "severity": severity, "comment": comment,
           "evidence": {"kind": kind, "harm": harm, "quote": quote}}
    if line is not None:
        out["line"] = line
    return out


def _model_output(findings, assessment="ISSUES_FOUND"):
    return json.dumps({"assessment": assessment, "summary": "s",
                       "findings": findings, "good": []})


def _v2(content, fid, gate=True, diff=None):
    return pr.normalize_v2(content, _diff(fid) if diff is None else diff,
                           gate=gate)


# ---- true positives survive with sound declarations ------------------

def test_m3_contract_contradiction_survives():
    content = _model_output([_finding(
        "M3", 'find "$repo/plans/ROADMAP.md" -mtime -30',
        "in_diff_contract_contradiction", "demonstrated", line=10)])
    result, audit = _v2(content, "M3")
    f = result["findings"][0]
    assert f["severity"] == "blocking"
    assert result["assessment"] == "ISSUES_FOUND"
    assert audit[0]["permitted"] is True
    assert result["schema_version"] == 2


def test_m12_clarified_contract_detection_survives():
    content = _model_output([_finding(
        "M12", "except (OriginError, ParseError):",
        "in_diff_contract_contradiction", "demonstrated", line=31)])
    result, audit = _v2(content, "M12")
    assert result["findings"][0]["severity"] == "blocking"
    assert audit[0]["permitted"] is True


def test_m16_fabricated_success_survives():
    content = _model_output([_finding(
        "M16", 'return {"ok": True, "updated": len(LABELS)}',
        "in_diff_behavior", "demonstrated", line=11)])
    result, audit = _v2(content, "M16")
    assert result["findings"][0]["severity"] == "blocking"


# ---- mechanical failures downgrade -----------------------------------

def test_missing_file_downgrades():
    content = _model_output([_finding(
        "M3", "-mtime -30", "in_diff_behavior", "demonstrated",
        file="not/in/diff.py")])
    result, audit = _v2(content, "M3")
    assert result["findings"][0]["severity"] == "non-blocking"
    assert result["findings"][0]["machine_reason"] == \
        "BLOCKING_EVIDENCE_INSUFFICIENT"
    assert result["assessment"] == "CLEAR"
    assert result["assessment_recomputed"] is True
    # missing file also voids the quote check (fail-closed)
    assert audit[0]["failed_checks"] == ["file_in_diff",
                                         "quote_in_patch"]


def test_quote_not_in_patch_downgrades():
    content = _model_output([_finding(
        "M3", "parses the Last reviewed date with dateutils",
        "in_diff_contract_contradiction", "demonstrated")])
    result, _ = _v2(content, "M3")
    assert result["findings"][0]["severity"] == "non-blocking"


def test_line_outside_hunk_downgrades():
    content = _model_output([_finding(
        "M16", 'return {"ok": True, "updated": len(LABELS)}',
        "in_diff_behavior", "demonstrated", line=999)])
    result, audit = _v2(content, "M16")
    assert result["findings"][0]["severity"] == "non-blocking"
    assert "line_in_hunk" in audit[0]["failed_checks"]


def test_presumed_harm_downgrades():
    content = _model_output([_finding(
        "M3", 'find "$repo/plans/ROADMAP.md" -mtime -30',
        "in_diff_contract_contradiction", "presumed", line=10)])
    result, audit = _v2(content, "M3")
    assert result["findings"][0]["severity"] == "non-blocking"
    assert "harm_declared_demonstrated" in audit[0]["failed_checks"]
    declared = [c for c in audit[0]["checks"]
                if c["class"] == "declared"]
    assert len(declared) == 2  # mechanical vs declared is explicit


def test_out_of_diff_assumption_kind_downgrades():
    content = _model_output([_finding(
        "M3", "-mtime -30", "out_of_diff_assumption", "demonstrated")])
    result, audit = _v2(content, "M3")
    assert result["findings"][0]["severity"] == "non-blocking"
    assert "kind_not_presumed_assumption" in audit[0]["failed_checks"]


def test_gate_without_diff_fails_closed():
    content = _model_output([_finding(
        "M16", 'return {"ok": True}', "in_diff_behavior",
        "demonstrated")])
    result, audit = pr.normalize_v2(content, None, gate=True)
    assert result["findings"][0]["severity"] == "non-blocking"
    assert audit[0]["failed_checks"][0] == "file_in_diff"


def test_missing_evidence_fails_closed_when_gated():
    content = json.dumps({"assessment": "ISSUES_FOUND", "summary": "s",
                          "findings": [{"file": FIXTURES["M16"]["input"]["files"][0]["path"],
                                        "severity": "blocking",
                                        "comment": "no evidence object"}],
                          "good": []})
    result, audit = pr.normalize_v2(content, _diff("M16"), gate=True)
    assert result["findings"][0]["severity"] == "non-blocking"
    assert "quote_in_patch" in audit[0]["failed_checks"]


def test_malformed_evidence_enum_downgrades():
    content = _model_output([_finding(
        "M16", 'return {"ok": True}', "vibes", "demonstrated")])
    result, audit = _v2(content, "M16")
    assert result["findings"][0]["severity"] == "non-blocking"


# ---- adversarial cases: the gate's honest limit ----------------------

def test_c13_real_keyword_false_demonstrated_passes_gate():
    """THE adversarial pin (B1 C13 survivor class): real in-diff
    keyword + falsely declared demonstrated harm PASSES the gate.
    Mechanical checks cannot read intent; this residue belongs to the
    honesty audit protocol. The gate must not pretend otherwise."""
    content = _model_output([_finding(
        "C13", "pull_request_target", "in_diff_behavior",
        "demonstrated", line=3,
        comment="publishes unreviewed PR head code with credentials")])
    result, audit = _v2(content, "C13")
    assert result["findings"][0]["severity"] == "blocking"
    assert audit[0]["permitted"] is True
    declared = [c for c in audit[0]["checks"] if c["class"] == "declared"]
    assert all(c["passed"] for c in declared)  # only declared, unverified


def test_c12_real_code_false_contradiction_passes_gate():
    """C12 KeyError family: quotes real code, claims contract
    contradiction — mechanically valid, semantically a false blocker.
    Survives the gate; honesty-audit case."""
    content = _model_output([_finding(
        "C12", '_cache["last_good"]', "in_diff_contract_contradiction",
        "demonstrated", line=32)])
    result, audit = _v2(content, "C12")
    assert result["findings"][0]["severity"] == "blocking"


def test_c12_removed_contract_phrase_fails_quote_check():
    """Composition with the Phase-08 clarification: quoting the OLD
    docstring phrase no longer matches the clarified patch."""
    content = _model_output([_finding(
        "C12", "on origin failure serve the last-good",
        "in_diff_contract_contradiction", "demonstrated")])
    result, _ = _v2(content, "C12")
    assert result["findings"][0]["severity"] == "non-blocking"


def test_c13_honest_declaration_downgrades():
    content = _model_output([_finding(
        "C13", "pull_request_target", "out_of_diff_assumption",
        "presumed", line=3)])
    result, _ = _v2(content, "C13")
    assert result["findings"][0]["severity"] == "non-blocking"
    assert result["assessment"] == "CLEAR"


def test_c3_guard_design_weakness_with_presumed_harm_downgrades():
    content = _model_output([_finding(
        "C3", 'echo "STALE: $repo"', "in_diff_behavior", "presumed",
        line=12, comment="wired into CI, a STALE result would not fail "
                         "the build")])
    result, _ = _v2(content, "C3")
    assert result["findings"][0]["severity"] == "non-blocking"


# ---- v1 compatibility + parser parity --------------------------------

def test_v1_normalize_unchanged_and_schema_v1():
    content = _model_output([{"file": "a.py", "severity": "blocking",
                              "comment": "broken", "line": 1}])
    legacy = pr.normalize(content)
    assert legacy["schema_version"] == 1
    assert legacy["assessment"] == "ISSUES_FOUND"
    assert "evidence" not in legacy["findings"][0]
    assert "machine_reason" not in legacy["findings"][0]


def test_gate_off_preserves_evidence_without_gating():
    content = _model_output([_finding(
        "M3", "-mtime -30", "out_of_diff_assumption", "presumed")])
    result, audit = pr.normalize_v2(content, _diff("M3"), gate=False)
    assert result["findings"][0]["severity"] == "blocking"  # untouched
    assert result["findings"][0]["evidence"]["kind"] == \
        "out_of_diff_assumption"
    assert audit == []
    assert result["schema_version"] == 2


def test_inconclusive_passthrough_has_no_gate():
    result, audit = pr.normalize_v2("not json at all", _diff("M3"),
                                    gate=True)
    assert result["assessment"] == "INCONCLUSIVE"
    assert result["schema_version"] == 1
    assert audit == []


def test_quote_normalization_parity_with_matcher():
    samples = [
        'find "$repo/plans/ROADMAP.md" -mtime -30',
        "return {\"ok\": True, \"updated\": len(LABELS)}",
        "on origin failure serve the last-good cached config",
        "except (OriginError, ParseError):",
        "isn't verifiable from the diff",
    ]
    for s in samples:
        assert pr.normalize_quote_text(s) == rc._norm_needle_text(s)


def test_machine_downgrade_recompute_never_yields_inconclusive():
    """Machine downgrades are validated decisions: ISSUES_FOUND with
    all blockers gate-downgraded resolves to CLEAR — the INCONCLUSIVE
    path stays reserved for untrusted output."""
    content = _model_output([_finding(
        "C3", 'echo "OK: $repo" and exit 0 with no nonzero path',
        "out_of_diff_assumption", "presumed")], assessment="ISSUES_FOUND")
    result, _ = _v2(content, "C3")
    assert result["assessment"] == "CLEAR"
    assert result["assessment_recomputed"] is True


# ---- harness wiring ---------------------------------------------------

def test_live_records_raw_output_and_gate_audit(tmp_path, monkeypatch):
    import eval.profile_qualification as pq
    import tests.test_profile_qualification as tpq

    v2_content = _model_output([_finding(
        "C1", "anything", "out_of_diff_assumption", "presumed",
        file=FIXTURES["C1"]["input"]["files"][0]["path"],
        comment="gate should downgrade this")])

    def fake_engine_http(engine_module):
        def post(body):
            return tpq._ok_body(v2_content), 0, 0.01
        return post

    monkeypatch.setattr(pq, "engine_http", fake_engine_http)
    monkeypatch.setenv("PM_QUALIFY_LIVE_AUTHORIZED", "1")
    out = tmp_path / "gated"
    profile, overrides = tpq._low_profile()
    pq.live(out, [tpq._fixture("C1")], 1, tpq.MODEL, profile, overrides,
            evidence_gate=True)
    rec = json.loads((out / "records.jsonl").read_text().splitlines()[0])
    assert rec["raw_model_output"] == v2_content
    assert rec["evidence_gate"]["enabled"] is True
    audit = rec["evidence_gate"]["audit"]
    assert audit and audit[0]["permitted"] is False
    # the declared-presumed blocker was downgraded -> CLEAR
    assert rec["result"]["assessment"] == "CLEAR"
    assert rec["result"]["schema_version"] == 2


def test_live_default_leaves_gate_off(tmp_path, monkeypatch):
    import eval.profile_qualification as pq
    import tests.test_profile_qualification as tpq

    def fake_engine_http(engine_module):
        def post(body):
            return tpq._ok_body(tpq._CLEAR), 0, 0.01
        return post

    monkeypatch.setattr(pq, "engine_http", fake_engine_http)
    monkeypatch.setenv("PM_QUALIFY_LIVE_AUTHORIZED", "1")
    out = tmp_path / "plain"
    profile, overrides = tpq._low_profile()
    pq.live(out, [tpq._fixture("C1")], 1, tpq.MODEL, profile, overrides)
    rec = json.loads((out / "records.jsonl").read_text().splitlines()[0])
    assert rec.get("evidence_gate") is None
    assert rec["raw_model_output"] == tpq._CLEAR
    assert rec["result"]["schema_version"] == 1

def test_cli_evidence_gate_on_without_spend_flags_reaches_live(tmp_path, monkeypatch):
    """CLI gate state is independent of optional spend configuration."""
    import eval.profile_qualification as pq

    called = {}

    def fake_live(out_dir, fixtures, runs, model, profile, overrides,
                  run_index=None, spend=None, ledger=None,
                  evidence_gate=False):
        called["gate"] = evidence_gate
        called["spend"] = spend
        called["ledger"] = ledger

    monkeypatch.setattr(pq, "live", fake_live)
    monkeypatch.setenv("PM_QUALIFY_LIVE_AUTHORIZED", "1")
    rc = pq.main([
        "--live",
        "--reasoning-effort", "low",
        "--fixtures", "C1",
        "--runs", "1",
        "--out", str(tmp_path / "cli-gated"),
        "--evidence-gate", "on",
    ])
    assert rc == 0
    assert called == {"gate": True, "spend": None, "ledger": None}

def test_patch_content_keeps_code_lines_that_resemble_diff_headers():
    patch = (
        "--- a/x.txt\n"
        "+++ b/x.txt\n"
        "@@ -1 +1 @@\n"
        "----removed-marker\n"
        "++++added-marker\n"
    )
    body = pr._patch_content(patch)
    assert "---removed-marker" in body
    assert "+++added-marker" in body
    assert "--- a/x.txt" not in body
    assert "+++ b/x.txt" not in body


def test_dry_run_record_explicitly_has_null_raw_model_output(tmp_path):
    import eval.profile_qualification as pq

    pq.main([
        "--dry-run",
        "--reasoning-effort", "low",
        "--fixtures", "C1",
        "--runs", "1",
        "--out", str(tmp_path / "dry"),
    ])
    req = json.loads((tmp_path / "dry" / "requests.json").read_text())
    rec = req["records"][0]
    assert "raw_model_output" in rec
    assert rec["raw_model_output"] is None

