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
| `pinned_sha_demoted_to_branch` | 4/5 (1 INVALID) | 0/5 | **GENERALIZATION PASS** |
| `preserved_claim_vs_dropped_call_result` | 3/5 | 0/5 | GENERALIZATION FAIL |
| `consume_before_validate_ordering` | 1/5 | 0/5 | GENERALIZATION FAIL |
| `secret_logged_by_echo` | 3/5 | **1/5** | GENERALIZATION FAIL |
| `doc_self_contradiction` | 2/5 | **2/5** | GENERALIZATION FAIL |
| `jsonl_format_vs_unslurped_jq` | 3/5 | 0/5 | GENERALIZATION FAIL |

**Aggregate: 16/30 positives admitted, 3/30 controls admitted, 1/6
relations PASS → no blanket promotion of the six-relation registry.**
Standing regression guards all held (C11 refused; C10 standing
near-miss against the still-FAILED M10 relation; M3 admitted via the
existing witness; M13 refused; C12/M12 refused; oracle
`117b4164e5446f50`).

## The INVALID pair

`psd-P4` is a **fixture authoring defect**: the authored "pinned"
ref is 39 hex chars, not a 40-hex commit SHA (proof in the report's
`fixture_defects`: single hex run of length 39 in the removed lines).
Per the preregistered defect path it is marked INVALID, excluded from
the score, and counted neither as verifier success nor failure.
Excluding it leaves psd at 4/4 scored positives with 0/5 controls —
PASS under the frozen threshold either way. Correction would require
a reviewed amendment before any rerun; nothing was edited.

## Exact failed fixtures

- psd: (P4 → INVALID)
- pcd: P3, P4 — both **predeclared scope probes** (requests/httpx);
  in-scope urlopen semantics: 3/3
- cbv: P2, P3, P4, P5 — all **predeclared scope probes** (setter
  method, non-`.state` properties, Python `None`); original
  `.state = null` shape: 1/1
- sle: P4, P5 (predeclared probes: f-string, `console.log`) plus
  **control leak sle-C3** (fingerprint near-miss)
- dsc: P3, P4, P5 (in-scope positives) plus **control leaks dsc-C1,
  dsc-C2** (scoped-exception controls)
- jfu: P2 (predeclared probe: single-redirect producer), P5
  (beyond-definition: single-document `length` assumption without
  `.[]`)

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
4. **Beyond-definition authoring — 1 fixture (jfu-P5)**: tests a
   single-document assumption the preregistered relation wording
   (array filter `.[]`) does not cover. An 18A scope slip, recorded
   here and still counted honestly; the relation fails 3/5
   regardless.
5. **Fixture defect — 1 pair (psd-P4)**: INVALID, see above.

## Per-relation viability under the frozen rules

- **`pinned_sha_demoted_to_branch`** is the only relation eligible to
  carry into the next implementation/preregistration phase.
- `secret_logged_by_echo` and `doc_self_contradiction` need
  **semantic redesign** (value-based rather than name-based secret
  matching; genuine contradiction rather than co-occurrence) through
  a fresh preregistered cycle — not tuning; their failures are
  evidence.
- `preserved_claim_vs_dropped_call_result`,
  `consume_before_validate_ordering`, and
  `jsonl_format_vs_unslurped_jq` have sound in-scope cores with zero
  leakage; generalizing them beyond the original surface shapes is
  future preregistered work with the same holdout discipline.

No relation was changed, no fixture was changed, and no promotion
decision is made by this artifact. Results are published for review.
