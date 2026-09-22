# Phase 18B — out-of-sample generalization result

First evaluation of the six frozen Phase-17 relations against the
preregistered 18A holdout (60 unseen fixtures). Method:
`python3 eval/v21_generalization_eval.py`, implementing the
operationalization and thresholds frozen in the 18A `PROTOCOL.md`
**before** any run. Full fixture-level data:
`generalization-report.json`. The Phase-17 verifier was called, never
modified; fixture files were read, never written.

## Verdicts

| relation | positives | controls | verdict |
|---|---:|---:|---|
| `pinned_sha_demoted_to_branch` | 4/4 scored (P4/C4 INVALID) | 0/4 scored | **INVALID_PENDING_AMENDMENT** |
| `preserved_claim_vs_dropped_call_result` | 3/5 | 0/5 | GENERALIZATION FAIL |
| `consume_before_validate_ordering` | 1/5 | 0/5 | GENERALIZATION FAIL |
| `secret_logged_by_echo` | 3/5 | **1/5** | GENERALIZATION FAIL |
| `doc_self_contradiction` | 2/5 | **2/5** | GENERALIZATION FAIL |
| `jsonl_format_vs_unslurped_jq` | 3/4 scored (P5/C5 INVALID) | 0/4 scored | **INVALID_PENDING_AMENDMENT** |

**Scored aggregate: 16/28 positives admitted, 3/28 controls admitted;
raw observations remain 16/30 and 3/30. Final relation states:
0 PASS, 4 FAIL, 2 INVALID → no blanket promotion.**
Standing regression guards all held (C11 refused; C10 standing
near-miss against the still-FAILED M10 relation; M3 admitted via the
existing witness; M13 refused; C12/M12 refused; oracle
`117b4164e5446f50`).

## INVALID pairs

The frozen 18A protocol says a discovered fixture/oracle defect marks
the **pair INVALID**, is never counted as verifier success or failure,
and requires a reviewed amendment before rerun. Therefore neither
affected relation receives a PASS/FAIL verdict in this phase.

- `psd-P4/C4`: P4's authored "pinned" ref is 39 hex chars rather than
  a 40-hex commit SHA. Mechanical proof is recorded in
  `fixture_defects`. The valid observed psd subset is 4/4 positives
  and 0/4 controls, but the preregistered 4/5-or-5/5 threshold may not
  be rewritten to 4/4 post hoc. Verdict:
  **INVALID_PENDING_AMENDMENT**.
- `jfu-P5/C5`: P5 tests `jq 'length > 0'` over JSONL, but the frozen
  Phase-17/18A relation definition is specifically an unslurped
  **array-filter (`.[]`) consumer**. This is an 18A scope-authoring
  defect, not a verifier miss. The valid observed jfu subset is 3/4
  positives and 0/4 controls. Verdict:
  **INVALID_PENDING_AMENDMENT**.

Correction requires a reviewed holdout amendment and rerun of the
affected pair(s); nothing in the frozen verifier may be changed.

## Exact failed fixtures

- psd: P4/C4 → INVALID pair; no PASS/FAIL verdict
- pcd: P3, P4 — both **predeclared scope probes** (requests/httpx);
  in-scope urlopen semantics: 3/3
- cbv: P2, P3, P4, P5 — all **predeclared scope probes** (setter
  method, non-`.state` properties, Python `None`); original
  `.state = null` shape: 1/1
- sle: P4, P5 (predeclared probes: f-string, `console.log`) plus
  **control leak sle-C3** (fingerprint near-miss)
- dsc: P3, P4, P5 (in-scope positives) plus **control leaks dsc-C1,
  dsc-C2** (scoped-exception controls)
- jfu: P2 (predeclared probe: single-redirect producer); P5/C5 are an
  INVALID pair because P5 is outside the frozen `.[]` relation scope

## Failure taxonomy (preregistered classification)

1. **Syntactic/brittleness — 9 fixtures, all flagged `probe: true` in
   18A**: the frozen implementations recognize only the original
   corpus surface shapes (bare `urllib.request.urlopen`, literal
   `.state = null`, `echo`/`printf`/`print`/`log*` with `$VAR`,
   `>>`-redirect jq producers). The semantic cores they do recognize
   held with zero control leakage in-scope (pcd 3/3, cbv 1/1, jfu
   array-iteration 3/3).
2. **Semantic over-trigger — 3 fixtures, all control leaks.** This is
   the study's deepest finding: `secret_logged_by_echo` admits
   `sle-C3` because a *variable named* `VAULT_KEY_FP` matches the
   name-based proxy even though the logged value is a non-reversible
   fingerprint; `doc_self_contradiction` admits `dsc-C1`/`dsc-C2`
   because universal-word + exception-word *co-occurrence* fires on
   scoped, compatible exceptions. Both relations passed their
   same-corpus pair test in Phase 17; unseen near-miss controls
   exposed false-positive modes that in-corpus controls never
   embodied. Indirect proxies (name matching, co-occurrence) passed
   the pair test and still do not carry the semantics.
3. **Vocabulary narrowness — 3 fixtures (dsc-P3/P4/P5)**: in-scope
   contradictions whose exception wording (`purged`, `renewed`,
   `rejected`) falls outside the frozen `bypass|approval|unless|
   manual` set. In-scope but unrecognized — brittleness on the
   contract side.
4. **Authoring defects — 2 pairs**: psd-P4/C4 (39-hex "pin") and
   jfu-P5/C5 (P5 outside the frozen `.[]` relation definition).
   Both are INVALID and excluded from scoring pending reviewed
   amendment; neither affected relation gets a PASS/FAIL verdict.

## Per-relation viability under the frozen rules

- No relation is yet eligible to carry forward from Phase 18B.
  `pinned_sha_demoted_to_branch` is promising (4/4 valid positives,
  0/4 valid controls) but remains **INVALID_PENDING_AMENDMENT** until
  its defective pair is corrected and rerun.
- `secret_logged_by_echo` and `doc_self_contradiction` need
  **semantic redesign** (value-based rather than name-based secret
  matching; genuine contradiction rather than co-occurrence) through
  a fresh preregistered cycle — not tuning; their failures are
  evidence.
- `preserved_claim_vs_dropped_call_result` and
  `consume_before_validate_ordering` have zero control leakage but
  failed recall thresholds. `jsonl_format_vs_unslurped_jq` is
  **INVALID_PENDING_AMENDMENT** because of the out-of-scope P5/C5
  pair; its remaining observed core is 3/4 with zero leakage.

No relation was changed, no fixture was changed, and no promotion
decision is made by this artifact. Results are published for review.
