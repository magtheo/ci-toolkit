"""Phase-12 execution-wiring tests for the preregistered v2 trial.

Zero provider calls. Pins:
- default harness behavior is byte-identical (suffix/schema optional);
- the trial runner's pre-flight verifies EVERY preregistered pin
  against reality and refuses on any mismatch BEFORE request 1;
- spend authorization requires BOTH the runner flag and the
  PM_QUALIFY_LIVE_AUTHORIZED gate;
- an authorized (faked-transport) run sends exactly the preregistered
  prompts under the trial schema, with the gate on and the $0.02
  ceiling, freezes records + mechanical counts, and computes NO
  verdict.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import engine  # noqa: E402
import eval.profile_qualification as pq  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import eval.run_v2_trial as rt  # noqa: E402
import transport  # noqa: E402

PREREG_TEXT = rt.PREREG.read_text()
PINS = rt.prereg_pins(PREREG_TEXT)
TRIAL_SCHEMA = json.loads(rt.TRIAL_SCHEMA.read_text())


def _review_input(fid, model):
    fx = json.loads(
        (REPO / "eval" / "fixtures" / f"{fid}.json").read_text())
    return rc._review_input(fx, model)


# ---- harness threading: default-identical, opt-in behavior ----------

def test_default_request_is_byte_identical():
    ri = _review_input("M3", "z-ai/glm-5.3-flash")
    profile = transport.load_profile("z-ai/glm-5.3-flash")
    s1, u1, b1 = pq.build_initial_request(
        engine, ri, "z-ai/glm-5.3-flash", profile)
    s2, u2 = engine._build_prompts(ri)
    assert (s1, u1) == (s2, u2)
    assert b1["response_format"]["json_schema"] == transport.load_schema()


def test_prompt_suffix_appends_exactly_once():
    ri = _review_input("M3", "z-ai/glm-5.3-flash")
    profile = transport.load_profile("z-ai/glm-5.3-flash")
    suffix = "SUFFIX MARKER\nline two"
    _, user, body = pq.build_initial_request(
        engine, ri, "z-ai/glm-5.3-flash", profile, prompt_suffix=suffix)
    canon_user = engine._build_prompts(ri)[1]
    assert user == canon_user + "\n\n" + suffix
    assert body["messages"][1]["content"] == user


def test_response_schema_swap_and_refusal():
    ri = _review_input("M3", "z-ai/glm-5.3-flash")
    profile = transport.load_profile("z-ai/glm-5.3-flash")
    assert profile["structured_output"] is True
    _, _, body = pq.build_initial_request(
        engine, ri, "z-ai/glm-5.3-flash", profile,
        response_schema=TRIAL_SCHEMA)
    assert body["response_format"]["json_schema"] == TRIAL_SCHEMA
    assert body["response_format"]["json_schema"] != \
        transport.load_schema()
    unstructured = dict(profile, structured_output=False)
    with pytest.raises(SystemExit):
        pq.build_initial_request(engine, ri, "z-ai/glm-5.3-flash",
                                 unstructured,
                                 response_schema=TRIAL_SCHEMA)


# ---- runner pre-flight ----------------------------------------------

def test_runner_preflight_ready_on_clean_tree(capsys):
    assert rt.main(["--check"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("READY")
    assert "$0.02" in out and "z-ai/glm-5.3-flash" in out


def test_runner_preflight_blocks_doctored_prereg(tmp_path, capsys):
    doctored = tmp_path / "PREREGISTRATION.md"
    doctored.write_text(PREREG_TEXT.replace(
        PINS["pins"]["M3"], "0" * 64, 1))
    real_prereg, real_ext = rt.PREREG, rt.EXTENSION
    rt.PREREG = doctored
    try:
        assert rt.main(["--check"]) == 2
        out = capsys.readouterr().out
        assert "BLOCKED" in out and "prompt M3" in out
        assert "nothing was sent" in out
    finally:
        rt.PREREG, rt.EXTENSION = real_prereg, real_ext


def test_prereg_pins_are_complete():
    for name in ("oracle_version", "states.json", "engine.py",
                 "parse_review.py", "rubric.md", "transport.py",
                 "model_profiles.json", "review_result_schema.json",
                 "honesty audit protocol", "prompt extension",
                 "trial v2 response schema", "(all)",
                 "C3", "C11", "C12", "C13", "C16",
                 "M3", "M11", "M12", "M13", "M16"):
        assert name in PINS["pins"], name
    assert PINS["model"] == "z-ai/glm-5.3-flash"
    assert PINS["effort"] == "low"
    assert PINS["max_tokens"] == 8000
    assert PINS["ceiling_usd"] == 0.02
    assert sorted(PINS["fixtures"]) == [
        "C11", "C12", "C13", "C16", "C3",
        "M11", "M12", "M13", "M16", "M3"]
    assert "C4" not in PINS["fixtures"] and "M4" not in PINS["fixtures"]


# ---- authorization gates + faked execution ---------------------------

class _ForbiddenPost:
    def __call__(self, *a, **k):
        raise AssertionError("provider reached without authorization")


def test_spend_refused_without_live_env(monkeypatch, capsys):
    monkeypatch.delenv("PM_QUALIFY_LIVE_AUTHORIZED", raising=False)
    monkeypatch.setattr(pq, "engine_http",
                        lambda engine: _ForbiddenPost())
    argv = ["--authorize-spend", "--out", "/tmp/opencode/never",
            "--price-input-per-m", "0.1", "--price-output-per-m", "0.5",
            "--price-source", "test"]
    assert rt.main(argv) == 2
    assert "spend refused" in capsys.readouterr().out


def test_spend_refused_without_prices(monkeypatch, capsys):
    monkeypatch.setenv("PM_QUALIFY_LIVE_AUTHORIZED", "1")
    monkeypatch.setattr(pq, "engine_http",
                        lambda engine: _ForbiddenPost())
    assert rt.main(["--authorize-spend", "--out",
                    "/tmp/opencode/never"]) == 2
    assert "recorded prices" in capsys.readouterr().out


@pytest.fixture()
def fake_v2_transport(monkeypatch):
    """Canned OK_CONTENT transport capturing every request body."""
    import tests.test_profile_qualification as tpq
    bodies = []
    content = json.dumps({"assessment": "CLEAR", "summary": "ok",
                          "findings": [], "good": []})

    def fake_engine_http(engine_module):
        def post(body):
            bodies.append(json.loads(json.dumps(body)))
            return tpq._ok_body(content), 0, 0.01
        return post

    monkeypatch.setattr(pq, "engine_http", fake_engine_http)
    return bodies


def test_authorized_run_executes_frozen_trial(
        tmp_path, monkeypatch, fake_v2_transport):
    monkeypatch.setenv("PM_QUALIFY_LIVE_AUTHORIZED", "1")
    out = tmp_path / "trial"
    argv = ["--authorize-spend", "--out", str(out),
            "--price-input-per-m", "0.1",
            "--price-output-per-m", "0.5",
            "--price-source", "test-prices"]
    assert rt.main(argv) == 0

    records = [json.loads(ln) for ln in
               (out / "records.jsonl").read_text().splitlines()]
    assert len(records) == 10
    by_fixture = {r["fixture"]: r for r in records}
    assert sorted(by_fixture) == sorted(PINS["fixtures"])
    for fid, r in by_fixture.items():
        # exactly the preregistered final prompt was sent
        assert r["prompt_sha256"][1] == PINS["pins"][fid], fid
        assert r["prompt_sha256"][0] == PINS["pins"]["(all)"]
        assert r["reasoning_effort"] == "low"
        assert r["initial_max_tokens"] == 8000
        assert r["evidence_gate"]["enabled"] is True
        assert r["raw_model_output"] is not None
    # every request carried the trial schema + suffixed user prompt
    for body in fake_v2_transport:
        assert body["response_format"]["json_schema"] == TRIAL_SCHEMA
        assert body["messages"][1]["content"].endswith(
            rt.EXTENSION.read_text())
        assert body["model"] == "z-ai/glm-5.3-flash"
        assert body["max_tokens"] == 8000
    # the ceiling came from the prereg, prices recorded
    campaign = json.loads((out / "campaign.json").read_text())
    assert campaign["model"] == "z-ai/glm-5.3-flash"
    state = json.loads((out / "trial-state.json").read_text())
    assert state["status"] == "EXECUTED_PENDING_ADJUDICATION"
    assert state["ceiling_usd"] == 0.02
    assert state["actual_cost_usd"] >= 0.0
    assert state["price_source"] == "test-prices"
    assert len(state["mechanical_counts"]) == 10
    # the runner computes NO verdict: no decision keys anywhere, and
    # no adjudication verdict tokens as values (the explanatory note
    # saying the opposite is the only allowed mention)
    for key in state:
        assert key not in ("decision", "verdict", "outcome",
                           "GO", "NO-GO", "go", "no_go"), key
    for count in state["mechanical_counts"]:
        assert set(count) == {"fixture", "run_index", "assessment",
                              "blocking_survivors",
                              "gate_downgrades"}, count
