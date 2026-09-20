"""Shared campaign spend ledger with atomic reservation.

Invariant (preregistered Stage B1, $1.00 aggregate ceiling):

    settled spend + outstanding reservations <= ceiling

at every instant, across concurrent invocations and across crashes.

Mechanics
---------
- Every read-modify-write of the ledger file happens under an
  exclusive fcntl lock on a sibling `.lock` file; state is persisted
  by atomic rename BEFORE the lock is released.
- `reserve()` is the only path to a provider request: the worst-case
  cost bound of the next request is checked AND recorded as an
  outstanding reservation under ONE lock acquisition, so two
  concurrent invocations can never both pass a check against the
  same budget.
- `settle()` replaces a reservation with actual usage (signed delta:
  under-runs release budget back). Missing or unusable usage data is
  settled at the reserved amount — fail closed: unknown usage can
  only over-count spend, never under-count it.
- Crash recovery is liveness-based, never age-based: a reservation
  whose owning pid is no longer alive is an orphan and is settled at
  its reserved amount; a reservation whose pid IS alive stays
  outstanding no matter how old it is — a slow but active request is
  never double-settled and never has its budget wrongly released.
  Age is recorded for diagnostics only.
- On first creation the ledger seeds `settled` from the campaign's
  existing records directories (resume-safety when a crash happened
  before the ledger existed).
"""

import contextlib
import fcntl
import json
import os
import time
import uuid


def pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Reservation:
    def __init__(self, rid, pid, created_at, in_tokens, out_tokens, usd):
        self.id = rid
        self.pid = pid
        self.created_at = created_at
        self.in_tokens = in_tokens
        self.out_tokens = out_tokens
        self.usd = usd


