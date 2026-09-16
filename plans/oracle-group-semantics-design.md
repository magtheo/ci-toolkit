# Oracle repair design — explicit semantic-group matching

Status: PROPOSAL (rev 1) — eval semantics only; reviewer untouched;
zero model calls. Follows the human-directed oracle-validity audit
(#66, head `eb023bf`) and the failure-attribution audit (#65). This
document is the design for the next oracle-repair phase; it patches
nothing itself.

## 0. Problem statement (established by #66)

1. `expected.findings[]` conflates semantic-defect cardinality with
   phrasing alternatives. Oracle repairs 4/5 added second entries to
   M3/M11/M12/M16 intending **alternative acceptable wordings of one
   defect** (documented in the repair records and witness
   adjudications); `evaluate()` (eval/run_corpus.py:384) and the
   run-level floors convention read every entry as an **independently
   required defect** (AND).
2. The frozen Deviation-6 floors equal the OR-semantics rescore of
   #36 (exact per-positive reproduction in #66); the #64 retrospective
   applied AND against those OR floors. The same mixed comparison is
   embedded in the live qualification gate.
3. Corrected understanding (human adjudication, 2026-09-16): **the
   reviewer's sensitivity is mostly intact** (haiku 51/90 vs floor
   51; sonnet 65/90 vs 66; only M13 below floor — a genuine salience
   failure on a single-entry fixture). **The major remaining problem
   is false blocking / discrimination** (#65: severity
   miscalibration + speculative harm chains 47%, counterevidence
   argued past 19%, genuine missing evidence 18%).

The repair makes the oracle express what its own repairs meant, so
that measurements of the real problem (discrimination) are trusted.

## 1. Design

### 1.1 Schema: required semantic groups, alternatives inside

```text
required semantic groups: AND
alternatives inside a group: OR
```

Fixture schema migrates from a flat entry list to explicit groups:

```json
"expected": {
  "assessment": "ISSUES_FOUND",
  "groups": [
    {"alternatives": [
      {"severity": "blocking", "comment_all": ["mtime"],
       "comment_any": ["contract", "document", "comment",
                        "invariant", "date"]},
      {"severity": "blocking", "comment_all": ["filesystem metadata"],
       "comment_any": ["parse", "date"]}
    ]}
  ]
}
```

Semantics, precisely:

- **Group detection (per run):** a semantic group is detected in a
  run if **any** matcher alternative in that group matches a finding
  of that run (the existing `_finding_matches` per alternative,
  unchanged).
- **Run-level detection (floors / replay convention):** a run detects
  iff **every required group** is detected in that run.
- **Detection stability (fixture level, `evaluate()`):** per semantic
  group, count runs in which the group is detected; the fixture
  passes sensitivity only if **every required group** reaches the
  usual threshold (N=5 → 2/3 majority, unchanged).
- **False-blocker classification (union-based, unchanged):** a
  blocking finding matching **any accepted alternative in any group**
  is expected, not a false blocker. Today's per-finding union
  semantics is preserved bit-for-bit.

Concrete migration of the five multi-entry positives:

```text
M2:  group(trigger defect) AND group(floating-ref defect)     — 2 groups
M3:  group(mtime/contract  OR  filesystem-metadata/parse-date) — 1 group
M11: group(status/hardcoded OR status-less suppression)        — 1 group
M12: group(mask/raise      OR  stale-without-distinguishing)   — 1 group
M16: group(false-success   OR  returned-on-failure {"ok})      — 1 group
```

Every single-entry fixture migrates to **1 group × 1 alternative**
(scoring identical to today, by construction).

### 1.2 Explicit migration — no heuristics

The grouping is authored into the fixture bytes by a deterministic
migration script (one commit, all 36 fixtures):

- the script emits the new `groups` form from the current bytes;
  needles (`severity`, `comment_all`, `comment_any`) are
  **byte-identical** — only structure changes;
- the mapping is asserted against the #66 semantic-unit table
  (M2 → 2 groups; M3/M11/M12/M16 → 1 group of 2; all others → 1×1)
  and the build fails closed on any deviation;
- the loader (`load_corpus`) accepts **only** the new schema — old
  flat form is a load error, preventing silent mixed states;
- no runtime inference of grouping from history, ever.

### 1.3 Harness changes (the only code change)

