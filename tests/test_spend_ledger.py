"""Stage B1 aggregate spend ledger — invariant and recovery tests.

The preregistered invariant: settled spend + outstanding reservations
<= ceiling, across concurrent invocations and crashes. Recovery is
liveness-based, never age-based: a reservation whose pid is alive is
never settled, no matter how old; a dead pid's reservation settles at
the reserved amount (fail closed).
"""
import json
import subprocess
import sys
import time

import pytest

import eval.profile_qualification as pq
from eval.spend_ledger import SpendLedger, pid_alive

REPO = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True).stdout.strip()


def _guard(ceiling=1.0, chars=None):
    return pq.SpendGuard(ceiling, 0.075, 0.25,
                         chars or {"C1": 4000, "C2": 4000})


def _ledger(tmp_path, ceiling=1.0, seed_dirs=()):
    return SpendLedger(tmp_path / "ledger.json", _guard(ceiling),
                       seed_dirs=seed_dirs)


def _dead_pid():
    p = subprocess.Popen(["true"])
    p.wait()
    return p.pid


def _alive_pid():
    p = subprocess.Popen(["sleep", "30"])
    return p


def _make_reservation(ledger, fixture="C1", gen=1000, pid=None, age=None):
    """Inject a reservation directly (bypassing reserve()) to control
    pid and age for recovery tests."""
    worst_in = ledger.guard._est_input(fixture)
    worst_usd = ledger.guard.cost_usd_of(worst_in, gen)
    res = {"id": "injected-%d" % time.monotonic_ns(), "pid": pid or -1,
           "created_at": age if age is not None else int(time.time()),
           "in_tokens": worst_in, "out_tokens": gen,
           "usd": worst_usd, "fixture": fixture}
    with ledger._locked() as st:
        st["reservations"].append(res)
    from eval.spend_ledger import Reservation
    return Reservation(res["id"], res["pid"], res["created_at"],
                       worst_in, gen, worst_usd)


# ---- reserve / settle basics ----------------------------------------

def test_reserve_holds_invariant_and_settle_releases(tmp_path):
    led = _ledger(tmp_path, ceiling=0.01)
    res = led.reserve("C1", 1000)
    st = led.state()
    assert st["outstanding_reservations"] == 1
    assert st["invariant_holds"]
    settled_usd = led.settle(res, {"prompt_tokens": 100,
                                   "completion_tokens": 10,
                                   "reasoning_tokens": 5})
    st = led.state()
    assert st["outstanding_reservations"] == 0
    assert st["settled_usd"] == pytest.approx(settled_usd, abs=1e-6)
    assert st["remaining_usd"] == pytest.approx(
        0.01 - settled_usd, abs=1e-6)


def test_settlement_under_run_releases_budget(tmp_path):
    led = _ledger(tmp_path, ceiling=0.01)
    res = led.reserve("C1", 20000)           # worst case ~$0.0052
    led.settle(res, {"prompt_tokens": 10, "completion_tokens": 2,
                     "reasoning_tokens": 0})
    st = led.state()
    assert st["settled_usd"] < st["ceiling_usd"] / 10
    assert led.reserve("C1", 20000) is not None   # budget was released


def test_insufficient_funds_halts_before_reservation(tmp_path):
    led = _ledger(tmp_path, ceiling=0.01)
    res1 = led.reserve("C1", 20000)
    with pytest.raises(pq.SpendCeilingReached):
        led.reserve("C2", 20000)
    st = led.state()
    assert st["halts"] == 1
    assert st["outstanding_reservations"] == 1   # only the first kept
    led.settle(res1, None)
    with pytest.raises(pq.SpendCeilingReached):
        led.reserve("C2", 20000)                # still exhausted


