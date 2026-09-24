# Phase 23A — Combined-policy adoption design (design only — nothing is adopted)

**Status: design preparation.** This document defines the candidate
policy variants, authority boundaries, integration points,
prohibitions, and the acceptance gates a *future* adoption
preregistration must satisfy. It implements nothing, executes
nothing, and assumes no approval. PC2 and the separate 24-row
failed-firing-presence policy decision both remain open. The `m4rel` grant is treated
exactly as its record scopes it; **no grant registry or runtime
authority table is created by this phase.**

## Inputs this design binds to

- Frozen candidate: `eval/v21_m4_relation.py`,
  SHA256 `1a01d8ff6f15fd050eb290da4f20a2d99dacb59ea183b0dc6b803c6004139596`
  — never modified by adoption work; a changed SHA voids the grant.
- Accepted grant:
  `eval/evidence/v21-m4rel-qg5-grant-2026-09-23/GRANT_RECORD.json`
  (accepted at the #107 merge `71f78a19ab6297c89186552dbe03efd5a587c3d9`),
  with every documented limitation retained.
- Frozen 22A framework (two-authority separation, QG1–QG5), 21A
  reduction preregistration (R1′ = exploratory, relation-dependent,
  not adoptable), 21B witness-policy design (tiers, redaction
  accounting), 18A/18D reports, and the mechanical ledger in
  `COMBINED-LEDGER.json`.

## Candidate policy variants (corpus semantics)

All variants act only on `g2_contract_aware == BLOCK_SURVIVES` rows
on the `contract_contradiction` route. Aggregate effects are in
`COMBINED-LEDGER.json` → `counterfactual_effects`.

- **V2 — bare-scope reduction + m4rel grant (the working candidate).**
  Downgrades rows with **no evidence of any kind** (no T1 predicate,
  no relation firing of any tier), then exempts grant-eligible
  existing blocks (claim-linked `m4rel.covers`). Ledger: falls 20
  (15 controls + 5 extras — the intended benefit), 2 M4 true
  positives preserved by grant, 0 erroneous preservations, 123
  survivors unchanged, the 24 relation-carried TPs untouched.
- **V1 — bare-scope reduction without the grant.** Falls 22,
  including the two grant-protected M4 rows. Listed only to show
  what the grant buys; not a candidate.
- **V3 — qualified-evidence-only witness semantics (warning
  variant).** Treats failed-relation firings as non-witnessing (the
  redaction-accounting semantics). Falls 46: the 22 bare rows **plus
  the 24 relation-carried true positives**. Not proposed. Its purpose
  is the proof that evidence semantics must be stated precisely: a
  policy that "ignores failed relations" silently sacrifices 24
  true positives, none of which carry T1/T2 evidence by construction.
- **V0 — baseline.** No reduction; all numbers reconcile to g2
  as-is.

### The 24 relation-carried true positives — standing treatment

1. V2 leaves them **untouched**, and that is *all* it does: their
   non-bareness happens to rest on failed-relation firings. This is
   **evidence-presence dependence, admitted** — the rule is not
   invariant under redaction of T3/T4 firings.
2. Their firings therefore hold **no preservation authority** and
   must not acquire any implicitly: no grant, no tier promotion, no
   runtime special case may be derived from "V2 keeps them".
3. The rejected 21B redaction-equivalence claim is **not resurrected**: no adoption document may assert that redacting
   failed-relation firings "changes nothing".
4. If a future policy adopts V3-style semantics (or redacts failed
   firings), the V3 delta becomes binding: those 24 rows fall unless
   each gains qualified evidence through PA1/PA2/PA3 paths — a
   separate, human-gated decision per the 22A framework.
5. The M10-family row (stage-a-max r55) stays regression-evidence
   only (FAILED 17; C10 standing near-miss), as everywhere else.

## Authority boundaries

- **psd** retains its previously qualified, contract-route admission
  authority (`EVIDENCE_BACKED_ELIGIBLE__CONTRACT_ROUTE_ONLY`).
  Unchanged. No expansion, no re-parameterization, no new admission
  scope.
- **m4rel** holds preservation-only authority exactly as granted:
  existing `BLOCK_SURVIVES` blocks, contract route,
  claim-linked `covers()`, measured corpus effect = the two named
  rows, exclusions intact (no admission, no block creation, no
  extra preservation, no route expansion, no GATING, no deployment).
- **The five 18D-failed relations and the failed M10 relation** have
  no qualified preservation or admission authority. V2 nevertheless
  reads their firing **presence** to decide whether a row is bare:
  that is decision-bearing evidence-presence dependence, not a
  qualified preservation witness. The 24 relation-carried TPs
  (including M10) remain blocked under V2 for this reason alone.
  The distinction must be explicitly approved or replaced with
  independent qualified evidence before V2 adoption; no implicit
  tier promotion, grant, or redaction-invariance claim is permitted.
  V3 shows the 24-TP cost when failed firings are not used even for
  bare-ness.
- **Human risk acceptance** (PC2 Path A, if chosen) is scope
  language only. It never becomes evidence, never enters a grant
  registry, and never appears as a runtime input.

## Integration points (design-level)

1. **Reduction evaluator (future):** a new module consuming only
   frozen records + frozen `v21_contract_relations` /
   boundary-simulation semantics + the grant registry file. It must
   not modify `eval/v21_m4_relation.py`, the frozen verifier, any
   baseline decision module, or any evidence artifact.
2. **Grant registry (future):** a machine-readable file listing
   accepted grants with their exact scope, candidate SHA, evidence
   pins, and exclusions — seeded from the accepted m4rel record,
   created only by an authorized adoption PR.
3. **Evidence boundary:** all reduction outputs are counterfactual
   reports until an execution authorization exists; reports write to
   a new evidence directory; existing evidence directories are
   immutable (22D's read-only lifecycle rule generalizes).
4. **CI/tests:** the standing deterministic suite must grow the
   adoption gates below as mechanical tests before any execution.

## Prohibitions (runtime policy invariants)

- No fixture IDs, oracle roles, hidden labels, expected/ground-truth
  fields, or known holdout membership as runtime policy inputs.
- No oracle-label (`ADMITS`/`REFUSES`) reads outside offline
  evaluation.
- No use of failed-relation or M10 firings as **qualified
  admission/preservation witnesses**. V2 still makes their *presence*
  decision-bearing through the bare-ness predicate: this historical
  dependence must be specifically dispositioned by a human before
  adoption, never hidden behind an advisory-only tier label.
  A policy prohibiting ALL decision-bearing failed-firing use cannot
  adopt V2 as written; it must choose qualified independent evidence
  or explicitly confront the 24-TP V3 loss.
- No widening of `m4rel.covers`, its claim boundary, or its route
  scope; no reuse of the grant's semantics for other candidates
  without their own qualification + grant.
- No post-hoc tuning of frozen evidence; any discrepancy halts
  (fail-closed), as in 22D.

## Adoption gates (a future adoption preregistration must satisfy all)

1. **Exact-head evidence and hash integrity:** PR head recorded;
   every input pinned by SHA256; pins verified live, fail-closed.
2. **No new admission authority; psd unchanged:** psd referenced
   only as-is; its chain artifacts hash-unchanged.
3. **No preservation authority from failed relations or M10:**
   mechanically asserted over all populations. Separately, resolve
   the V2 failed-firing-presence dependence for all 24 relation-carried
   true positives: explicitly accept the narrow evidence-presence
   semantics as a *policy* decision without mislabeling it a witness
   grant, or require independently qualified preservation evidence
   before changing those decisions. An R1′-style redaction-invariance
   claim fails this gate.
4. **Preservation of the two qualified M4 rows:** the grant-eligible
   set re-derived and asserted = {b1-low r44 f0, stage-a-max r66 f0}.
5. **Zero extra-blocker preservation and no new control blockers** on
   the qualified evaluation populations (corpus: 0/77 controls, 0/34
   extras preserved; no control row newly blocked by the combined
   policy).
6. **Explicit PC2 disposition and holdout recall accounting:** the
   chosen path recorded with its exact authorization; holdout
   outcomes stated per `COMBINED-LEDGER.json` variants; no silent
   extension to holdout material.
7. **Unchanged standing guards and non-contract behavior:** frozen
   guard dict, C10 near-miss, non-contract routes, oracle
   `117b4164e5446f50` — all byte-stable.
8. **No hidden oracle-role branching:** runtime inputs enumerated in
   the preregistration; test-pinned.
9. **Independently reviewed implementation/evaluation boundary;**
   no post-hoc tuning of frozen evidence: implementer ≠ sole
   reviewer; any evaluator defect found during execution is
   preserved, provenance-logged, and corrected under the 22D
   disclosure pattern.

## The four authorization kinds — explicitly distinguished

| Kind | Object | Example gate | Implies the next? |
| --- | --- | --- | --- |
| **Policy-design approval** | this design + PC2 disposition + variant choice | human review of an adoption prereg PR | **No** |
| **Execution authorization** | running the reduction evaluator / holdout runs on frozen records | separate human go, scope- and artifact-bounded | **No** |
| **Authority grant** | per-candidate preservation/admission authority (QG5-shaped) | qualification PASS + separate human grant; permanent, recorded | **No** |
| **Deployment / GATING activation** | changing deployed reviewer behavior or GATING states | its own human decision, out of scope for every phase so far | terminal only |

None follows automatically from another. A PASS record is not a
grant (humility rule); a grant is not an implementation; an
implementation is not a deployment. Sequence for any real adoption:
design approval → execution authorization → measured evidence →
(if new authority is needed) grant → (only then) deployment/GATING
decision.

## What this phase does NOT do

A merge of this design does not select PC2 or resolve the 24-row
failed-firing-presence dependence, and it does not accept either
recall/authority trade-off. Both require a separate, explicitly
reviewed policy disposition before any adoption preregistration
can be approved.

No R1′ or successor implementation, no reduction execution, no new
holdout execution (the 21B V2 prediction stays frozen), no change to
the frozen `m4rel` detector, no baseline decision changes, no
additional authority, no GATING, no deployment, no grant registry
file. **Stopped for human review.**