- `eval/run_corpus.py`: `evaluate()` computes per-group stability and
  requires all groups at threshold; false-blocker matching iterates
  the union of alternatives (semantics unchanged); the run-level
  "all groups per run" convention becomes a named helper so the
  floors replay, retrospective tooling, and the future gate share one
  implementation.
- `_finding_matches`, thresholds, N, pair integrity, GATING states,
  qualification rules: unchanged.
- Deterministic tests updated + added (see §3).

### 1.4 What does NOT change

- Matched needles (byte-identical), rubric, prompts, `engine.py`,
  `parse_review.py`, `render.py`, `review.sh`.
- The frozen artifacts: #33/#35/#36/#40/#62/#64 bundles and
  `witness-replay.json` — **including the floor VALUES**, which stay
  the normative reference. The repair changes how entries are *read*,
  not what the floors require; #66 proved the floors already encode
  the intended semantics (exact reproduction), and §3 pins that
  equivalence forever as a regression test.
- Prior measurements: each frozen bundle stays valid under its
  recorded `oracle_version`; the state-log records the #64
  mixed-convention finding (already recorded in #66) — history is
  not rewritten.

### 1.5 oracle_version

Moves (harness + corpus bytes change → both are oracle inputs). Per
the methodology rule, changing oracle semantics invalidates prior PASS
records — **there are none** (T1.2 INCOMPLETE; no qualification
activation has ever occurred). The state-log entry lands with the
implementation phase.

## 2. Acceptance bar (mechanical, zero model calls)

All from frozen evidence; the implementation PR is correct only if
every item demonstrates green:

1. **#36 floors parity**: rescore under the new harness reproduces
   the existing frozen per-positive floors exactly (18/18 × both
   profiles; aggregates 51/90 and 66/90).
2. **M2 stays AND**: dropping either group alone fails the fixture
   (deterministic test with synthetic ablations).
3. **M3/M11/M12/M16 alternatives**: each phrasing extension is
   accepted as an alternative of its group (deterministic tests).
4. **#62 pass-1 rescore**: haiku 51/90, sonnet 65/90.
5. **Residual floor violations**: only sonnet M13 (0 < 1).
6. **#62 REVERT stands**: verdict artifacts untouched; no criterion
   re-evaluation in this repair.
7. **Control FB and attribution totals unchanged**: C7/control-FB
   story untouched; the #65 population derivation re-reconciles
   91/139 + family totals against the migrated corpus.
8. **oracle_version changes; frozen floor values do not.**
9. **Witness soundness holds** (the false-acceptance guard): #35 →
   16 genuine accepted / 11 negatives rejected; #36 → 214 matched
   (211 expected-expression + 3 adjudicated), 324/324 false blockers
   rejected; #40 replay parity (197 matched; 272/273 FBs rejected).
10. **Old evidence immutable**: no frozen bundle or floor value
    modified; git history is the proof; state-log records, never
    rewrites.

## 3. Implementation shape

- **One phase PR** (`25k` on this feature branch): migration script +
  migrated fixtures + harness change + test updates + a zero-call
  validation bundle (eval/evidence/track1-oracle-group-semantics-<date>/)
  containing the §2 acceptance outputs and the rerun parity/replay
  scripts against the new schema.
- Eval semantics and reviewer intelligence stay in separate PRs (this
  repair touches no reviewer file at all).
- After human merge: oracle trust is restored; only then does the
  iteration-5 design PR follow, carrying the human's working
  hypothesis — *the primary discrimination failure is failure to
  establish a demonstrated, present defect before escalating an
  observation to blocking severity* — against trusted measurement.

## 4. Risks and mitigations

- **False-acceptance widening (OR accepts more)**: mitigated — the
  alternatives are the already-adjudicated frozen needles with their
  #37 context requirements intact; acceptance item 9 re-proves all
  witness rejections mechanically.
- **Schema churn / mixed states**: loader is fail-closed on the old
  schema; migration is one explicit commit; corpus_hash moves with
  the bytes.
- **Floors drift**: the floors file is untouched; item 1 is a
  permanent regression test pinning harness ↔ floors equivalence.

## 5. Non-goals

No reviewer change; no rubric/prompt change; no threshold or state
change; no new measurement campaign; no iteration-5 design in this
repair; no reinterpretation of frozen verdicts.
