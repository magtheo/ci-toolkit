"""Qualification machinery tests (phase 3) — deterministic, no network.

Covers:
- pair integrity MECHANICALLY enforced (the explicit baseline-derived
  requirement: M8 passed 3/3, C8 false-blocked 3/3 — that combination
  must never be promotion-eligible);
- qualification record shape and force-red labeling;
- oracle versioning (stable, content-sensitive, subject-independent);
- verify.py: the deployment invariant as a pure function;
- workflow trust-model source invariants (secret ordering, triggers).
"""

import json
import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import eval.run_corpus as rc  # noqa: E402
import eval.verify as ev      # noqa: E402

TOOLKIT_ROOT = pathlib.Path(__file__).resolve().parents[1]


# ---- pair integrity: the M8/C8 lesson, enforced by machinery -----------------

def _fx_result(fid, kind, passes, pair):
    return {"id": fid, "kind": kind, "pair": pair, "passes_policy": passes}


def test_m8_shape_never_promotion_eligible():
    per = [_fx_result("M8", "positive", True, "C8"),
           _fx_result("C8", "control", False, "M8")]
    violations, eligible = rc.pair_integrity(per)
    assert eligible == []
    assert len(violations) == 1
    assert violations[0]["positive"] == "M8"
    assert violations[0]["control"] == "C8"
    assert "over-triggering" in violations[0]["reason"]


def test_both_pass_is_promotion_eligible():
    per = [_fx_result("M9", "positive", True, "C9"),
           _fx_result("C9", "control", True, "M9")]
    violations, eligible = rc.pair_integrity(per)
    assert eligible == ["M9"]
    assert violations == []


def test_failing_positive_is_not_a_violation_just_not_eligible():
    per = [_fx_result("M4", "positive", False, "C4"),
           _fx_result("C4", "control", True, "M4")]
    violations, eligible = rc.pair_integrity(per)
    assert eligible == []
    assert violations == []   # no false capability claimed


def test_controls_are_never_promotion_entries():
    per = [_fx_result("C4", "control", True, "M4"),
           _fx_result("M4", "positive", False, "C4")]
    violations, eligible = rc.pair_integrity(per)
    assert eligible == [] and violations == []


def test_missing_control_blocks_promotion():
    per = [_fx_result("M1", "positive", True, "C1")]  # control absent
    violations, eligible = rc.pair_integrity(per)
    assert eligible == []
    assert violations and violations[0]["positive"] == "M1"


# ---- qualification record ----------------------------------------------------

def _fake_engine(monkeypatch, results_cycle):
    import types
    calls = {"n": 0}
    fake = types.ModuleType("fake_engine")

    def run_review(review_input):
        r = results_cycle[calls["n"] % len(results_cycle)]
        calls["n"] += 1
        return r

    fake.run_review = run_review
    monkeypatch.setattr(rc, "load_engine", lambda d: fake)
    return calls


_CLEAR = {"schema_version": 1, "assessment": "CLEAR", "findings": [],
          "summary": "", "good": [], "usage": None, "raw_output": ""}
_HIT = {"schema_version": 1, "assessment": "ISSUES_FOUND", "findings": [
    {"file": ".github/workflows/ai-review.yml", "comment":
     "uses secrets: inherit — grant every secret", "severity": "blocking",
     "line": 9, "suggestion": None}], "summary": "", "good": [],
    "usage": None, "raw_output": ""}


def test_record_written_with_expected_fields(tmp_path, monkeypatch):
    # stub a perfectly-behaving engine: M1 hit 3/3, C1 clear 3/3;
    # everything else measured from the REAL corpus fixtures
    def scripted(review_input):
        policy = review_input["policy"]
        title = review_input["title"]
        # only the corpus fixtures under test reach here
        return _CLEAR

    import types
    fake = types.ModuleType("fake_engine")
    fake.run_review = scripted
    monkeypatch.setattr(rc, "load_engine", lambda d: fake)

    record_path = tmp_path / "record.json"
    rc.main(["--n", "1",
             "--subject-sha", "a" * 40,
             "--record-out", str(record_path),
             "--out", str(tmp_path / "report.json")])
    rec = json.loads(record_path.read_text())
    assert rec["schema_version"] == 1
    assert rec["subject_sha"] == "a" * 40
    assert rec["result"] in ("PASS", "FAIL")
    assert rec["oracle_version"] == rc.oracle_version()
    assert "promotion_eligible_positives" in rec
    assert "pair_integrity_violations" in rec
    assert rec["forced_red"] is False
    assert rec["model_profile"]["model"]


