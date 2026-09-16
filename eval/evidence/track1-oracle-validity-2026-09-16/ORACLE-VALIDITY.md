# Oracle-validity audit — expected-entry semantics (DIAGNOSTIC, zero model calls)

Question (human-directed, 2026-09-16): **for repaired fixtures, do
multiple `expected.findings[]` entries represent multiple
independently required defects, or alternative acceptable
descriptions of the same underlying defect?** And: **what part of the
measured sensitivity failure is reviewer behavior, and what part is
the oracle asking for the wrong thing?**

This audit changes nothing: no oracle edit, no matcher patch, no
rubric/prompt change, no threshold change, no state change, no model
calls. #62/#64 frozen artifacts untouched. It measures and reports;
repair design is a separate human decision.

Companion artifact: `oracle-validity-replay.json` (produced by
`semantic_replay.py` from committed frozen inputs only).

## 1. Method

Sources (all committed, frozen):

- **#36** raw reports: `track1-baseline3-2026-09-07/{haiku,sonnet}-n5.json`
  (subject `4b07246`, the Deviation-6 floor source run)
- **#62** pass-1 traces: `track1-t13-iter4-measurement-2026-09-15/raw/`
  joined via `(model_id, digest)` exactly as `pass1_rescore.py`
- fixture corpus + harness matcher (`eval/run_corpus.py:
  _finding_matches`, eval/run_corpus.py:348)
