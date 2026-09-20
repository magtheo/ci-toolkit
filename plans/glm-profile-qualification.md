# Plan: GLM reasoning-profile qualification

Status: APPROVED-BY-DIRECTIVE (human directive 2026-09-18); Phase 01
implemented, **awaiting human review + explicit spend authorization
before any model call**.

## Objective

Select the deployed reasoning profile for `z-ai/glm-5.3-flash`
(effort low/high/max, budget) through **measured qualification**
against the repaired 25k oracle — never ad-hoc. The deployed
provisional profile (low / 8000) stays untouched until a profile
earns deployment through this campaign.

## Boundaries (hard)

- **Oracle**: `eval/run_corpus.py` + `eval/fixtures/` +
  `eval/states.json` byte-identical to oracle checkout
  `4b116a7c7c4e9e78cddd362cd3ca4766aaf6ea25`;
  `oracle_version = 9e20730cb0436002` throughout. The qualification
  tooling is NOT an oracle input (oracle_version excludes it) —
  asserted by tests.
- **Subject**: prompts (`engine._build_prompts`), rubric, parser
  semantics unchanged; golden prompt hashes pin all 36 fixtures;
  subject files byte-identical to the oracle checkout.
- **Transport**: request shape / classification / escalation /
  failure taxonomy imported from the #70-pinned `transport.py`
  (`b663bfd3139bb04a70f95d661c96ee150f534513`) — one source, no
  reimplementation; byte-identity asserted by tests.
- **Measurement-only overrides** (`--reasoning-effort`,
  `--max-tokens`) exist only in `eval/profile_qualification.py` and
  evidence artifacts; `model_profiles.json` byte-identity asserted.
- Zero reasoning-chain content is ever persisted.

## Branch structure

- `feature/glm-profile-qualification` — forked at the oracle
  checkout `4b116a7` (the repaired oracle lives on the umbrella
  feature branch), then integrated `main@1ae4287` (merge `fa068c7`)
  **by explicit directive** (the directive pins both the oracle
  checkout and the transport). Merge resolution policy: subject
  files (engine/render/rubric/parse_review/review.sh/workflows) stay
  at the oracle checkout; the transport trio
  (transport.py/model_profiles.json/review_result_schema.json) is
  main's #70 content byte-for-byte. Main-side deployment deltas
  (#70 review.sh integration, #71 workflow model pin) reconcile at
  the umbrella merge, not here.
- `phase/glm-profile-qualification/01-q0-preflight` — Phase 01 only:
  `eval/profile_qualification.py`, tests, this plan, the Q0 evidence
  bundle. PR targets the feature branch.

## Phase 01 — Q0 preflight (this PR)

Deliverables: measurement adapter with `--dry-run` (zero network,
deterministic), request-equivalence + escalation + boundary tests,
golden prompt hashes, oracle/subject/transport identity tests, dry-run
manifests for low/high/max, Stage A preregistration (metrics,
selection rule, spend bounds) in the evidence README. **Zero model
calls.** Live mode is double-gated (`--live` +
`PM_QUALIFY_LIVE_AUTHORIZED=1`).

 ## Phase 02 — Stage A (COMPLETE — all profiles disqualified)

Full matrix, metrics, selection rule, and spend gate are
pre-registered in
`eval/evidence/q0-glm-profiles-2026-09-18/README.md` — written
before any profile result exists. Executed 2026-09-19 (324/324,
$0.3916): D3 (zero-tolerance control false-blocking) fired at every
effort; the frozen rule selected no profile. Evidence published via
PR #78; per-`out_dir` ceiling scope disclosed there.

## Phases 03–06 — the B sequence (directed 2026-09-19/20)

- **03 — Stage B0** (MERGED, PR #79): zero-call attribution of the
  D3 false positives; exact 58-finding reconciliation; C11 confirmed
  as an oracle defect.
- **04 — Oracle repair** (MERGED, PR #80): C11/M11 invalid flag
  removed; `oracle_version` → `5472d990f3b946c3`; historical records
  keep their original identities. C8 pending independent
  adjudication — excluded from qualification sets until ruled on.
- **05 — B1 preregistration** (this phase): frozen package in
  `eval/evidence/stage-b1-prereg-2026-09-20/` — revised rubric
  (subject-side, single rule block), 15-fixture matrix incl. C4/M4,
  aggregate $1 spend-ceiling design, group-wise no-regression pass
  criteria, M4/M13 reported separately (zero baseline detection).
  Preregistration ONLY: no rubric applied, no code, no calls.
- **06 — B1 execution** (gated): applies the approved rubric
  byte-for-byte, implements the aggregate ledger, and runs 90
  reviews ONLY after (a) package approval pinning its sha256,
  (b) rotated API key, (c) explicit live-spend authorization.
  PASS → Stage B2 (full 18-fixture qualification under the revised
  subject) is preregistered separately; FAIL → revise and
  re-preregister.

Throughout the B sequence the deployed GLM profile remains
**non-authoritative**; GATING states, fixtures, and harness are
frozen at `5472d990f3b946c3`.

## Stop conditions

Oracle_version movement without an oracle PR, subject/transport
byte drift outside an approved subject phase, prompt-hash drift, or
any model call before the phase's (a)+(b) gates = stop and escalate.
