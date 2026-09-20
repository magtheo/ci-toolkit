# Stage B0 — D3 false-positive attribution (zero model calls)

Source: frozen Stage-A evidence
`eval/evidence/stage-a-glm-profiles-2026-09-19/` (324 records, oracle
identity `9e20730cb0436002`, Q0 merge `cdaf736`, Stage-A publication
merge `e192978`). **No model calls were made**; this analysis only
reprocesses persisted findings against fixture content and
`rubric.md`. Every number below is mechanically derivable from
`classification.json` (built by `build_classification.py`, which
fails closed if any blocking control finding is unclassified).

## Scope of the failure

10 of 18 control-designated fixtures received at least one blocking
finding; 58 blocking findings span 49 distinct control–effort–run
combinations (low 16, high 15, max 18). Of those fixtures, C11 is an
oracle defect and C8 has four findings awaiting adjudication; these
must not be counted as confirmed false-positive controls.

| control | blocked runs (L/H/M) | blocking findings | dominant model argument |
|---|---|---|---|
| C12 | 2/2/3 | 12 | `except OriginError` "dead code" + KeyError type vs documented "raises" |
| C3 | 3/2/3 | 10 | "guard must exit non-zero" / missing-file blind spot / mtime-vs-checkout |
| C13 | 3/3/3 | 9 | `pull_request_target` fires on update, "contradicts publish on merge" |
| C8  | 3/2/0 | 6 | Riverpod `listenManual` lifecycle; "already-set course never resumes" |
| C16 | 2/1/2 | 6 | collection-PUT "replaces label set"; 4xx/5xx "treated as success" |
| C2  | 3/1/1 | 5 | `pull_request_target` + secrets = "pwn request" (unseen callee) |
| C10 | 0/1/2 | 3 | no tests for a security gate |
| C4  | 0/2/1 | 3 | "scope violation": docs-only title + new class (caused D2) |
| C11 | 0/1/1 | 2 | `--skip-generate` invalid for `migrate status` — **model right, oracle wrong** |
| C15 | 0/0/2 | 2 | no tests |

## Attribution — exact reconciliation

Every one of the 58 blocking findings is assigned exactly one primary
category (`classification.json` asserts total coverage):

| primary | count | meaning |
|---|---|---|
| `invented` | **20** | defect not demonstrable in the diff: speculation about unseen callees/APIs/framework behavior (C2 ×5, C3 ×8, C12 ×3, C16 ×3, C8 ×1), or a contract invented from the PR title |
| `severity` | **18** | observation true in the abstract but advisory-grade here, escalated to blocking (C13 trigger-vs-title ×9, C12 exception-type polish ×5, C3 deployment-context ×2, C16 HTTP-status ×2) |
| `rubric` | **14** | the rubric itself licenses the block: "missing tests for core behavior" ×11 (C10 ×3, C12 ×4, C15 ×2, C16 ×1, C8 ×1) and "scope violation" ×3 (C4 — this produced the **D2 GATING regression** at high/max) |
| `pending-adjudication` | **4** | C8 `listenManual` lifecycle findings — framework-contract knowledge that may be correct against an under-specified synthetic fixture; excluded from the false-positive count until adjudicated |
| `correct-not-fp` | **2** | C11 — **verified oracle defect**: Prisma CLI reference documents `migrate status` options as exactly `--help`/`--schema`; `--skip-generate` is invalid, so the fixture's wrapper can never pass. The model was right; the corpus was wrong. |

**Reconciliation of earlier drafts**: the first-pass tallies
(17+21+14=52) closed to 52 of 56 claimed true false positives. The
four unaccounted findings are the C8 `listenManual` set, which belong
to category (6) pending adjudication rather than (1)/(2)/(3). True
false-positive count is therefore **52 actionable + 4 pending**, not
56; all 58 findings (including the two C11 findings) have attribution
rows with short comment excerpts in `classification.json`. Full original
findings remain verbatim in the frozen Stage-A `records.jsonl` files.

## Synthesis — the calibration hypothesis

**The attribution supports a combined evidence-threshold and severity-
calibration hypothesis, not a pure effort-tuning explanation.** Some
findings identify real but advisory-grade concerns; 20 others rely on
unsupported or invented claims, and two correctly expose the C11
oracle defect. The reviewer promotes speculative, external, or
advisory-grade concerns to `blocking`, while the current rubric
actively licenses two of those promotions ("missing tests", "scope
violation") and places no demonstrability burden on blocking claims.

Parser/render layer exonerated: all severities were model-emitted;
zero parse or render artifacts (0 INCONCLUSIVE at low/high; the 2 at
max were genuine budget exhaustions).

## Approved direction (not execution)

The directing human approved the calibration **direction** with
revisions; nothing below authorizes paid execution:

**Rubric intervention (subject change → its own PR; eval semantics —
fixtures, states, harness — stay frozen):**
- A reviewer-invented assumption about unseen code cannot
  independently justify blocking.
- An absolute contract claim introduced **by the diff itself** can
  still warrant blocking when central to the change and the supplied
  evidence cannot establish it (preserves M4-style detection).
- Missing tests and scope violations are not automatically blocking;
  severity depends on a concrete correctness, security, or
  regression consequence. The ability to block a genuinely unsafe
  change is retained.

**Stage B1 matrix (draft preregistration, 15 fixtures × N=3 ×
{low, high} = 90 reviews):** recurrent false-positive controls C2,
C3, C12, C13, C16 + C4 (independent D2 cause) + their paired
positives M2, M3, M4, M12, M13, M16 + never-blocked controls C1, C5,
C14. C8 **excluded** until adjudicated (its B0 findings remain on
record). Preregistered pass criteria: zero control false-blocks; no
loss of paired-positive detection under a precisely defined
per-group comparison vs the Stage-A per-fixture baseline; no GATING
regression. **M4 detection reported separately** so a baseline miss
cannot make continued failure look like success.

## Required follow-ups (human-directed sequence)

1. This B0 publication (phase 03).
2. **Oracle repair PR**: correct C11 **and its paired positive M11**
   (remove the unsupported flag while preserving the distinction
   between correct failure reporting and a hardcoded success). Pin
   the relevant Prisma version and link the CLI reference in the
   repair evidence. The repair **moves `oracle_version`**; Stage-A
   records keep their original identity intact — no relabeling, no
   claim that historical results passed the repaired corpus.
3. C8 adjudication (independent; do not silently reclassify).
4. Finalize the B1 preregistration (freeze amended rubric, repaired
   oracle identity, matrix, spend ceiling) — then human review
   before live mode.
5. The deployed GLM profile stays **non-authoritative** throughout;
   rotate the exposed OpenRouter key before any further campaign.