- repair history: state-log, commits `c14e309` (repair 4) +
  `5d04505` (#37 review corrections), repair 5 (`f8f691b`, PR #42),
  PR #37 body, repair-4/5 `witness-replay.json`

Built-in fail-closed validity (`semantic_replay.py`): before any
candidate-semantics number is produced, the comparator must

1. reproduce #64's retrospective headline (36/90, 47/90) from the #62
   traces under S0/AND (the convention `pass1_rescore.py` actually
   used), and
2. reproduce the frozen normative floors
   (`track1-oracle-repair4-2026-09-07/witness-replay.json`,
   `replay.per_positive_detections`) per-positive from the #36 raw
   reports under **exactly one** of the two candidate semantics —
   ambiguity aborts. The comparator discovers which: it is **S1/OR**
   (S0 gives 36/90 and 52/90 and provably does not reproduce them;
   see Finding 2).

Both hold, so every delta below is attributable to entry semantics
alone, not to a reimplementation drift.

### Candidate semantics

- **S0 (current harness convention)** — a run detects iff **ALL**
  expected entries match. This is what `evaluate()` enforces at
  fixture level (`detected_ok = all(per-entry majority)`,
  eval/run_corpus.py:384) and what the #64 retrospective enforced at
  run level (`fixture_level_detection`, all entries per run).
- **S1 (intended, if entries are alternative phrasings)** — a run
  detects iff **ANY** expected entry matches.

## 2. Fixture-semantics table (history-based, not structure-inferred)

Multi-entry positives: M2, M3, M11, M12, M16 (all other positives are
single-entry and therefore convention-invariant).

| fixture | expected entries | intended semantic units | history of each entry | current oracle semantics | match? |
|---|---|---|---|---|---|
| **M2** (workflow runs PR code from floating ref) | 2: (a) `pull_request` trigger / trusted-base, (b) unpinned floating ref | **2 independent required aspects** — AND intended | both entries present since T1.1 corpus creation (`7b43ee8`); repair 2 only added needles *inside* entry1; the subject PR title names both facets ("trigger and references") | requires both | **correct** |
| **M3** (roadmap freshness guard uses mtime instead of the documented parsed date) | 2: (a) `mtime` + contract/date anchor, (b) `filesystem metadata` + parse/date anchor | **1 defect**; entry1 = "filesystem metadata" phrasing of the same mtime-vs-documented-date defect | entry1 added by repair 4 (#37): "parsed-date **phrasing**", "original mtime entry byte-preserved"; adjudicated from the #36 validity audit as a **matcher-gap** (genuine detections rejected by frozen needles) | requires both | **defect — AND misrepresents OR intent** |
| **M11** (migration check hardcodes success, suppresses failure exit) | 2: (a) `status` + always/hardcoded/`|| true`, (b) `|| true` + suppress/exit-code | **1 defect**; entry1 = the status-less phrasing family of the same suppression defect | entry1 added by repair 5 (#42): "the **status-less phrasing family**", original entry untouched; witness = haiku #40 r0f1, adjudicated genuine | requires both | **defect** |
| **M12** (config fallback silently returns instead of documented raise) | 2: (a) mask/KeyError/`{}`/instead-of-raising family, (b) `stale` + without-distinguishing/different-failure-mode | **1 compound contract violation** (one `except: return` line violates the documented resilience contract on two faces); entry1 = the stale-without-distinguishing phrasing family | entry1 added by repair 4 (#37): "masking-visibility **phrasing**", original entry preserved; repair-4 replay flips adjudicated as genuine detections | requires both | **defect** |
| **M16** (label sync swallows exception, fabricates `{"ok": true}`) | 2: (a) swallow/fabricat/false-success family (needles extended repairs 3+4 *within* the entry), (b) `{"ok` + returned-on-exception family | **1 defect**; entry1 = fabricated-success stated as returned-on-failure | repair 3+4 changed needles inside entry0 only; entry1 added by repair 5 (#42): "fabricated-success **stated as returned-on-failure**"; frozen #35 response-shape negative remains rejected | requires both | **defect** |

Intent evidence is not inferred from structure: the repair records
themselves classify the added entries as **phrasing-family
extensions** and the corresponding witness narratives as genuine
detections of the *same* frozen defect ("novel phrasings genuinely
express the frozen M16 defect but miss the frozen needles — CONFIRMED
MATCHER MISCLASSIFICATION", state-log 2026-09-06). A matcher
misclassification of a genuine detection is by definition an
alternative-wording problem, not a new required defect.

## 3. Findings

### Finding 1 — the harness has no way to express "alternative wordings for one defect"

`expected.findings[]` conflates semantic-defect cardinality with
phrasing alternatives. When repairs 4/5 used a second entry to mean
"wording A **OR** wording B", `evaluate()` (and the #64 run-level
convention) read it as "defect A **AND** defect B". A reviewer run
that states the defect in the original wording now **fails** whenever
it does not additionally use the new phrasing family. Measured
directly on #62: for haiku M3/M12/M16, entry0 matched in **all 5
runs** and entry1 in **0** — five genuine detections scored as five
misses.

### Finding 2 — the normative floors and the harness disagree on semantics

The replay proves (exact per-positive reproduction, 18/18 both
profiles, aggregates 51/90 and 66/90):

- **The frozen Deviation-6 floors equal the S1/OR-semantics rescore**
  of #36 — not the S0/AND rescore (S0 gives 36/90 and 52/90 and does
  not reproduce the frozen values). This is consistent with the
  repairs' intent: original entries were byte-preserved, so every
  originally-counted run still counts; added alternative entries can
  only add matches.
- **#64's retrospective applied S0/AND against those S1/OR floors.**
  The recorded comparison (haiku 36/90 vs floor 51; sonnet 47/90 vs
  floor 66) mixed conventions.

### Finding 3 — replay under convention-consistent semantics

Detection totals (runs detecting, out of 90 = 18 positives × 5):

| | haiku | sonnet |
|---|---|---|
| floors under AND | 36 | 52 |
| floors under OR (= frozen normative) | **51** | **66** |
| #64 retrospective under AND (as recorded) | 36 | 47 |
| #64 retrospective under OR | **51** | **65** |
| violations, AND vs AND | **0** | 4 (M11 2<3, M12 0<2, M13 0<1, M3 0<1) |
| violations, OR vs OR | **0** | **1 (M13 0<1)** |
| as recorded in #64 (AND vs OR — mixed) | 3 (M3, M12, M16) | 5 (M3, M11, M12, M13, M16) |

Interpretation:

- **haiku: the entire recorded sensitivity regression (36 vs 51) is
  an oracle-representation artifact.** Under either consistent
  convention the reverted single-stage reviewer exactly meets every
  haiku floor (36/36 AND, 51/51 OR).
- **sonnet: 18 of the 19 recorded shortfall points are representation
  artifacts.** Under intended semantics the reviewer misses exactly
  one floor run: **sonnet M13 (0 < 1)** — a single-entry fixture,
  i.e. the one residual that no entry-semantics choice can explain.
  #65's diagnostic stands: M13's five misses are genuine
  attention/salience failures (the missing tag input was never
  noticed under security-chain load).
- The 38 entry-level sensitivity diagnostics in #65 remain accurate
  as entry-level observations (22 wording-family + 16
  evidence-present-but-missed), but under intended semantics **33 of
  the 38 diagnosed runs actually detect** via their original entry;
  only sonnet M13's 5 runs remain genuine non-detections.

### Blast radius

- **#64**: measurements are internally correct under their stated
  (AND) convention and are NOT rewritten. The material change is to
  the *comparison*: recorded floors-side violations M3/M12/M16 (both
  profiles) and M11/M12/M3 (sonnet AND) dissolve under
  convention-consistent scoring; sonnet M13 survives. #64 used the
  then-current oracle semantics; this audit estimates how much of the
  observed sensitivity loss is attributable to oracle representation:
  **haiku — all of it; sonnet — all but one run.**
- **#62 campaign verdict / executed revert**: unaffected — the
  two-stage mechanism produced zero final blocking findings under any
  semantics (verifier fence-rejection → INCONCLUSIVE everywhere), so
  criterion 5 failed regardless of convention; C7 GATING and the
  control-FB criteria are entry-semantics-independent (controls have
  no expected entries; false-blocker classification matches each
  finding against the *union* of entries, eval/run_corpus.py:397).
- **#65 false-blocker attribution**: unaffected — its population and
  classifications are per-finding (union-of-entries matching), with
  no run-level conjunction anywhere in the pipeline.
- **Future qualification runs**: exposed. The live harness would
  judge any future mechanism under AND semantics against OR-based
  floors — the same mixed comparison that distorted #64, embedded in
  the qualification gate itself. This must be resolved before T1.2
  can be trusted again.

## 4. Repair directions (NOT executed — human decision required)

Recorded for the follow-up oracle-repair design; none implemented
here, per the no-patch-while-diagnosing rule:

1. **Explicit alternative-group semantics** in the corpus schema
   (e.g. entries grouped as alternatives of one semantic unit), with
   `evaluate()` and the run-level convention reading groups as OR;
   floors rescored under the repaired oracle; `oracle_version`
   bump; witness replay re-run (the repair-4/5 witness sets
   adjudicate directly — they already treat the added entries as
   same-defect acceptances).
2. **Collapse alternatives into one entry per defect** (merge needle
   families) — simpler schema, but loses the context-requirement
   discipline the two-stage entries encode (`stale` AND
   without-distinguishing), and risks the false-acceptance the
   #37 review corrections were made to prevent.
3. **Declare entries AND-intended going forward** — contradicts the
   frozen repair adjudications and the floors' own rescore semantics;
   recorded as rejected for completeness.

The floors themselves need no change under option 1: they already
equal the intended-semantics rescore (Finding 2). What needs repair
is the *reading* of entries — harness, retrospective convention, and
any future gate must agree with the frozen floors.

## 5. Methodological limits

- The OR reading of the floors is *proved by exact reproduction* and
  corroborated by repair-intent language and witness adjudications,
  but the original rescore's implementation was not documented
  step-by-step in the artifact; the reconstruction is this audit's
  own (fail-closed: it reproduces the frozen numbers exactly, while
  the AND reading provably does not).
- History-based intent classification is documented above per fixture;
  M2's "AND intended" rests on creation-time structure + subject-PR
  facet analysis (no contrary evidence found in any repair record).
- This audit quantifies #62/#36 frozen outputs only; it makes no
  claim about the reverted reviewer's general sensitivity beyond this
  sample, and it does not reactivate T1.2 (C7 GATING remains failed
  on both profiles from #36/#62-era measurements; #64 remains
  diagnostic).

## Reproduce

```bash
python3 eval/evidence/track1-oracle-validity-2026-09-16/semantic_replay.py
```

Zero model calls; reads only committed frozen artifacts; fails closed
if the parity proofs do not hold.
