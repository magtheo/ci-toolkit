# Phase 22E — m4rel QG5 preservation-grant record

**Status: PROPOSED grant.** This record was authored by the coding
agent from the operator's stated QG5 disposition. Per the 22A
framework and standing rules, **agents never grant authority**: the
grant becomes effective only through the human merge acceptance of
the 22E pull request. No test, qualification record, or document
grants it.

## Approved scope (operator's QG5 disposition)

| Dimension | Approved scope |
| --- | --- |
| Authority type | Preservation only |
| Candidate | Exact frozen `m4rel` implementation, SHA `1a01d8ff…` |
| Eligible decision | An existing `g2_contract_aware = BLOCK_SURVIVES` |
| Route | `contract_contradiction` only |
| Evidence requirement | `m4rel.covers(finding, fixture)` — claim-linked, not merely same-file |
| Effect | Exempt an eligible existing block from a future, separately approved bare-scope downgrade |
| Historical effect | Preserve the two named M4 true positives |
| Exclusions | No admission, no block creation, no extra-blocker preservation, no route expansion, no GATING or deployed change |

The grant is **not** an unrestricted exemption for every future
m4rel detection: its reusable semantics are the frozen claim boundary
plus the existing-block / contract-route / claim-linked conditions;
its measured corpus effect is exactly the two M4 rows. Any broader
generalization claim requires additional independent validation.
The `true_positive_detection` role is a **frozen evaluation label,
never a runtime decision input**. The observed zero control/extra
preservation is corpus-scoped; a future combined-policy adoption must
separately demonstrate those safety conditions without oracle labels.

## Evidence pins (distinguished)

- **Original run-4 report** (`qualification-report.execution-4.json`,
  sha256 `a4ebaabac2dea4c662541f433aeb580bd91d301e45dde576ce3688eb4a422c1f`)
  — the evaluator's original SUCCESS output.
- **Review-annotated published report**
  (`qualification-report.json`,
  sha256 `fec590e9f822880a4e82aaa281f1ad6c0942559eaa55dbc64c6ddab08a11934c`)
  — the human-reviewed published record.
- **Preserved first-run HALT**
  (`qualification-report.execution-1.json`,
  sha256 `b368b5a4…`) — immutable; an evaluator aggregation defect,
  not a candidate failure.
- PR #106 merge SHA `9a962c08dc90947ecdf5b6c3f67d212cf82915a2`
  (final reviewed head `90fd9293…`), 22D transition `b3eb2a4c…`,
  22B contract `0f7e1837…`, oracle `117b4164e5446f50`, frozen
  verifier `bb0ebdee…`.

All qualification limitations are retained verbatim in
`GRANT_RECORD.json`: preregistered-validation-only (NOT
vocabulary-independent generalization), cross-execution identity
proved first-vs-final only (intermediate runs rest on the disclosed
log), the existing-holdout gate's structural caveat, and the extras
file-match diagnostics.

## Mechanical effect on the frozen corpus (re-derived in tests)

- 276 blocking rows; grant-eligible rows: **exactly**
  stage-a-max r66 f0 and b1-low r44 f0 — the two named M4 true
  positives.
- **Zero controls preserved (0/77). Zero extras preserved (0/34).**
  The role filter is redundant: `covers()` claim-linkage alone
  excludes every extra.
- Bare-contract survivors (22 = 15 C + 5 E + 2 TP): the grant
  preserves the 2 TPs; the 20 remaining falls under any future
  bare+grant policy are the intended benefit (they are false
  blockers) and require the separately reviewed adoption design.
- 123 survivors untouched; the 24 relation-carried TPs gain nothing
  from this grant (21B relation-dependence problem unchanged).

## What this resolves — and what it does not

- **PC1** is resolved at the qualification-and-grant level, subject
  to verification that the future combined policy preserves exactly
  those two rows. It does not itself demonstrate that an eventual
  reduction implementation works.
- **PC2 (dsc-P4) remains open**: any bare-scope rule extended to the
  holdout would still downgrade dsc-P4; neither this grant nor the
  FAILED dsc relation exempts it. The adoption design stays blocked
  until PC2 has an explicitly reviewed disposition (accept the cost /
  qualify dsc′ first / decline holdout extension).
- No R1′ implementation, no baseline decision changes, no GATING,
  no deployment. psd admission scope untouched. Failed relations and
  M10 gain no authority.

**STOPPED for human review — acceptance happens at the 22E merge.**
