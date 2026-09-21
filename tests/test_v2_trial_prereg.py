"""Phase-11 preregistration machine pins.

The prereg document freezes identities BEFORE any v2 prompt exists.
These tests keep the document honest: every pinned hash must equal
reality, the prompt extension's enums must match the parser's, the
trial's fixtures must exist with the frozen expected states, and the
extension's schema must round-trip normalize_v2. Zero provider calls.
"""
import hashlib
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import engine  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import parse_review as pr  # noqa: E402

PREREG = REPO / "eval" / "evidence" / "v2-trial-prereg-2026-09-21" \
    / "PREREGISTRATION.md"
EXTENSION = REPO / "eval" / "v2_trial_prompt_extension.txt"
PROTOCOL = REPO / "eval" / "evidence" \
    / "honesty-audit-protocol-2026-09-21" / "PROTOCOL.md"

DOC = PREREG.read_text()
CONTROLS = ["C3", "C4", "C12", "C13", "C16"]
POSITIVES = ["M3", "M4", "M12", "M13", "M16"]
TRIAL = CONTROLS + POSITIVES
MODEL = "z-ai/glm-5.3-flash"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _doc_hash_for(label):
    rows = [ln for ln in DOC.splitlines()
            if ln.startswith("|") and f"`{label}`" in ln
            and re.search(r"`[0-9a-f]{64}`", ln)]
    assert len(rows) == 1, f"prereg must pin {label} exactly once"
    return re.search(r"`([0-9a-f]{64})`", rows[0]).group(1)


def test_extension_hash_matches_doc():
    assert _sha(EXTENSION.read_bytes()) == _doc_hash_for("prompt extension")


def test_protocol_hash_matches_doc():
    assert _sha(PROTOCOL.read_bytes()) == _doc_hash_for("honesty audit protocol")


def test_states_hash_matches_doc():
    assert _sha((REPO / "eval" / "states.json").read_bytes()) == \
        _doc_hash_for("eval/states.json")


def test_subject_pins_match_doc_and_files():
    for name in ("engine.py", "parse_review.py", "rubric.md",
                 "transport.py", "model_profiles.json",
                 "review_result_schema.json"):
        assert _sha((REPO / name).read_bytes()) == _doc_hash_for(name), name


def test_oracle_identity_unchanged():
    """The oracle CONTENT hash is the binding freeze; ORACLE_SHA in
    the pin tests is the provenance commit the subject files are
    checked out from (4b116a7, PR #74 merge)."""
    assert rc.oracle_version() == "117b4164e5446f50"
    assert "117b4164e5446f50" in DOC
    assert "4b116a7c7c4e9e78cddd362cd3ca4766aaf6ea25" in DOC


def test_extension_enums_match_parser():
    text = EXTENSION.read_text()
    kind_block = text[text.index('"kind": one of'):
                      text.index('"harm": one of')]
    harm_block = text[text.index('"harm": one of'):
                      text.index('"quote"')]
    for block, valid in ((kind_block, pr.EVIDENCE_KINDS),
                         (harm_block, pr.EVIDENCE_HARM)):
        named = set(re.findall(r'"([a-z_]+)"\s*-', block))
        assert named == set(valid), (named, valid)


def test_trial_fixtures_exist_with_frozen_states():
    corpus = {f["id"]: f for f in
              rc.load_corpus(REPO / "eval" / "fixtures")}
    for fid in CONTROLS:
        assert corpus[fid]["expected"]["assessment"] == "CLEAR", fid
    for fid in POSITIVES:
        assert corpus[fid]["expected"]["assessment"] == "ISSUES_FOUND", fid
    # pairs are real pairs in the corpus
    pairs = {"M3": "C3", "M12": "C12", "M13": "C13",
             "M16": "C16", "M4": "C4"}
    for pos, ctl in pairs.items():
        assert corpus[pos]["paired_with"] == ctl or \
            corpus[ctl]["paired_with"] == pos, (pos, ctl)


