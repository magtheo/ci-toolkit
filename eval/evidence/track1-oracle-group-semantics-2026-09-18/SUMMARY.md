# 25k acceptance bundle — oracle semantic groups (2026-09-18)

Zero-call mechanical validation of the 25k oracle repair
(`expected.groups[].alternatives[]` — a group is an OBJECT carrying
`alternatives`: **AND of required groups, OR of alternatives within a
group**), implemented per the approved #67 design.

`prove.py` is exact-head-reproducible by construction: item 11 checks
the committed diff scope (fixtures + harness + migration + tests +
state-log + this bundle ONLY) and refuses a working tree dirty
outside this bundle; the run regenerates `acceptance.json` and exits
2 until a rerun at the committed head reproduces it byte-identically.
Any violation exits non-zero; conditions are never weakened to pass.

Result: **ALL 11 ITEMS PASS** (`acceptance.json`).

| # | Item | Result |
|---|------|--------|
| 1 | #36 floor parity (new harness vs frozen floors) | haiku **51/90**, sonnet **66/90**, per-positive **18/18 both** |
| 2 | M2 remains AND | either group alone → KNOWN_GAP; both → detected |
| 3 | Alternatives are OR | M3/M11/M12/M16 accept either phrasing alternative (3/3 each) |
| 4 | Control semantics / no vacuous truth | clean passes; blocker → false blocker; 5 loader rejections; `all([])` guarded False |
| 5 | #62 pass-1 replay | haiku **51/90**, sonnet **65/90** (new `run_detects_all_groups`) |
| 6 | Residual floor violations | haiku none; sonnet **M13 only (0 < 1)** |
| 7 | #62 historical REVERT | unchanged, never rewritten |
| 8 | FB / #65 attribution parity | 91 / 139 recomputed via new harness; families RECONCILED |
| 9 | oracle_version moves, floor VALUES don't | `cb6870c5a4c635b2` → `9e20730cb0436002`; floors hash-pinned |
| 10 | Witness soundness | #35 16/11; #36 214 matched (211+3), 324/324 FBs rejected; #40 197 matched, 272/273 rejected |
| 11 | Frozen evidence immutability + needle preservation | 3/3 frozen hashes byte-identical; **36/36 fixtures: base `findings` == flattened `alternatives` verbatim** (order, severity, comment_all, comment_any); diff scope enforced incl. `eval/state-log.md`; working-tree guard |

Semantics (single canonical implementation in `eval/run_corpus.py`,
reused by harness/replays/rescores):

- alternative match = existing `_finding_matches` (UNCHANGED)
- group detected in one run = ANY alternative matches
- run-level detection = EVERY required group detected
- fixture stability = EACH group independently reaches `(N+2)//2`
  (distinct from run-level detection — pinned by test)
- false blocker = finding matching NO accepted alternative (union)

Migration: `eval/migrate_to_groups.py` (deterministic, `--check`
mode); cardinality exactly per the approved table — 18 controls `[]`,
M2 2×1, M3/M11/M12/M16 1×2, 13 positives 1×1; needles preserved
verbatim. History untouched: historical verdicts remain historical.
