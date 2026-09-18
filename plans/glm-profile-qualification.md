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

## Phase 02 — Stage A (BLOCKED on human decisions)

Full matrix, metrics, selection rule, and spend gate are
pre-registered in
`eval/evidence/q0-glm-profiles-2026-09-18/README.md` — written
before any profile result exists. Stage A runs ONLY after (a) human
review of Phase 01 and (b) explicit spend authorization. It is
**profile screening**: no state promotion, no GATING changes, no
iteration-5, no deployment pin change, no fleet rollout follow
automatically from its outcome.

## Stop conditions

Oracle_version movement, subject/transport byte drift, prompt-hash
drift, or any model call before (a)+(b) = stop and escalate.
