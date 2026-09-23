# psd contract-route qualification — closeout record

This document closes out the `pinned_sha_demoted_to_branch` (psd)
qualification evidence as a **standalone, reviewable result**. It
consolidates the complete evidence chain, states exactly what was
established and what was not, and fixes the conditions under which
the record is void. Machine-readable form: `RECORD.json` (same
directory). Every hash in this record is mechanically verified by
`tests/test_v21_psd_closeout.py`.

## Subject

- Relation: `pinned_sha_demoted_to_branch` — a cited-file
  change from a pinned full 40-hex commit SHA to the specific mutable
  forms recognized by the frozen verifier (`@main`, `@master`, or
  `ref: main/master`). This record does **not** establish coverage of
  arbitrary branch names or tags.
- Frozen verifier: `eval/v21_contract_relations.py`
  (sha256 `bb0ebdee…`, merged at `0631b095…` in PR #93). Called,
  never modified, across every phase below.
- Oracle: `117b4164e5446f50` (unchanged throughout).

## Established (with evidence chain)

**psd is `EVIDENCE_BACKED_ELIGIBLE__CONTRACT_ROUTE_ONLY`** under the
frozen oracle: it may sustain a `BLOCK_EVIDENCE_BACKED` decision on
the `contract_contradiction` route, by the preregistered rule
(contract route AND psd fires AND baseline `g2_contract_aware` is
`DOWNGRADE`).

| phase | PR (merge) | result |
|---|---|---|
| 17 — relation frozen | #93 (`0631b095…`) | binding pair discipline; psd among 6 survivors; M10 relation FAILED and excluded |
| 18A — holdout prereg | #94 (`600f3a6e…`) | 60 unseen fixtures frozen before any run |
| 18B — first eval | #95 (`76e076f9…`) | 0 PASS · 4 FAIL · 2 INVALID; psd pair INVALID (39-hex ref); record frozen |
| 18C — amendment | #96 (`15cbdd11…`) | reviewed correction of both INVALID pairs; no verifier execution |
| 18D — final holdout | #97 (`59656cae…`) | **psd GENERALIZATION PASS: 5/5 positives, 0/5 controls**; 56/56 reconciliation exact |
| 19A — integration prereg | #98 (`00f8237f…`) | contract-route-only rule; frozen prediction: exactly 1 promotion; halt conditions fixed |
| 19B — integration executed | #99 (`04db3e10…`) | **SUCCESS, zero halts: 1 promotion, 275 decisions unchanged, 0 collateral, 0 new control/extra promotions** |

The single promoted finding is the preregistered M2 instance
(`stage-a-max` rec 28: pinned SHA → `@main` on
`.github/workflows/ai-review.yml`), previously downgraded by both the
quote gate and the contract-aware gate.

## What this record does NOT claim

- **Not a GATING activation** or authorization; the promotion path to
  GATING (measured qualification, permanent) is separate and
  untouched.
- **Not a deployed reviewer change** — an offline qualification
  result on the feature branch.
- **Not a registry promotion** — the other five relations remain
  non-gating (sle/dsc: semantic false-positive failures → redesign
  from first principles; pcd/cbv: recall failures → new preregistered
  cycles; jfu: affirmative-`if` recall boundary → new pair/holdout
  cycle).
- **Does not resolve the baseline's 27 surviving control blockers** —
  19B added zero new control promotions; the pre-existing remainder
  is untouched by this evidence.
- **Does not extend psd beyond the contract route** — the 18
  psd-matching downgrades on `external_fact`/`unwitnessed_behavior`
  routes remain downgraded by design; route extension requires its
  own preregistered evaluation.
- **Not a correctness claim about any subject** (humility rule):
  eligibility is scoped to oracle `117b4164e5446f50` — this harness,
  this corpus, this GATING state.

## Void conditions

This record is void if any of the following occur; tests fail loudly
rather than degrade silently:

1. the verifier module hash drifts from `bb0ebdee…`;
2. the oracle drifts from `117b4164e5446f50`;
3. any referenced artifact hash drifts (18B/18D/19B reports, 19A
   contract, 18A holdout manifest);
4. the FAILED `doc_contract_prefix_unanchored_match` (M10) ceases to
   be FAILED;
5. any standing regression guard fails (C11/M13/C12/M12 refused;
   M3 witnessed via existing evidence; C10 standing near-miss).

## Deployment-contract note

The repo deployment contract remains **PENDING ACTIVATION** until the
umbrella `feature/reviewer-eval-baseline` merge; pin-to-qualification
binding on the `qualifications` branch is not exercised by this
record.
