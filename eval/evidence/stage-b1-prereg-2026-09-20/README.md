# Stage B1 preregistration — rubric calibration screen (DRAFT FOR HUMAN REVIEW)

**Status: preregistration only. No paid execution is authorized by
this document.** Execution (phase 06) requires: maintainer approval
of this frozen package, a rotated OpenRouter API key, an explicit
live-spend authorization, and the aggregate spend-ceiling
implementation. Directed 2026-09-20 after the C11/M11 oracle repair
(PR #80, merge `f9168cf`).

## Objective and hypothesis

B0 (`stage-b0-attribution-2026-09-19`) identified a combined
**evidence-threshold and severity-calibration failure**: 20 findings
rest on invented or unsupported claims, 18 inflate advisory-grade
observations, and 14 follow rubric-invited blocking categories. The
rubric licenses "missing tests for core behavior" and "scope
violation" and places no diff-demonstrability burden on blockers.

**H1 (single intervention):** amending only the rubric's
severity/blocking rules — demonstrability, external-fact precision,
diff-introduced claims, missing-tests default, description-mismatch
default — eliminates control false-blocks **without losing paired-
positive detection**. Fixtures, states, harness, engine, transport:
frozen. `rubric.md` is the only subject file touched at execution.

## Identity pins (frozen by this package)

- `oracle_version`: **`5472d990f3b946c3`** (post-repair; must NOT
  move — a rubric change is a subject change, and the existing test
  asserts rubric changes never move oracle_version).
- Subject revision: `rubric-revised.md` in this directory,
  sha256 **`f13db50022cab1f498c13c1abdb802e1a3624c33bae28ab2c31c32b12f407e37`**
  (`rubric-diff.patch` is the complete change: one rule block
  replaced in Judgment rules; every other line byte-identical;
  verified to apply onto the live `rubric.md` and reproduce this
  file byte-for-byte). The **claims** rule now has two explicit
  failure modes: (i) a *central, unsubstantiated absolute guarantee
  about code outside the diff* may be blocked — unverifiability
  itself is the defect (this is M4's expected finding, preserved);
  (ii) a *contradicted or narrower claim* is severity-gated by the
  normal bar (broken/unsafe → blocking; functional-but-different →
  advisory — this is C13 going CLEAR); an explicitly self-scoped
  claim (C4's docstring) is neither failure mode.
  Execution must apply this file byte-for-byte as `rubric.md`; the
  campaign identity's `rubric_sha256`/`subject_content_ref` must
  match the applied tree. Engine prompt golden hashes will be
  regenerated in the execution phase (the rubric feeds prompts);
  that regeneration is mechanical and reviewed there.
- Model: `z-ai/glm-5.3-flash`, efforts **low and high only**
  (max is independently disqualified on cost/latency/discrimination;
  Stage A evidence), budget 8000 with ≤1 escalation to 16000, N=3.

## Matrix (15 fixtures × N=3 × 2 efforts = 90 logical reviews)

- Recurrent false-positive controls (B0): **C2, C3, C12, C13, C16**
- The independent D2 cause: **C4**
- Never-blocked controls: **C1, C5, C14**
- Paired positives: **M2, M3, M4, M12, M13, M16**
- **C8 excluded** — pending independent adjudication; its B0
  findings remain on record and it stays out of qualification sets
  until ruled on.

Balanced run order (all three runs defined): run 0 evaluates each
fixture low→high, run 1 high→low, run 2 low→high — every effort
gets N=3 runs per fixture (45 per effort), and effort order
alternates across invocations (low is first in two of three rounds;
perfect order balance is impossible with an odd N). One evidence directory per effort, campaign
identity per directory, provider routing recorded and unpinned.

## Aggregate spend-ceiling design (fixes the Stage-A scope flaw)

Stage A disclosed that the seeded ceiling enforced per
effort-directory. B1 uses a **campaign-aggregate ledger** with
**atomic reservation** — the invariant is that no two requests can
ever pass a ceiling check against the same budget:

- `spend-ledger.json` at the campaign root holds
  `{settled: {prompt_tokens, output_tokens, usd}, reservations: [...]}`;
  every read-modify-write happens under an exclusive `fcntl` lock on
  a sibling `.lock` file and persists by atomic rename before the
  lock is released.
- **Pre-request reserve**: the worst-case cost bound for the next
  request is checked AND reserved under one lock acquisition
  (`reserve(amount) -> ok | halt`); the reservation — `{id, pid,
  created_at, amount}` — is persisted before the request starts. A
  `halt` fires `SpendCeilingReached` before any HTTP request; a
  concurrent invocation can never see budget already reserved.
- **Settlement**: when the request completes, `settle(id, actual)`
  runs under the same lock: the reservation is removed and the
  delta (actual − reserved, signed) applied to `settled`; under-runs
  release budget back.
- **Crash recovery (fail closed)**: on startup an invocation sweeps
  reservations whose `pid` is no longer alive or older than a 30 min
  stale bound (> max observed request wall) and settles them at
  their reserved amount — an orphaned reservation is counted as
  spent, never silently released, so crashes can only under-spend
  the accounting, never over-run the ceiling.
- Ceiling: **$1.00 aggregate** across both efforts (~16× the
  projected ≈$0.06 from Stage-A unit costs; still fails fast on
  retry storms). Halt = `SpendCeilingReached`, campaign incomplete,
  resumable (pending reservations swept first), reported — never D1.
- **Implementation gate (phase 06)**: the invariant is proven by a
  concurrency test — N workers racing `reserve` under the lock, the
  sum of successful reservations plus settled spend must never
  exceed the ceiling. A successful single-process test does NOT
  establish this and will not be accepted as evidence.

## Pass criteria (preregistered; all gating criteria must hold)

1. **Zero control false-blocks**: no `blocking`-severity finding on
   any of the 9 control fixtures in any of the 54 control reviews
   (this subsumes the GATING members C4 and C5 — **no GATING
   regression**; C7 is not in the matrix and unchanged).
2. **No paired-positive detection loss, group-wise, per effort**:
   for every positive and every expected group, B1 detection count
   (of 3 runs) ≥ the Stage-A baseline at the same effort
   (`baseline-stage-a.json`, pinned). Baseline highlights: M2 group
   0 is 1/3 at low and 0/3 at high — group-wise no-regression
   applies.
3. **Viability**: INCONCLUSIVE ≤ 10% of 90 reviews; zero unresolved
   transport failures; post-escalation exhaustion ≤ 5% of
   escalations.
4. **M4 and M13 reported separately** — both had **zero baseline
   detection at both efforts**, so criterion 2 is trivially
   satisfied for them and cannot hide a continued miss behind a
   pass. Their B1 detection counts are reported standalone; B1 PASS
   is not evidence of M4/M13 capability (humility rule).
5. Informational, non-gating: **subset-matched blocking-finding
   burden on positives** (not an oracle-classified false-block count)
   — within the frozen Stage-A records restricted to the
   six B1 positives, 15/18 (low) and 17/18 (high) OK_CONTENT
   positive runs emitted ≥1 blocking finding (21 and 26 blocking
   findings respectively; see `baseline-stage-a.json`). The
   published Stage-A figures 5/11 cover all 18 positives and are
   **NOT comparable** to B1 — recorded only as context. The B1
   blocking-finding burden is reported descriptively; a lower count
   alone is not proof of improved correctness and is not required
   to pass.
   Provider distribution, token usage, and actual cost are reported.

**Decision rule**: all gating criteria hold → B1 PASS, which
**permits preparation of a separate Stage B2 preregistration** —
the full 36-fixture corpus (18 controls + 18 positives) × N=3 ×
{low, high} = 216 logical reviews under the revised subject and
oracle `5472d990…` (new subject identity). B2 execution and spend
are NOT authorized by a B1 pass; B2 gets its own frozen package,
review, and live-spend gate. Any B1 gating failure → revise the
hypothesis and re-preregister; no matrix or criteria tweaks after
first result.

## Stop conditions

- Any ceiling halt, transport-failure halt, or identity mismatch
  (campaign.json vs this package's pins) → stop, report, human
  direction.
- C8 stays excluded and unresolved; the deployed GLM profile stays
  **non-authoritative** regardless of outcome.
- Prerequisites before any run: this package approved (possibly with
  edits — approval pins the edited sha256), API key rotated,
  explicit live authorization, aggregate-ledger implementation
  merged and tested.

## Addendum (2026-09-20, phase-06 review direction)

**Crash-recovery refinement**: recovery is **liveness-only**. A
reservation is swept (settled at its reserved amount) exclusively
when its owning pid is no longer alive. Age alone — however large —
never settles an active request: a 30-minute-old reservation with a
live pid stays outstanding, so an active request can never be
double-accounted or have its budget wrongly released. Age remains
recorded for diagnostics. The "30 min stale bound" in the section
above is superseded by this rule; fail-closed direction is
unchanged (orphaned outcomes count as spent, never released).

The aggregate-ledger implementation and its test matrix (including
explicit process-liveness and active-recovery cases) are delivered
in phase 06.
