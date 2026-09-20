# Stage B1 preregistration — rubric calibration screen (DRAFT FOR HUMAN REVIEW)

**Status: preregistration only. No paid execution is authorized by
this document.** Execution (phase 06) requires: maintainer approval
of this frozen package, a rotated OpenRouter API key, an explicit
live-spend authorization, and the aggregate spend-ceiling
implementation. Directed 2026-09-20 after the C11/M11 oracle repair
(PR #80, merge `f9168cf`).

## Objective and hypothesis

B0 (`stage-b0-attribution-2026-09-20`) established that GLM-5.3-flash's
false blocks are **severity-policy failures, not perception
failures**: the rubric's blocking rule invites two over-trigger
categories ("missing tests for core behavior", "scope violation")
and places no diff-demonstrability burden on blocking claims.

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
  sha256 **`993aa79db515cde92ddf9e62668921faf190858f94224c50e79b940267392bab`**
  (`rubric-diff.patch` is the complete change: one rule block
  replaced in Judgment rules; every other line byte-identical).
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

Balanced cyclic run order per fixture as in Stage A (run 0
low→high, run 1 high→low), one evidence directory per effort,
campaign identity per directory, provider routing recorded and
unpinned.

## Aggregate spend-ceiling design (fixes the Stage-A scope flaw)

Stage A disclosed that the seeded ceiling enforced per
effort-directory. B1 uses a **campaign-aggregate ledger**:

- `spend-ledger.json` at the campaign root holds cumulative
  `{prompt_tokens, output_tokens, usd}`; mutated only under an
  exclusive `fcntl` lock on a sibling `.lock` file, persisted by
  atomic rename after every persisted record.
- Each invocation seeds its `SpendGuard` from the ledger (plus its
  own directory's records for identity-protected recomputation) and
  checks the worst-case pre-request bound against the **shared**
  ceiling.
- Ceiling: **$1.00 aggregate** across both efforts (~16× the
  projected ≈$0.06 from Stage-A unit costs; still fails fast on
  retry storms). Halt = `SpendCeilingReached`, campaign incomplete,
  resumable, reported — never D1.

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
5. Informational, non-gating: false-blockers-on-positives vs
   baseline (low 5 / high 11 — expected to fall, not required);
   provider distribution; token usage; actual cost.

**Decision rule**: all gating criteria hold → B1 PASS, which
authorizes **Stage B2**: full 18-fixture × N=3 × {low, high}
qualification of the revised subject under oracle `5472d990…` (new
subject identity), preregistered separately. Any gating failure →
revise the hypothesis and re-preregister; no matrix or criteria
tweaks after first result.

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