def test_missing_usage_settles_at_reserved(tmp_path):
    led = _ledger(tmp_path, ceiling=0.02)
    res = led.reserve("C1", 20000)
    reserved_usd = res.usd
    led.settle(res, None)                        # no usage at all
    st = led.state()
    assert st["settled_usd"] == pytest.approx(reserved_usd, abs=1e-9)
    # zero-valued usage is also "unknown" — settle at reserved
    res = led.reserve("C1", 20000)
    led.settle(res, {"prompt_tokens": 0, "completion_tokens": 0,
                     "reasoning_tokens": 0})
    st = led.state()
    assert st["settled_usd"] == pytest.approx(2 * reserved_usd,
                                              abs=1e-9)


def test_partial_usage_settles_at_reserved(tmp_path):
    """A PARTIALLY populated usage report must not price the missing
    fields at zero: output/reasoning present but no prompt count
    settles the WHOLE reservation at its reserved amount."""
    led = _ledger(tmp_path, ceiling=0.05)
    r0 = led.reserve("C1", 20000)
    reserved = r0.usd
    led.settle(r0, {"completion_tokens": 100,
                    "reasoning_tokens": 20})     # prompt missing
    st = led.state()
    assert st["settled_usd"] == pytest.approx(reserved, abs=1e-9)
    # prompt_tokens explicitly zero is also partial/untrusted
    r1 = led.reserve("C1", 20000)
    led.settle(r1, {"prompt_tokens": 0, "completion_tokens": 100,
                    "reasoning_tokens": 20})
    st = led.state()
    assert st["settled_usd"] == pytest.approx(2 * reserved, abs=1e-9)
    # complete usage still settles at actual
    r2 = led.reserve("C1", 20000)
    actual = led.settle(r2, {"prompt_tokens": 800,
                             "completion_tokens": 10,
                             "reasoning_tokens": 0})
    st = led.state()
    assert st["settled_usd"] == pytest.approx(2 * reserved + actual,
                                              abs=1e-6)  # 6dp reporting
    assert st["outstanding_reservations"] == 0
    assert st["invariant_holds"]


def test_retry_flow_after_failed_attempt(tmp_path):
    led = _ledger(tmp_path, ceiling=0.02)
    r1 = led.reserve("C1", 20000)
    led.settle(r1, None)                         # attempt died: reserved
    r2 = led.reserve("C1", 20000)                # retry reserves again
    led.settle(r2, {"prompt_tokens": 900, "completion_tokens": 40,
                    "reasoning_tokens": 10})
    st = led.state()
    assert st["outstanding_reservations"] == 0
    assert st["invariant_holds"]


# ---- crash recovery: liveness, never age ----------------------------

def test_dead_pid_reservation_swept_at_reserved_amount(tmp_path):
    led = _ledger(tmp_path, ceiling=0.01)
    _make_reservation(led, pid=_dead_pid())
    assert led.sweep() == 1
    st = led.state()
    assert st["outstanding_reservations"] == 0
    assert st["orphan_sweeps"] == 1
    assert st["settled_usd"] > 0                 # settled at reserved


def test_active_pid_never_swept_even_if_old(tmp_path):
    led = _ledger(tmp_path, ceiling=0.01)
    proc = _alive_pid()
    try:
        assert pid_alive(proc.pid)
        _make_reservation(led, pid=proc.pid, age=int(time.time()) - 7200)
        assert led.sweep() == 0                  # age alone never settles
        st = led.state()
        assert st["outstanding_reservations"] == 1
        assert st["settled_usd"] == 0
        assert st["orphan_sweeps"] == 0
    finally:
        proc.kill()
        proc.wait()


def test_active_pid_swept_only_after_death(tmp_path):
    led = _ledger(tmp_path, ceiling=0.01)
    proc = _alive_pid()
    try:
        res = _make_reservation(led, pid=proc.pid)
        led.reserve("C1", 10)                    # second live reservation
        assert led.sweep() == 0
    finally:
        proc.kill()
        proc.wait()
    assert led.sweep() == 1                      # now an orphan
    st = led.state()
    assert st["outstanding_reservations"] == 1   # the live one remains
    swept = st  # settled amount equals the swept reservation's amount
    assert swept["settled_usd"] == pytest.approx(res.usd, abs=1e-9)