class SpendLedger:
    """Shared ceiling authority. `guard` is the per-process SpendGuard
    whose worst-case cost model and conservative price assumptions the
    ledger reuses verbatim — one cost model, two scopes."""

    def __init__(self, path, guard, seed_dirs=()):
        self.path = os.fspath(path)
        self.guard = guard
        self.lock_path = self.path + ".lock"
        self.seed_dirs = [os.fspath(d) for d in seed_dirs]
        self._state = self._open()

    # ---- persistence -------------------------------------------------

    def _empty(self):
        return {"settled_in_tokens": 0, "settled_out_tokens": 0,
                "reservations": [], "halts": 0, "swept_orphans": []}

    def _seed_from_records(self):
        """Initial settled totals from persisted records (tokens)."""
        import pathlib
        in_t = out_t = 0
        for d in self.seed_dirs:
            rp = pathlib.Path(d) / "records.jsonl"
            if not rp.exists():
                continue
            for line in rp.read_text().splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                for a in r.get("attempts") or []:
                    u = a.get("usage") or {}
                    in_t += u.get("prompt_tokens") or 0
                    out_t += ((u.get("completion_tokens") or 0)
                              + (u.get("reasoning_tokens") or 0))
        return in_t, out_t

    def _open(self):
        if os.path.exists(self.path):
            with open(self.path) as fh:
                return json.load(fh)
        state = self._empty()
        if self.seed_dirs:
            (state["settled_in_tokens"],
             state["settled_out_tokens"]) = self._seed_from_records()
        self._write(state)
        return state

    def _write(self, state):
        tmp = "%s.tmp.%d" % (self.path, os.getpid())
        with open(tmp, "w") as fh:
            json.dump(state, fh, indent=1)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)

    @contextlib.contextmanager
    def _locked(self):
        """Exclusive access: read fresh state, yield, ALWAYS persist
        and release — including when the body raises (a halt counted
        inside a raising reserve() must still reach disk)."""
        fh = open(self.lock_path, "a+")
        try:
            fcntl.flock(fh, fcntl.LOCK_EX)
            state = self._open()
            try:
                yield state
            finally:
                self._write(state)
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
            fh.close()

    # ---- accounting view ---------------------------------------------

    def _reserved_usd(self, state):
        return sum(r["usd"] for r in state["reservations"])

    def _committed_usd(self, state):
        return self.guard.cost_usd_of(state["settled_in_tokens"],
                                      state["settled_out_tokens"])

    # ---- crash recovery ---------------------------------------------

    def _sweep(self, state):
        """Settle orphans: reservations whose pid is no longer alive.
        Liveness-only — an active request is never settled for being
        old. Orphans are settled at their reserved amount (fail
        closed: an unknown outcome can only over-count spend)."""
        orphans = [r for r in state["reservations"]
                   if not pid_alive(r["pid"])]
        for r in orphans:
            state["reservations"].remove(r)
            state["settled_in_tokens"] += r["in_tokens"]
            state["settled_out_tokens"] += r["out_tokens"]
            r["swept_at"] = int(time.time())
            state["swept_orphans"].append(r)
        return len(orphans)

    def sweep(self):
        with self._locked() as st:
            return self._sweep(st)

    # ---- the only path to a provider request ------------------------

    def reserve(self, fixture_id, gen_budget):
        """Check the worst-case bound for the next request and record
        it as an outstanding reservation under one lock acquisition.
        Raises SpendCeilingReached (no reservation kept) when the
        invariant would be violated."""
        from eval.profile_qualification import SpendCeilingReached
        worst_in = self.guard._est_input(fixture_id)
        worst_out = gen_budget
        worst_usd = (worst_in * self.guard.p_in
                     + worst_out * self.guard.p_out) / 1e6
        with self._locked() as st:
            self._sweep(st)
            committed = self._committed_usd(st)
            outstanding = self._reserved_usd(st)
            if committed + outstanding + worst_usd > self.guard.ceiling:
                st["halts"] = st.get("halts", 0) + 1
                raise SpendCeilingReached(
                    "aggregate spend ceiling: settled $%.4f + "
                    "outstanding $%.4f + worst-case next $%.4f > "
                    "ceiling $%.2f — halting BEFORE the request "
                    "(ledger %s); the campaign is resumable pending "
                    "human direction"
                    % (committed, outstanding, worst_usd,
                       self.guard.ceiling, self.path))
            res = Reservation(str(uuid.uuid4()), os.getpid(),
                              int(time.time()),
                              worst_in, worst_out, worst_usd)
            st["reservations"].append({
                "id": res.id, "pid": res.pid,
                "created_at": res.created_at,
                "in_tokens": res.in_tokens,
                "out_tokens": res.out_tokens, "usd": res.usd,
                "fixture": fixture_id,
            })
            return res

    def settle(self, reservation, usage_facts):
        """Replace a reservation with actual usage. `usage_facts` None
        or without at least one strictly-positive token count settles
        at the reserved amount (fail closed: an all-zero usage report
        is indistinguishable from missing usage and can only
        under-count — never trust it). Signed delta: an under-run
        releases budget back. Returns the settled USD amount."""
        with self._locked() as st:
            for r in st["reservations"]:
                if r["id"] == reservation.id:
                    st["reservations"].remove(r)
                    if usage_facts and any(
                            (usage_facts.get(k) or 0) > 0 for k in
                            ("prompt_tokens", "completion_tokens",
                             "reasoning_tokens")):
                        in_a = usage_facts.get("prompt_tokens") or 0
                        out_a = ((usage_facts.get("completion_tokens")
                                  or 0)
                                 + (usage_facts.get("reasoning_tokens")
                                    or 0))
                    else:
                        in_a, out_a = r["in_tokens"], r["out_tokens"]
                    st["settled_in_tokens"] += in_a
                    st["settled_out_tokens"] += out_a
                    return self.guard.cost_usd_of(in_a, out_a)
            raise KeyError("unknown reservation %s" % reservation.id)

    # ---- reporting ---------------------------------------------------

    def state(self):
        with self._locked() as st:
            self._sweep(st)
            settled = self._committed_usd(st)
            outstanding = self._reserved_usd(st)
            return {
                "ledger_path": self.path,
                "settled_usd": round(settled, 6),
                "outstanding_reservations": len(st["reservations"]),
                "outstanding_usd": round(outstanding, 6),
                "ceiling_usd": self.guard.ceiling,
                "remaining_usd": round(
                    self.guard.ceiling - settled - outstanding, 6),
                "invariant_holds": (
                    settled + outstanding <= self.guard.ceiling + 1e-9),
                "halts": st.get("halts", 0),
                "orphan_sweeps": len(st["swept_orphans"]),
                "recovery_rule": "liveness-only: dead-pid reservations "
                                 "settle at reserved amount; active "
                                 "pids are never swept for age",
            }