def test_preregistered_prompt_hashes_reproducible():
    """The exact execution prompts are computable offline: canonical
    user + '\\n\\n' + extension bytes. Records at execution must
    carry these hashes (fail-closed identity check)."""
    ext = EXTENSION.read_text()
    sys_row = [ln for ln in DOC.splitlines()
               if ln.startswith("| (all) |")][0]
    want_system = re.search(r"`([0-9a-f]{64})`", sys_row).group(1)
    for fid in TRIAL:
        fx = json.loads(
            (REPO / "eval" / "fixtures" / f"{fid}.json").read_text())
        system, user = engine._build_prompts(
            rc._review_input(fx, MODEL))
        assert _sha(system.encode()) == want_system, fid
        final = user + "\n\n" + ext
        row = [ln for ln in DOC.splitlines()
               if ln.startswith(f"| {fid} |")][0]
        want_user = re.search(r"`([0-9a-f]{64})`", row).group(1)
        assert _sha(final.encode()) == want_user, fid


def test_extension_schema_round_trips_parser():
    """A response shaped exactly as the extension instructs parses
    through normalize_v2 with the gate on: honest demonstrated
    declaration survives; presumed declaration downgrades."""
    fid = "M3"
    fx = json.loads((REPO / "eval" / "fixtures" / f"{fid}.json").read_text())
    diff = {f["path"]: f["patch"] for f in fx["input"]["files"]}
    path = fx["input"]["files"][0]["path"]
    line = None
    new_ln = None
    for ln in fx["input"]["files"][0]["patch"].splitlines():
        hm = re.match(r"@@ -\\d+(?:,\\d+)? \\+(\\d+)(?:,\\d+)? @@", ln)
        if hm:
            new_ln = int(hm.group(1))
            continue
        if new_ln is None:
            continue
        if ln.startswith("-"):
            continue
        if ln.startswith("+") and "-mtime -30" in ln:
            line = new_ln
            break
        new_ln += 1
    assert line is not None
    assert line in pr.valid_lines_from_patch(
        fx["input"]["files"][0]["patch"])
    base = {"file": path, "severity": "blocking", "line": line,
            "comment": "roadmap freshness window never fails the build"}
    demonstrated = json.dumps({"assessment": "ISSUES_FOUND",
                               "summary": "s",
                               "findings": [dict(base, evidence={
                                   "kind": "in_diff_contract_contradiction",
                                   "harm": "demonstrated",
                                   "quote": 'find "$repo/plans/ROADMAP.md" -mtime -30'})],
                               "good": []})
    result, audit = pr.normalize_v2(demonstrated, diff, gate=True)
    assert result["findings"][0]["severity"] == "blocking"
    assert result["schema_version"] == 2 and audit[0]["permitted"] is True
    presumed = json.dumps({"assessment": "ISSUES_FOUND", "summary": "s",
                           "findings": [dict(base, evidence={
                               "kind": "in_diff_contract_contradiction",
                               "harm": "presumed",
                               "quote": "-mtime -30"})],
                           "good": []})
    result, _ = pr.normalize_v2(presumed, diff, gate=True)
    assert result["findings"][0]["severity"] == "non-blocking"


def test_model_and_request_profile_are_frozen():
    profiles = json.loads((REPO / "model_profiles.json").read_text())
    p = profiles["profiles"][MODEL]
    assert p["max_tokens"] == 8000
    assert p["reasoning_effort"] == "low"
    assert p["structured_output"] is True
    assert p["retry_budget_escalation"] is True
    for term in (MODEL, "max_tokens=8000", "16000",
                 "OpenRouter provider routing"):
        assert term in DOC, term


def test_prereg_decision_terms_pinned():
    """Edits that move the rule trip the test."""
    for term in ("Hard ceiling $0.02", "R ≤ 10%", "low effort only",
                 "zero non-oracle-defect", "M13 carve-out",
                 "does not promote anything",
                 "frozen fixture BEFORE any fix"):
        assert term in DOC, term
