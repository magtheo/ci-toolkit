# Phase 18A — unseen generalization holdout: preregistration only

Status: **frozen 2026-09-22, evaluation deliberately NOT performed.**
This artifact freezes a holdout test set and the Phase-18B evaluation
rules before any verifier behavior on that holdout is observed. No
provider calls; no parser, schema, rubric, prompt, oracle, route, or
Phase-17 relation change; no existing fixture or evidence file
touched.

## Purpose

Phase 17 designed six contract-relation verifiers and validated them
on the same corpus that informed their design — a necessary but not
sufficient test. This holdout measures, for the first time, whether
those relations generalize to unseen surface forms, on pairs whose
answers are frozen before the verifier runs.

## Frozen subject

- Phase-17 verifier implementation frozen at feature-merge SHA
  `0631b0956f795ab1ee6d13f68b0c1cebe8a6d23b`.
- Module `eval/v21_contract_relations.py`, SHA-256
  `bb0ebdeeb7fc80395626bf10d3e9ad1a730936ccf0ab7e719c43c1b5754b1b57`
  (pinned in `MANIFEST.json`; the 18A tests enforce it — any
  modification of the module in 18A fails the suite).
- `doc_contract_prefix_unanchored_match` remains **FAILED** from
  Phase 17; it is not rehabilitated, amended, or tested here. C10/M10
  remains a standing near-miss regression example only.

## Anti-leakage rules (binding)

1. **No execution.** The Phase-17 verifier
   (`relation_names()` / `eval/v21_contract_relations.py` or any
   equivalent) must NOT be executed against the holdout during
   18A — not by the authors, not by the tests, not in CI. Phase 18A
   ends with the holdout frozen; Phase 18B performs the first and
   only evaluation.
2. **Authoring basis.** Fixtures are authored from the semantic
   relation definitions in the Phase-17 protocol (pin demotion;
   preservation claim vs dropped result; consume-before-validate;
   secret value logged; doc self-contradiction vs scoped exception;
   JSONL producer vs unslurped array consumer). They are NOT
   constructed by searching for strings that satisfy or defeat the
   current regex implementation.
3. **Labels.** `expected_label` (positive → ADMITS, control →
   REFUSES) is determined from the intended semantics recorded in
   each fixture's `rationale`, never from verifier behavior.
4. **Hash pins.** Every fixture file has a SHA-256 pin in
   `MANIFEST.json`; the manifest itself is pinned by
   `manifest_lines_sha256` over the sorted `<sha256>  <id>` lines.
5. **Amendments.** After the 18A PR opens, fixture content or labels
   may change only for an independently demonstrated fixture defect,
   via a reviewed amendment that names the fixture and the defect
   explicitly.
6. **No reverse adaptation.** No relation may be changed in response
   to holdout behavior. A failure is evidence, not a patch request.

## Holdout structure

- 6 relations x 5 pairs = 30 positives + 30 near-miss controls = 60
  fixtures under `fixtures/`.
- Each pair tests the same semantic distinction with superficial
  syntax varied (names, formatting, quoting, surrounding statements,
  equivalent control-flow shapes, language-specific forms where the
  relation naturally supports them). The control changes only the
  semantic feature that makes the positive defective.
- Nine positives are pre-declared `probe: true`: semantically
  in-scope but authored in surface forms beyond the original
  corpus's shapes (e.g. non-shell logging syntax, Python `None`,
  non-`.state` consumption, single-redirect jq producers). This
  pre-declaration exists so a failure there is classifiable as
  syntactic/brittleness rather than hidden.
- Fixture JSON schema: `id`, `relation`, `role`, `expected_label`,
  `language`, `probe`, `rationale`, `finding{file,comment}`,
  `fixture.input.files[{path,patch}]`.

## Phase-18B evaluation rules (preregistered now)

Operationalization: for each fixture, run the frozen
`relation_names(finding, fixture)` once. The relation under test
"admits" the fixture iff its name is in the returned set. No quote
gate, route layer, or other machinery is involved in the 60-fixture
score.

Per relation, independently:

- control leakage must be **0/5**; any control admission = that
  relation **GENERALIZATION FAIL**;
- positive recall target **>= 4/5**; fewer = **GENERALIZATION FAIL**;
- 4/5 or 5/5 positives with 0/5 controls = **GENERALIZATION PASS**.

Aggregate:

- all six relations PASS → the contract relation layer is eligible
  for the next implementation/preregistration phase;
- any relation FAILS → **no blanket promotion** of the six-relation
  registry; per-relation results are preserved and viability is
  decided separately per relation;
- a discovered fixture/oracle defect marks that pair **INVALID** —
  never silently counted as verifier success or failure; correction
  requires a reviewed amendment before rerun.

Required 18B report: per-relation TP/control counts, exact failed
fixture IDs, aggregate TP recall, aggregate control leakage, and
whether each failure is semantic or syntactic/brittleness.

## Standing regression invariants (18B harness guards, NOT part of the 60-fixture score)

Phase 18B must additionally preserve, via the existing frozen
replays: C11 remains refused; C10 remains a standing near-miss
against the FAILED M10 relation; M3 remains admitted through the
existing witness; M13 remains refused; C12 and M12 downgrade controls
remain refused; oracle remains `117b4164e5446f50`.

## Scope boundary of the 18A tests

The 18A tests validate the holdout artifact mechanically (counts,
pair structure, labels, uniqueness, hash pins, frozen verifier
identity). They must not import or call the relation verifier on the
holdout fixtures. The important deliverable is not "60 fixtures our
verifier passes" — it is **60 fixtures whose answers were frozen
before anyone knew how the verifier behaves**.
