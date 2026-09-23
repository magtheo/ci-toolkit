# Phase 18D — amended-pair evaluation and reconciliation result

Execution of the frozen 18C rerun procedure (`AMENDMENT.md` in the
holdout directory): evaluate the four amended fixtures with the
unchanged Phase-17 verifier, then run the full 60-fixture
reconciliation. Method: `python3 eval/v21_generalization_eval.py`
(`evaluate_amended_pairs()` for step 1, `evaluate()` for step 2). The
Phase-17 verifier was called, never modified (`bb0ebdee…` verified
in-run by fail-closed checks); fixture files were read, never
written. Full fixture-level data: `generalization-report-18d.json`.

## Reconciliation (halt gate)

All **56 unchanged fixtures** reproduce the frozen 18B observations
**exactly** — same `admitted` flag and same `fired_relations` set,
fixture by fixture, against the SHA-pinned 18B report
(`a56235b5…`). Zero mismatches; the mechanical halt gate did not
trigger. The 18B failure taxonomy carries over unchanged for the four
FAIL relations.

## Amended-pair outcomes

| fixture | relation | expected | verifier | observed |
|---|---|---|---|---|
| `psd-P4` | `pinned_sha_demoted_to_branch` | ADMITS | fires relation | **admitted** |
| `psd-C4` | `pinned_sha_demoted_to_branch` | REFUSES | fires nothing | **refused** |
| `jfu-P5` | `jsonl_format_vs_unslurped_jq` | ADMITS | fires nothing | **not admitted** |
| `jfu-C5` | `jsonl_format_vs_unslurped_jq` | REFUSES | fires nothing | **refused** |

- psd: the amended pair is clean — P4 admits, C4 refuses. Completing
  the 18B valid subset (4/4 · 0/4), psd scores **5/5 positives,
  0/5 controls**.
- jfu: the amended P5 is in-definition (added JSONL producer +
  unslurped `any(.[]; .failed)` consumer) but the frozen relation
  does not fire. Completing the 18B valid subset (3/4 · 0/4), jfu
  scores **3/5 positives, 0/5 controls**.

## Final verdicts (frozen thresholds, unchanged: ≥4/5 positives, 0/5 controls)

| relation | positives | controls | verdict |
|---|---:|---:|---|
| `pinned_sha_demoted_to_branch` | 5/5 | 0/5 | **GENERALIZATION PASS** |
| `preserved_claim_vs_dropped_call_result` | 3/5 | 0/5 | GENERALIZATION FAIL |
| `consume_before_validate_ordering` | 1/5 | 0/5 | GENERALIZATION FAIL |
| `secret_logged_by_echo` | 3/5 | **1/5** | GENERALIZATION FAIL |
| `doc_self_contradiction` | 2/5 | **2/5** | GENERALIZATION FAIL |
| `jsonl_format_vs_unslurped_jq` | 3/5 | 0/5 | GENERALIZATION FAIL |

**Aggregate: 17/30 positives admitted, 3/30 controls admitted.
Final relation states: 1 PASS, 5 FAIL → no blanket promotion**
(`blanket_promotion_eligible: false`). Standing regression guards all
held (C11 refused; C10 standing near-miss against the still-FAILED
M10 relation; M3 admitted via the existing witness; M13 refused;
C12/M12 refused; oracle `117b4164e5446f50`).

## Why the amended jfu-P5 does not fire (characterization only)

The frozen M6-family matcher accepts a bare `jq …` consumer and the
negated guard forms `! jq …` / `if ! jq …`, but its line-prefix
regex does **not** accept the affirmative conditional form
`if jq …`. The amended P5 uses exactly that semantically valid
affirmative guard (`if jq -e 'any(.[]; .failed)' <"$stages_jsonl"`
— "if any stage failed, fail"). Every other required element is
present: same-file JSONL producer (`>>"$stages_jsonl"`), array
filter, variable read, and no slurp. The relation therefore fails to
generalize to the affirmative-`if` guard form. This is
recorded as evidence of the frozen relation's recall boundary; per
the frozen procedure, **no relation may be changed in response to
18D behavior** — any guard-polarity extension is future preregistered
work, subject to the full qualification methodology including new
near-miss controls.

## Scope and humility

This run resolves psd and jfu — and only psd and jfu — against the
frozen Phase-17 verifier, exactly as preregistered. Per the standing
humility rule, PASS is scoped to this oracle (this harness, corpus,
and GATING state): it is a measured qualification record, not a
correctness claim about any subject. The historical 18B artifacts
(`RESULTS-18B.md`, `generalization-report.json`) remain byte-for-byte
unchanged.
