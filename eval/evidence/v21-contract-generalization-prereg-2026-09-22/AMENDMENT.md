# 18C — reviewed holdout amendment record

Amendment-only change under the 18A `PROTOCOL.md` clause: "fixture
content or labels may change only for an independently demonstrated
fixture defect, via a reviewed amendment that names the fixture and
the defect explicitly." Authorization: human merge review of PR #95
(final Phase-18B interpretation: **0 PASS, 4 FAIL, 2 INVALID**).

## Amended pairs (exactly two; nothing else touched)

1. **psd-P4 / psd-C4** — defect: authored refs were not consistently
   40-hex commit SHAs. The frozen 18B `fixture_defects` artifact
   mechanically records P4's removed ref at length `[39]`. During the
   reviewed 18C pre-evaluation amendment inspection, the original pair
   was additionally checked directly and showed non-40-hex runs in
   both members. Correction: every ref in both fixtures replaced with
   a genuine 40-hex SHA; the intended
   pin→mutable-branch vs re-pin semantic distinction is unchanged.
2. **jfu-P5 / jfu-C5** — defect: the positive tested `jq 'length > 0'`
   over JSONL, outside the frozen relation definition (unslurped
   `.[]` array consumer). Correction: P5 replaced with a
   frozen-definition positive — added JSONL producer
   (`jq -c '.stages[]' … >>"$stages_jsonl"`) plus unslurped
   `any(.[]; .failed)` consumer; C5 updated to its semantic
   near-miss (identical producer, names, and guard shape; only the
   slurp differs).

Labels are re-asserted from the frozen definitions before any
evaluation: amended positives → ADMITS, amended controls → REFUSES.
`probe` flags: unchanged pairs untouched; amended jfu-P5 is
in-definition (`probe: false`).

Hashes refreshed: the four fixture files above, their `MANIFEST.json`
entries, `manifest_lines_sha256`, and the independent full-manifest
SHA-256 pin in `tests/test_v21_generalization_prereg.py`. No other
fixture, no label of an unamended pair, no evidence artifact, and —
binding for this phase — **no verifier execution of any kind**: the
Phase-17 relations module is not called on the holdout in 18C, and
the 18B evaluator is not run.

## Frozen Phase-18D rerun procedure (preregistered now)

Subject: the same frozen Phase-17 verifier
(`eval/v21_contract_relations.py`, sha256 `bb0ebdeeb7fc80395626bf10d3
e9ad1a730936ccf0ab7e719c43c1b5754b1b57`, merge
`0631b0956f795ab1ee6d13f68b0c1cebe8a6d23b`). No verifier edit before
or during 18D.

1. **Amended-pair evaluation**: run the frozen verifier on exactly
   the four amended fixtures (psd-P4, psd-C4, jfu-P5, jfu-C5).
2. **Full reconciliation run**: one full deterministic evaluation of
   all 60 fixtures must reproduce the 18B observations exactly
   on the 56 unchanged fixtures (per-fixture admitted flags and
   fired-relation sets). Any divergence is a halt condition — recorded
   as INVALID/halt, never reconciled silently.
3. **Combination**: per relation, the final scored population is all
   5 positives and 5 controls (18B valid observations for unchanged
   pairs + 18D results for the amended pairs, identical to the
   reconciliation run by determinism).
4. **Thresholds unchanged**: control leakage must be 0/5; positive
   recall ≥ 4/5; PASS/FAIL verdicts assigned per the 18A protocol.
   Final expected headline space: psd and jfu resolved to PASS or
   FAIL; pcd/cbv/sle/dsc remain FAIL — no re-evaluation, no
   re-interpretation, no tuning opportunity.
5. **Publication**: a new Phase-18D report (fixture-level JSON +
   RESULTS-18D.md) is published and test-bound to evaluator output;
   the Phase-18B report file remains frozen as the historical record.
6. **No relation may be changed in response to 18D behavior.** A
   failure is evidence, not a patch request.

Standing regression invariants (C11 refused; C10 near-miss standing
against the FAILED M10 relation; M3 admitted; M13 refused; C12/M12
refused; oracle `117b4164e5446f50`) remain 18D harness guards.
