# Oracle repair — C11/M11 invalid Prisma flag (2026-09-20)

Phase 04 of `feature/glm-profile-qualification`. Directed by the
maintainer after Stage B0 (PR #79, merge `405b589`) verified the
defect. **This PR changes oracle semantics only** — fixtures C11 and
M11 plus the identity pins that move with them. No rubric, engine,
transport, harness-semantics, or states.json change; C8 remains
untouched pending independent adjudication.

## The defect

`C11` (control, expected CLEAR) presented a CI wrapper invoking
`npx prisma migrate status --skip-generate`. `--skip-generate` is
**not a valid option of `prisma migrate status`** — the Stage-A
model said so (high run2, max run1) and B0 verified it against the
official CLI reference. With the flag, the CLI rejects the
invocation, the `>/dev/null 2>&1` redirect hides the error, and the
wrapper always reports `{"status":"failed"}`: the control can never
pass, so it measures the model's factual correctness, not
calibration.

Source of truth (pinned):
- Prisma ORM **v7** CLI reference — `migrate status` Options table
  lists exactly `--help`/`-h` and `--schema`:
  https://www.prisma.io/docs/orm/reference/prisma-cli-reference#migrate-status
  (accessed 2026-09-19 and 2026-09-20; independently confirmed by
  the maintainer).
- `--skip-generate` is documented only on `migrate dev` /
  `migrate reset`; Prisma v7 additionally removed it from
  `db push` ("The `--skip-generate` flag was removed in Prisma
  v7", db push section of the same reference).

## The repair (minimal, distinction-preserving)

One line changed in each fixture patch — the flag removed from the
`npx prisma migrate status` invocation; nothing else:

- **C11** keeps the full intended control semantics: documented
  always-exit-0 + JSON contract, `status` **derived from the
  command's outcome** (`if npx prisma migrate status …; then
  status=ok; else status=failed`), output discarded. Post-repair the
  command is valid, so the control can legitimately report ok or
  failed — it tests calibration again, not CLI trivia.
- **M11** keeps its isolated injected defect intact: `status=ok`
  **hardcoded** with the command outcome discarded via `|| true`.
  The expected detection groups (blocking finding citing `status`
  plus always/hardcoded/never/ignored/swallow/`|| true`, or the
  `|| true` alternative) are unchanged — the positive remains
  detectable for exactly the reason that made it a positive.

The control/positive distinction is therefore preserved exactly:
correct outcome-derived failure reporting (C11) vs hardcoded success
that swallows the outcome (M11).

## Identity movement (fail closed)

- `oracle_version`: **`9e20730cb0436002` → `5472d990f3b946c3`**
  (content hash of the eval implementation + every fixture byte +
  states.json; the fixture edit moves it by construction).
- Updated with it: `ORACLE_VERSION` in `eval/profile_qualification.py`
  and the two pinned literals in `tests/test_profile_qualification.py`
  (oracle-stability test + campaign-identity test).
- `tests/golden_prompts_q0.json`: the **user-prompt** hashes for C11
  and M11 regenerated (`6e6b8ed87d4d8897 → 8bc83a958a5b2283`,
  `6a20f0dd1132c486 → 3085b0499ff8cd6d`); system prompts and all 34
  other fixtures byte-identical.
- `ORACLE_CHECKOUT_SHA` (`4b116a7…`) stays as the **lineage origin**
  provenance; from this repair onward the oracle is pinned by
  content equality (`oracle_version`), which the identity test
  asserts against the live tree ("no history needed").

## Non-retroactivity

Stage-A, Q0, and B0 records keep their original identities. Nothing
historical is relabeled; no result is claimed to have passed the
repaired corpus. Any qualification under `5472d990…` starts fresh —
the Stage B1 preregistration (phase 05) will pin the new identity.

## Validation

Full deterministic suite: **230 passed** (includes: prompt golden
byte-identity, oracle-inputs-untouched-and-version-stable at the new
constant, campaign-identity at the new constant, M11 alternative-
group semantics, and the GATING ratchet). Suite must be green at the
exact PR head.