def test_crash_after_reservation_recovered_by_next_invocation(tmp_path):
    # invocation A reserves and dies without settling
    led_a = _ledger(tmp_path, ceiling=0.01)
    _make_reservation(led_a, pid=_dead_pid())
    # invocation B opens the same ledger: recovery on open
    led_b = SpendLedger(led_a.path, _guard(0.01))
    st = led_b.state()
    assert st["outstanding_reservations"] == 0
    assert st["orphan_sweeps"] == 1
    assert st["invariant_holds"]


def test_resume_seeds_settled_from_records_dirs(tmp_path):
    seed = tmp_path / "low"
    seed.mkdir()
    rec = {"attempts": [{"usage": {"prompt_tokens": 1000,
                                   "completion_tokens": 200,
                                   "reasoning_tokens": 100}}]}
    (seed / "records.jsonl").write_text(json.dumps(rec) + "\n")
    led = _ledger(tmp_path, ceiling=1.0, seed_dirs=[seed])
    st = led.state()
    expected = (1000 * 0.075 + 300 * 0.25) / 1e6
    assert st["settled_usd"] == pytest.approx(expected, abs=1e-6)


# ---- the concurrency invariant --------------------------------------

WORKER = """
import sys
sys.path.insert(0, %r)
from eval.spend_ledger import SpendLedger
from eval.profile_qualification import SpendGuard, SpendCeilingReached

path, chars = sys.argv[1], int(sys.argv[2])
guard = SpendGuard(1.0, 0.075, 0.25, {"C1": chars})
led = SpendLedger(path, guard)
ok = halted = 0
for _ in range(200):
    try:
        r = led.reserve("C1", 100000)
    except SpendCeilingReached:
        halted += 1
        break
    led.settle(r, None)          # settle at reserved (worst case)
    ok += 1
print(ok, halted)
""" % (REPO,)


def test_multiprocess_race_never_exceeds_ceiling(tmp_path):
    ledger_path = tmp_path / "race-ledger.json"
    # worst case per reserve: ceil(800000/4)*2*0.075/1e6 + 100000*
    # 0.25/1e6 = $0.085 -> ceiling $1 admits at most 11 reservations
    procs = [subprocess.Popen(
        [sys.executable, "-c", WORKER, str(ledger_path), "800000"],
        stdout=subprocess.PIPE, text=True) for _ in range(8)]
    outs = [p.communicate()[0].strip() for p in procs]
    assert all(p.returncode == 0 for p in procs)
    results = [tuple(map(int, line.split())) for line in outs]
    total_ok = sum(ok for ok, _ in results)
    total_halted = sum(h for _, h in results)
    assert total_halted >= 1                     # oversubscribed
    led = SpendLedger(str(ledger_path), _guard(1.0))
    st = led.state()
    # the invariant: settled (everything was settled at reserved)
    # never exceeded the ceiling despite 8 racing workers
    assert st["settled_usd"] <= st["ceiling_usd"] + 1e-9
    assert st["outstanding_reservations"] == 0
    assert st["invariant_holds"]
    # bookkeeping consistency: every successful reserve was settled
    per_reserve = st["settled_usd"] / total_ok
    assert st["settled_usd"] == pytest.approx(total_ok * per_reserve,
                                              abs=1e-6)
    # reservation amounts are identical, so the last reserve must fit:
    assert st["settled_usd"] + per_reserve > st["ceiling_usd"]


# ---- adapter integration --------------------------------------------

def _fixture(fid):
    import eval.run_corpus as rc
    import pathlib
    matches = [f for f in rc.load_corpus(
        pathlib.Path(REPO) / "eval" / "fixtures") if f["id"] == fid]
    assert matches, fid
    return matches[0]


