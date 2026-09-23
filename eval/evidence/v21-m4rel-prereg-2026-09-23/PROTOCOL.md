# Phase 22B — m4rel candidate: preregistration

**Status: preregistration only. No candidate module exists, nothing
has been executed, and no authority is granted. Per the 22A framework
(`candidate_specific_preregistration_required`), this phase freezes —
before implementation or evaluation — m4rel's exact targets and
disjoint ownership, paired near misses, existing controls, the fresh
independent holdout with frozen thresholds, extra-blocker effect, and
the no-oracle-role runtime constraint.**

## Candidate definition (frozen)

`m4rel` detects the **unsubstantiated absolute docstring claim**: an
in-diff docstring or comment makes an absolute/exclusive claim
(always / never / all / only / none / no other / every / exactly-N /
guarantees) about the behavior of code **not present in the diff**,
where nothing in the change substantiates the claim and documenting
that out-of-diff contract is the change's stated purpose. The word
list is **illustrative, not the detector**: the definition is
semantic (out-of-diff referent + unsubstantiated + documentation
purpose); keyword-only matching is insufficient and non-conformant.
Module to
be: `eval/v21_m4_relation.py` (does not exist yet). Relation name:
`unsubstantiated_absolute_docstring_claim`.

**Must not fire** on: self-scoped/disclaiming docstrings (the C4
pattern — "this module does not define how consumers …" asserts
nothing about out-of-diff behavior); hedged or default-path wording
(typically/usually/advisory/may); claims the change's own hunks
substantiate (the m4h-C3 pattern); PR-metadata scope mismatches
without a docstring absolute claim (the C4-row / M4-extra pattern);
external well-known semantics (C13/C2/C16); or docstring-vs-in-diff-
code contradictions (C12 — that is dsc territory, not m4rel).

Runtime constraint: the candidate sees only PR content — **no
oracle-role, source-record, or record-index branching**.

## Targets and disjoint ownership (frozen)

Declared targets = **P-M4 exactly**: stage-a-max r66 f0 and b1-low
r44 f0 (the two bare contract-route M4 true positives), each with its
finding text/file/line **hash-pinned** (`finding_pins` in
`TARGETS_CONTRACT.json`). Qualification requires **2/2 fired**. m4rel
is the only slate candidate whose targets include these ids; no
successor may claim them.

The other five M4 true positives (b1-low r29 unwitnessed survivor,
b1-low r14, b1-high r14/r29/r44) are **family-context non-targets**:
candidate firings on them are permitted and recorded; non-firings are
permitted and recorded; neither affects qualification. They are not
preservation-relevant (b1-low r29 survives on the unwitnessed route;
the rest are already downgraded by g2 and preservation cannot
resurrect rows).

## Near misses (frozen)

QG1 binds m4rel to **zero firings on all 77 corpus control rows**,
fail closed. The design-adjacent subset, enumerated in
`TARGETS_CONTRACT.json` (25 rows), is what near-miss behavior is
reviewed against: the three **C4** rows (the M4-paired control — same
retry-contract PR, strictly self-scoped docstring, scope-violation
findings); the thirteen **C12** docstring rows (honest in-diff
contract claims the code violates — dsc territory); **C8** r16 and
**C3** r6/r36 (comment-promise vs edge-case gaps); **C13** r4/r40/r32,
**C2** r46, **C16** r79/r43 (metadata and external-fact claims). The
enumeration method (frozen vocabulary regex over control comments) is
mechanically re-derived in tests.

The semantic boundary in one line: **m4rel fires on unverifiable
exclusivity about out-of-diff code; it stays silent when the claim is
self-scoped, hedged, substantiated in-diff, or about in-diff
behavior.**

## Extra blockers (frozen)

All 34 positive-extra-blocker rows are non-targets. The four **M4
extras** (stage-a-high r30/r102, stage-a-max r30/r102 — the
scope-violation flavor of the same PR) are named explicitly. Any
candidate firing on an extra row is recorded in the qualification
record; firing on extras is not an automatic FAIL at qualification,
but **any proposed adoption preserving an extra blocker fails the
preservation-safety gate** (22A QG1).

## Existing holdout (frozen expectation)

On the 18A holdout, m4rel must fire on **zero of the 30 controls**.
m4rel is a new family, not a remediation of a failed relation, so no
existing-holdout positive expectations are claimed or required.

## Fresh independent holdout (frozen material + thresholds)

`eval/evidence/v21-m4rel-holdout-2026-09-23/` — **6 semantic
near-miss pairs** (12 fixtures), authored **before any candidate
implementation exists**, in the 18A probe-record schema:

- **m4h-P1/C1** — scheduler job priority; control = self-scoped
  disclaimer.
- **m4h-P2/C2** — collector sampling interval; control = hedged
  default-path statement.
- **m4h-P3/C3** — workspace-root resolver; control = **same absolute
  wording substantiated in-diff** by the change's own consumer
  (hardest near miss).
- **m4h-P4/C4** — queue redelivery marker; control = self-scoped.
- **m4h-P5/C5** — watcher debounce; control = advisory framing with
  explicit deferral.
- **m4h-P6/C6** — supervisor restart policy; control = self-scoped.

Labels: positives `ADMITS` (6/6 must fire), controls `REFUSES` (0/6
may fire). Scenario domains, paths, class names, and claim wording
are new; the canonical M4 corpus claim appears in no holdout fixture
(mechanically asserted). Manifest pins: full-file
`7b82ed00806a431a795d0e7eace92940cb82c3e88b5d988b07efbd8b9f34df3f`,
lines `2e1eb0d9892878d1afcdb9c93e00f301073d45b3eda3f7bc57051eea44544d45`.

**Independence and its limit**: the holdout was authored before any
implementation exists (nothing to overfit), and this PR's human
review is the freeze point — the reviewer may amend fixtures before
freeze. Residual risk, disclosed in the manifest authorship block:
holdout author and future candidate author are the same agent;
post-merge fixture changes require an AMENDMENT.md entry with hash
refresh (the 18C rule). Thresholds are frozen **before first
candidate execution**; no tuning after seeing output.

## Qualification binding (unchanged from 22A)

QG1: 2/2 targets, 0/77 controls, extras recorded · QG2: 0/30
existing-holdout controls, 6/6 + 0/6 fresh holdout, no post-hoc
tuning · QG3: new module, no delegation, frozen verifier byte-frozen ·
QG4: standing guards · QG5: human-reviewed qualification record
before any adoption PR; **a pass never self-grants preservation
authority**. Any gate failure is recorded and m4rel is auto-excluded,
never tuned post hoc; the two PC1 M4 losses then remain open costs.

## Non-goals

No implementation, no execution, no authority grant, no adoption
preregistration, no reduction rule, no GATING, no deployed change, no
edits to frozen modules/fixtures/routes/parser/oracle, no
`eval/fixtures` additions — the holdout lives in the evidence layer
and changes no oracle input.
