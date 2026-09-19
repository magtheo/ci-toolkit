# Track 1 oracle repair — 2026-09-05

Eval-semantics-only phase (reviewer untouched, zero model calls).
Triggered by the T1.2 diagnostic run's derived-evidence pass
(`../track1-baseline-2026-09-05/`), which exposed corpus/oracle
validity defects. Lifecycle recorded as plan **Deviation 5**: T1.2
remains incomplete; this repair precedes the binding T1.2
remeasurement.

## Audit of the 96 fragment/placeholder-artifact codings

Decomposed from the frozen `narrative-coding.jsonl`:

| class | fixtures | codings | ruling |
| --- | --- | --- | --- |
| Added-file fragment symbols | C12 (33), M12 (25), C16 (10), M16 (13) | 81 | **Corpus defect — repaired.** For `added` files the reviewer cannot assume omitted module context: C12/M12 now define `CONFIG_URL`, `OriginError`, `ParseError`, `_decode`; C16/M16 now define `LABELS`. |
| Placeholder SHA | C1 (2 incl. sonnet placeholder-blocking), C2 (1) | 3 | **Corpus defect — repaired.** All four fixtures (C1/M1/C2/M2) now use realistic 40-hex SHAs; C1/M1 additionally gained least-privilege `permissions` + fork guard (added files must model the safe pattern as presented). C2's "missing permissions" blocker re-ruled invalid for a modified file (context implied). |
| Modified-file fragment claims | M7 (12) | 12 | **Fixture VALID as presented.** A `modified` file's diff semantically implies surrounding content; asserting undefined imports/constants is a hallucinated absence (reviewer behavior). Ruling recorded; frozen coding stands, family judgment refined to `hallucinated-fact` in any post-repair recoding. |

## Audit of the 55 matcher-vocabulary gaps

Inspected individually; extended **only** where the emitted narrative
genuinely expresses the already-frozen expected defect (monotonic —
original needles preserved; enforced by test):

| fixture | gaps | ruling |
| --- | --- | --- |
| M9 | 13 | 11 extended (message/branch/contradiction phrasings of the frozen inversion defect: `contradict/message/opposite/branch/prints/claims/executes when/wrong branch`); 2 ("lacks executable permission") re-ruled NOT defect expressions — remain false blockers (advisory-grade). |
| M10 | 13 | regex/anywhere narratives genuinely state the frozen non-anchoring defect: `comment_all ['search']` relaxed to any-of with `search/anywhere/not anchored` (+originals). "No tests" narratives remain false blockers. |
| M12 | 17 | docstring/`{}`/instead-of-raising narratives genuinely state the frozen masking defect: `comment_all ['parse']` relaxed to any-of including `parse` (+originals, +`docstring/contradict/instead of raising`). Concurrency/test-requirement narratives remain false blockers. |
| M16 | 5 | fabricated-success narratives genuinely state the frozen defect: `comment_all ['except']` relaxed to any-of including `except` (+originals, +`fake success/misleading/mask/returns {`). |
| M2 | 3 | `toolkit_ref: main` narratives genuinely express the SECOND frozen finding (floating ref): any-of extended with `toolkit_ref/supply/latest` (original `@main` needle missed the no-@ phrasing). |
| M6 | 4 | **NOT extended.** The narratives claim an *inversion*; the frozen defect is per-line-vs-slurp semantics (`jq -e` without `-s`). They misattribute the mechanism — not genuine expressions. Remain false blockers. |

## Round 2 (external review): embedded diff structure + witness-tested matchers

**Unified-diff structure validator** (oracle-hashed, in
`_validate_patch_structure`): every fixture patch's hunk headers are
checked against the actual bodies — old-side = context + removed,
new-side = context + added, canonical `-0,0` for added files, fail
closed on malformed headers/body lines. Running it across the corpus
revealed **19 fixtures with stale or non-canonical hunk metadata**
(C1, C4–C7, C9, M1–M4, M6–M9, M10–M13, M15, M16 — including
Phase-2-era headers like `-1,0`), all recomputed to their actual
counts. The exact patch string is reviewer input; malformed diff
metadata was itself a corpus-validity artifact. Tests prove wrong
old-side and new-side counts are rejected.

**Matcher-repair validation strengthened beyond lexical monotonicity.**
The first repair's union-preservation test was judged insufficient:
for M10/M12/M16 the required `comment_all` concepts had been moved
into a broad `comment_any` pool, admitting generic-token matches
(`search`/`parse`/`except` alone). The final design:

- needles are semantically sufficient phrases; generic single tokens
  dropped (M12 additionally drops bare `empty` — the witness set
  showed test-requirement narratives saying "empty cache raising"
  would false-accept);
- the frozen #30 diagnostic evidence is used as a deterministic
  **witness set** (`matcher-witnesses.json`, 122 witnesses: 69
  `genuine_expected_expression`, 53 `not_expected_expression`, every
  gap narrative ruled explicitly — including the rejected M9 chmod
  pair, the M6 inversion narratives as negatives, and unrelated
  blockers on every affected positive);
- the enforced invariant: **all previously accepted genuine
  detections remain accepted + every audited genuine gap becomes
  accepted + every audited non-defect narrative stays rejected**
  (test_matcher_repair_semantics_via_frozen_witnesses);
- the existing matcher schema sufficed — no OR-of-conjunctions
  complexity was needed.

## Deterministic guards added (authoring failure classes)

In `eval/run_corpus.py` (inside the oracle hash), enforced by
`load_corpus` + tests:

1. **Placeholder-SHA guard** — any 40-hex token that is all-same-char
   or contains the ascending `0123456789abcdef` pattern is rejected.
2. **Added-python self-containment lint** — bare UPPER_CASE constants
   and `*Error`/`*Exception` names must be defined in the file
   (assignment/def/class/import; dotted `module.Name` covered by the
   import; stdlib exception allowlist).
3. **Added-shell variable guard** — every UPPER_CASE variable read
   must be assigned or `: "${VAR:?…}"`-guarded in-script.
4. **Matcher monotonicity test** — pre-repair needle unions
   (snapshotted from merged #30, `de57cd0`) must remain subsets of
   the repaired unions: extensions only ever gain needles.

## Identity

- `oracle_version`: `92683f53fb1f7e30` → **`9fae85b26ff45dc6`**
  (round 1 `61380c91e84db0ef` superseded by the round-2
  diff-structure repairs + witness-driven needle redesign)
  (corpus + harness lint changes; states untouched — all 36 fixtures
  remain KNOWN_GAP / GATING as before; family taxonomy unchanged).
- Full human semantic audit of the repaired corpus:
  `fixture-audit.json` — all 36 fixtures judged on control-cleanness
  as presented, intended-defect presence, unrelated blocking defects
  (none), and pair delta. **Frozen before any remeasurement spend
  authorization.**
- Spend: **0 model calls.**

## Next (not in this PR)

Fresh unchanged-reviewer T1.2 remeasurement, N=5, both profiles —
that run (with the same narrative/grounding/false-clear derivations)
becomes the binding T1.3/T1.5 reference. T1.3 target family is chosen
only after it.