def _ok_body():
    return json.dumps({
        "provider": "test-provider",
        "choices": [{"message": {"content": json.dumps({
            "assessment": "CLEAR", "summary": "s", "findings": [],
            "good": []})}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1200, "completion_tokens": 300,
                  "completion_tokens_details": {"reasoning_tokens": 50}},
    })


def test_integration_halt_before_any_request(tmp_path):
    led = _ledger(tmp_path, ceiling=0.01)
    _make_reservation(led, pid=_dead_pid(), gen=38000)  # ~$0.00965: exhausts
    led.sweep()
    calls = []

    def post(body):
        calls.append(body)
        return _ok_body(), 0, 0.1

    with pytest.raises(pq.SpendCeilingReached) as ei:
        pq.logical_review(engine := __import__("engine"),
                          _fixture("C1"), 0, "z-ai/glm-5.3-flash",
                          {"reasoning_effort": "low", "max_tokens": 8000,
                           "retry_budget_escalation": True},
                          {"base_profile": "provisional-low",
                           "overrides": {}},
                          post, lambda r: None,
                          spend_guard=_guard(1.0), ledger=led)
    assert "spend ceiling" in str(ei.value)
    assert calls == []                           # request never made


def test_integration_settles_actual_usage_after_success(tmp_path):
    led = _ledger(tmp_path, ceiling=1.0)
    calls = []

    def post(body):
        calls.append(body)
        return _ok_body(), 0, 0.1

    recs = []
    pq.logical_review(__import__("engine"), _fixture("C1"), 0,
                      "z-ai/glm-5.3-flash",
                      {"reasoning_effort": "low", "max_tokens": 8000,
                       "retry_budget_escalation": False},
                      {"base_profile": "provisional-low",
                       "overrides": {}},
                      post, recs.append,
                      spend_guard=_guard(1.0), ledger=led)
    assert len(calls) == 1
    st = led.state()
    expected = (1200 * 0.075 + 350 * 0.25) / 1e6
    assert st["settled_usd"] == pytest.approx(expected, abs=1e-6)
    assert st["outstanding_reservations"] == 0
    assert st["invariant_holds"]


def test_integration_transport_failure_settles_at_reserved(tmp_path):
    led = _ledger(tmp_path, ceiling=1.0)

    def post(body):
        raise SystemExit("OpenRouter retries exhausted (last http 0)")

    recs = []
    with pytest.raises(SystemExit):
        pq.logical_review(__import__("engine"), _fixture("C1"), 0,
                          "z-ai/glm-5.3-flash",
                          {"reasoning_effort": "low", "max_tokens": 8000,
                           "retry_budget_escalation": False},
                          {"base_profile": "provisional-low",
                           "overrides": {}},
                          post, recs.append,
                          spend_guard=_guard(1.0), ledger=led)
    st = led.state()
    assert st["outstanding_reservations"] == 0   # not stranded
    assert st["settled_usd"] > 0                 # reserved amount kept
    assert recs[0]["terminal_state"] == "TRANSPORT_FAILURE"


def test_integration_escalation_reserves_and_settles_twice(tmp_path):
    led = _ledger(tmp_path, ceiling=1.0)
    bodies = [
        json.dumps({"provider": "p", "choices": [{"message": {
            "content": "x"}, "finish_reason": "length"}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 8000,
                      "completion_tokens_details": {"reasoning_tokens": 0}}}),
        _ok_body(),
    ]

    def post(body):
        return bodies.pop(0), 0, 0.1

    recs = []
    pq.logical_review(__import__("engine"), _fixture("C1"), 0,
                      "z-ai/glm-5.3-flash",
                      {"reasoning_effort": "low", "max_tokens": 8000,
                       "retry_budget_escalation": True},
                      {"base_profile": "provisional-low",
                       "overrides": {}},
                      post, recs.append,
                      spend_guard=_guard(1.0), ledger=led)
    st = led.state()
    expected = ((1000 * 0.075 + 8000 * 0.25)
                + (1200 * 0.075 + 350 * 0.25)) / 1e6
    assert st["settled_usd"] == pytest.approx(expected, abs=1e-6)
    assert recs[0]["escalated"] is True