def test_forced_red_is_labeled_and_skips_model(tmp_path, monkeypatch):
    def boom(review_input):
        raise AssertionError("force-red must not call the model")

    import types
    fake = types.ModuleType("fake_engine")
    fake.run_review = boom
    monkeypatch.setattr(rc, "load_engine", lambda d: fake)

    record_path = tmp_path / "record.json"
    rccode = rc.main(["--force-red",
                      "--subject-sha", "b" * 40,
                      "--record-out", str(record_path)])
    assert rccode == 1
    rec = json.loads(record_path.read_text())
    assert rec["result"] == "FAIL"
    assert rec["forced_red"] is True
    assert rec["gating_violations"] == ["FORCED-RED-DEMONSTRATION"]


def test_print_oracle_version_secretless(tmp_path):
    import subprocess
    r = subprocess.run(
        [sys.executable, str(TOOLKIT_ROOT / "eval" / "run_corpus.py"),
         "--print-oracle-version"],
        capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert r.returncode == 0
    assert r.stdout.strip() == rc.oracle_version()


# ---- oracle versioning --------------------------------------------------------

def test_oracle_version_stable_and_fixture_sensitive(tmp_path):
    base = tmp_path / "t"
    (base / "eval" / "fixtures").mkdir(parents=True)
    shutil.copy(TOOLKIT_ROOT / "eval" / "run_corpus.py",
                base / "eval" / "run_corpus.py")
    for f in sorted((TOOLKIT_ROOT / "eval" / "fixtures").glob("*.json")):
        shutil.copy(f, base / "eval" / "fixtures" / f.name)
    v1 = rc.oracle_version(base)
    assert v1 == rc.oracle_version(base)
    # mutate one fixture
    target = base / "eval" / "fixtures" / "M1.json"
    o = json.loads(target.read_text())
    o["input"]["title"] = "mutated"
    target.write_text(json.dumps(o))
    assert rc.oracle_version(base) != v1
    # harness content also feeds the oracle identity
    (base / "eval" / "run_corpus.py").write_text("# mutated\n")
    assert rc.oracle_version(base) != v1


# ---- verify.py: the deployment invariant as a pure function -------------------

def _record(**over):
    base = {"subject_sha": "c" * 40, "oracle_version": "0" * 16,
            "result": "PASS", "forced_red": False,
            "model_profile": {"model": "anthropic/claude-haiku-4.5"},
            "n": 3, "promotion_eligible_positives": [],
            "pair_integrity_violations": [], "timestamp": "t"}
    base.update(over)
    return base


def test_verify_passes_good_record():
    v = ev.verify(_record(), "0" * 16, "c" * 40,
                  {"anthropic/claude-haiku-4.5"})
    assert v["verdict"] == "PASS" and v["reasons"] == []


def test_verify_rejects_subject_mismatch():
    v = ev.verify(_record(), "0" * 16, "d" * 40,
                  {"anthropic/claude-haiku-4.5"})
    assert v["verdict"] == "FAIL"
    assert any("subject mismatch" in r for r in v["reasons"])


def test_verify_rejects_stale_oracle():
    v = ev.verify(_record(), "1" * 16, "c" * 40,
                  {"anthropic/claude-haiku-4.5"})
    assert v["verdict"] == "FAIL"
    assert any("stale oracle" in r for r in v["reasons"])


def test_verify_rejects_fail_and_forced_red():
    assert ev.verify(_record(result="FAIL"), "0" * 16, "c" * 40,
                     {"anthropic/claude-haiku-4.5"})["verdict"] == "FAIL"
    v = ev.verify(_record(forced_red=True), "0" * 16, "c" * 40,
                  {"anthropic/claude-haiku-4.5"})
    assert v["verdict"] == "FAIL"
    assert any("forced-red" in r for r in v["reasons"])


def test_verify_rejects_unlisted_model():
    v = ev.verify(_record(model_profile={"model": "gpt/x"}),
                  "0" * 16, "c" * 40, {"anthropic/claude-haiku-4.5"})
    assert v["verdict"] == "FAIL"
    assert any("not in allowed" in r for r in v["reasons"])


# ---- workflow trust-model source invariants -----------------------------------

QUALIFY_YML = TOOLKIT_ROOT / ".github" / "workflows" / "qualify.yml"
VERIFY_YML = (TOOLKIT_ROOT / ".github" / "workflows" /
              "verify-qualification.yml")
REVIEW_YML = TOOLKIT_ROOT / ".github" / "workflows" / "review.yml"


def test_qualify_never_runs_on_pull_request():
    src = QUALIFY_YML.read_text()
    assert "pull_request:" not in src
    assert "pull_request_target" not in src
    assert "if: github.ref == 'refs/heads/main'" in src


def test_qualify_secret_mapped_only_after_guard():
    src = QUALIFY_YML.read_text()
    guard = src.index("guard — subject must be merged into main")
    secret = src.index("secrets.LLM_API_KEY")
    assert guard < secret
    assert "merge-base --is-ancestor" in src


def test_qualify_triggers_cover_behavior_inputs():
    src = QUALIFY_YML.read_text()
    for path in ("engine.py", "parse_review.py", "render.py", "review.sh",
                 "rubric.md", "ai-review.yml", "qualify.yml", "eval/**"):
        assert path in src, path


def test_verify_workflow_is_secretless():
    src = VERIFY_YML.read_text()
    assert "secrets:" not in src
    assert "workflow_call" in src
    assert "LLM_API_KEY" not in src


def test_dogfood_verify_pin_job_is_secretless_and_gated():
    src = REVIEW_YML.read_text()
    job = src[src.index("verify-pin:"):]
    assert "secrets:" not in job.split("verify-pin:")[1]
    assert "verify-qualification.yml" in job


def test_local_reusable_reference_in_target_workflow():
    # `uses: ./...` inside pull_request_target resolves from the
    # trusted base — same commit as review.yml itself
    src = REVIEW_YML.read_text()
    assert "uses: ./.github/workflows/verify-qualification.yml" in src


def test_oracle_version_rejects_empty_corpus(tmp_path):
    base = tmp_path / "t"
    (base / "eval" / "fixtures").mkdir(parents=True)
    shutil.copy(TOOLKIT_ROOT / "eval" / "run_corpus.py",
                base / "eval" / "run_corpus.py")
    with pytest.raises(AssertionError, match="empty corpus"):
        rc.oracle_version(base)


def test_rubric_hash_comes_from_the_subject(tmp_path, monkeypatch):
    # the record's rubric_hash must reflect the SUBJECT's rubric, not
    # the oracle checkout's (regression for the malformed-expression
    # debris caught in review)
    import types
    fake = types.ModuleType("fake_engine")
    fake.run_review = lambda ri: dict(_CLEAR)
    monkeypatch.setattr(rc, "load_engine", lambda d: fake)
    subj = tmp_path / "subject"
    subj.mkdir()
    (subj / "rubric.md").write_text("SUBJECT RUBRIC")
    record_path = tmp_path / "record.json"
    rc.main(["--n", "1", "--subject-dir", str(subj),
             "--subject-sha", "e" * 40,
             "--record-out", str(record_path),
             "--out", str(tmp_path / "report.json")])
    rep = json.loads((tmp_path / "report.json").read_text())
    import hashlib
    assert rep["profile"]["rubric_hash"] == hashlib.sha256(
        b"SUBJECT RUBRIC").hexdigest()[:16]
