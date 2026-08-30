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
    # all-CLEAR stub: the GATING controls pass, nothing violates
    assert rec["gating_violations"] == []
    assert rec["result"] == "PASS"
    # every promotion-eligible positive has a passing pair (none can
    # pass here — no detections — so eligibility must be empty)
    assert rec["promotion_eligible_positives"] == []
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

def _seed_oracle_tree(tmp_path):
    base = tmp_path / "t"
    (base / "eval" / "fixtures").mkdir(parents=True)
    shutil.copy(TOOLKIT_ROOT / "eval" / "run_corpus.py",
                base / "eval" / "run_corpus.py")
    for f in sorted((TOOLKIT_ROOT / "eval" / "fixtures").glob("*.json")):
        shutil.copy(f, base / "eval" / "fixtures" / f.name)
    shutil.copy(TOOLKIT_ROOT / "eval" / "states.json",
                base / "eval" / "states.json")
    return base


def test_oracle_version_stable_and_fixture_sensitive(tmp_path):
    base = _seed_oracle_tree(tmp_path)
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
    assert "records/by-subject/" in job


def test_dogfood_verify_pin_inlines_the_consumer_checks():
    # inlined so the dogfood check is self-contained; the reusable
    # verify-qualification.yml remains the consumer interface
    src = REVIEW_YML.read_text()
    job = src[src.index("verify-pin:"):]
    assert "records/by-subject/" in job
    assert "--print-oracle-version" in job
    assert "eval/verify.py" in job


def test_oracle_version_rejects_empty_corpus(tmp_path):
    base = _seed_oracle_tree(tmp_path)
    for f in (base / "eval" / "fixtures").glob("*.json"):
        f.unlink()
    with pytest.raises(AssertionError, match="empty corpus"):
        rc.oracle_version(base)


# ---- oracle identity includes the GATING ratchet (review blocker 1) -----

def test_state_promotion_changes_oracle_version(tmp_path):
    base = _seed_oracle_tree(tmp_path)
    v_before = rc.oracle_version(base)
    states = json.loads((base / "eval" / "states.json").read_text())
    states["M5"] = "GATING"
    (base / "eval" / "states.json").write_text(json.dumps(states))
    assert rc.oracle_version(base) != v_before, \
        "promoting a fixture to GATING without changing the oracle " \
        "identity lets stale PASS records authorize deployment"


def test_missing_states_fails_closed(tmp_path):
    base = _seed_oracle_tree(tmp_path)
    (base / "eval" / "states.json").unlink()
    with pytest.raises(AssertionError, match="states.json absent"):
        rc.oracle_version(base)


def test_malformed_states_fails_closed(tmp_path):
    base = _seed_oracle_tree(tmp_path)
    (base / "eval" / "states.json").write_text(
        json.dumps({"M1": "SUPER-GATING"}))
    with pytest.raises(AssertionError, match="unknown state"):
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


# ---- publisher E2E incl. requalification (review blocker 3) -------------------

import subprocess as sp


def _run_publisher(repo, subject, record):
    return sp.run(
        ["bash", str(TOOLKIT_ROOT / "eval" / "publish_record.sh"),
         subject, str(record), str(repo)],
        capture_output=True, text=True, timeout=120)


def _record_file(tmp_path, name):
    rec = _record(subject_sha="f" * 40)
    path = tmp_path / name
    path.write_text(json.dumps(rec))
    return path


def test_publisher_bootstrap_and_requalification(tmp_path):
    # bare origin + clone; the clone plays the workflow checkout
    origin = tmp_path / "origin.git"
    sp.run(["git", "clone", "--bare", str(TOOLKIT_ROOT), str(origin)],
           check=True, capture_output=True)
    repo = tmp_path / "repo"
    sp.run(["git", "clone", str(origin), str(repo)],
           check=True, capture_output=True)

    rec1 = _record_file(tmp_path, "r1.json")
    rec2 = _record_file(tmp_path, "r2.json")

    # bootstrap: first qualification ever
    r1 = _run_publisher(repo, "f" * 40, rec1)
    assert r1.returncode == 0, r1.stderr
    # requalification: same subject, record ALREADY tracked on the
    # branch — the classic collision must not happen
    r2 = _run_publisher(repo, "f" * 40, rec2)
    assert r2.returncode == 0, r2.stderr

    listing = sp.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only",
         "origin/qualifications"], capture_output=True, text=True)
    files = listing.stdout.split()
    assert "records/by-subject/" + "f" * 40 + ".json" in files
    # both the subject record and the per-oracle record exist
    assert sum(1 for f in files if f.startswith("records/")) >= 2


def test_publisher_second_subject_lands_on_existing_branch(tmp_path):
    origin = tmp_path / "origin.git"
    sp.run(["git", "clone", "--bare", str(TOOLKIT_ROOT), str(origin)],
           check=True, capture_output=True)
    repo = tmp_path / "repo"
    sp.run(["git", "clone", str(origin), str(repo)],
           check=True, capture_output=True)
    assert _run_publisher(repo, "a" * 40, _record_file(tmp_path, "a.json")).returncode == 0
    # a DIFFERENT clone qualifies a different subject concurrently-ish
    repo2 = tmp_path / "repo2"
    sp.run(["git", "clone", str(origin), str(repo2)],
           check=True, capture_output=True)
    r = _run_publisher(repo2, "b" * 40, _record_file(tmp_path, "b.json"))
    assert r.returncode == 0, r.stderr
    listing = sp.run(["git", "-C", str(repo), "fetch", "origin",
                      "qualifications"], capture_output=True, text=True)
    tree = sp.run(["git", "-C", str(repo), "ls-tree", "-r", "--name-only",
                   "origin/qualifications"], capture_output=True, text=True)
    files = tree.stdout.split()
    assert "records/by-subject/" + "a" * 40 + ".json" in files
    assert "records/by-subject/" + "b" * 40 + ".json" in files


# ---- dogfood verifier source invariants (review blocker 2) --------------------

def test_verify_pin_uses_the_files_endpoint_and_fails_closed():
    src = REVIEW_YML.read_text()
    job = src[src.index("verify-pin:"):]
    assert "/files" in job and "--paginate" in job
    # pin lines touched but no extractable SHA => hard failure
    assert "refusing to pass verification without evidence" in job
    # extraction is pin-specific, not any-40-hex
    assert "ai-review\\.yml@" in job and "toolkit_ref:" in job


def test_qualify_publishes_via_script_and_is_serialized():
    src = QUALIFY_YML.read_text()
    assert "publish_record.sh" in src
    assert "concurrency:" in src
    assert "qualifications-branch" in src


def test_explicit_allow_model_replaces_the_default(tmp_path, monkeypatch):
    # caller-specified allowlists are AUTHORITATIVE: providing
    # --allow-model must not sneak the default profile back in
    import subprocess as sp2
    rec = tmp_path / "rec.json"
    rec.write_text(json.dumps(_record()))
    r = sp2.run(
        [sys.executable, str(TOOLKIT_ROOT / "eval" / "verify.py"),
         str(rec), "--oracle-version", "0" * 16,
         "--subject", "c" * 40, "--allow-model", "some/other-model"],
        capture_output=True, text=True)
    assert r.returncode == 1
    assert "not in allowed" in r.stdout
