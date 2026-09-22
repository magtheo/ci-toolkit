# PREREGISTRATION — v2 declaration regression freeze (post-trial)

Status: **preregistered 2026-09-22, before any v2.1 design work.**
Reviewed via the PR that introduces this directory; the merge is what
makes the freeze effective. Required by the frozen trial governance
(`eval/evidence/v2-trial-glm-2026-09-22/ADJUDICATION.md`,
"Consequences and next step"): regression cases are frozen BEFORE any
boundary fix.

## Purpose

Pin the exact parser/gate behavior observed on the five adjudicated
trial outcomes so that the planned v2.1 design (typed evidence roles)
— and any other change to `parse_review.py`, the gate, or the trial
response schema — **cannot silently change behavior on the confirmed
declaration-failure patterns or on the good-control patterns**. The
freeze is the regression baseline v2.1 must be measured against.

## Scope — exactly five cases, sourced verbatim

Three confirmed declaration failures (adjudication: S2/S1):

| case | fixture | verdict |
|---|---|---|
| `C11-fabricated-contract-contradiction` | C11 | `HARM_FABRICATED` (S1 control survivor) |
| `M3-context-only-evidence-quote` | M3 | `QUOTE_AS_CONTEXT` |
| `M13-external-fact-extrapolation` | M13 | `HARM_FABRICATED` |

Two good boundary controls (adjudication: S3):

| case | fixture | fact pinned |
|---|---|---|
| `C12-honest-uncertainty-downgrade` | C12 | honest `presumed`/`out_of_diff_assumption` declaration → correct downgrade, assessment recomputed CLEAR |
| `M12-contiguous-quote-downgrade` | M12 | non-contiguous quote → correct `quote_in_patch` downgrade beside a HONEST survivor |

Each case file (`cases/*.json`) carries:

- `source.record_line_sha256` — sha256 of the exact line in the
  published `eval/evidence/v2-trial-glm-2026-09-22/records.jsonl`;
- `raw_model_output` — verbatim model output (byte-equality asserted
  against the published record, both directions);
- `expected_result` — the complete frozen normalized ReviewResult;
- `expected_gate_audit` — the frozen per-check gate audit;
- `oracle_group_matched` — the mechanically pinned detection fact for
  positives (M3 `true`, M12 `true`, M13 **`false`** — the frozen @v4
  defect was missed even though a blocker survived);
- `verdict` / `notes` — the human adjudication, recorded as CONTEXT.
  Verdicts are never asserted in code: the honesty layer belongs to
  the frozen protocol, the parser layer to these pins.

## What freezing means (the rule any future change must satisfy)

`tests/test_v2_regression_freeze.py` re-runs `parse_review.normalize_v2`
on each frozen raw output against the corresponding corpus fixture's
diff and asserts **exact equality** with `expected_result` and
`expected_gate_audit`, plus the pinned `oracle_group_matched` facts
and the published-record linkage above. Therefore:

1. Any parser/gate/schema change that alters normalized output on
   these inputs FAILS the suite.
2. An intentional behavior flip is permitted only through a reviewed
   amendment to THIS preregistration that names the flipped cases and
   the new expected outputs — committed together with the change that
   causes them.
3. The honesty verdicts (HARM_FABRICATED etc.) are NOT pins: v2.1 may
   well make the gate stop a C11-style survivor — that is a desired
   flip and must arrive through rule 2, naming the case.

## Non-goals (this phase)

- No boundary fix, no schema change, no rubric change, no prompt
  change.
- No corpus/states/oracle change: the oracle content hash stays
  `117b4164e5446f50` (asserted by the freeze tests — the freeze is
  subject-side and must not move oracle identity).
- No provider calls; no promotion; the v2 boundary stays **default
  OFF and non-promotable**.
- No edit to any published trial artifact (`ADJUDICATION-EXTRACT.md`,
  `records.jsonl`, `trial-state.json`, `README.md` are untouched; the
  S2/S3 completion lives in the new `ADJUDICATION.md`).
