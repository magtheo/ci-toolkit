# Track 1 measured discrimination baseline (T1.2) — 2026-09-05

> **STATUS: DIAGNOSTIC MEASUREMENT — NOT THE BINDING T1.2 REFERENCE.**
>
> This 360-call run completed and is preserved immutable as evidence.
> Its derived-analysis pass exposed **corpus/oracle validity defects**:
> at least some controls are not genuinely self-contained or globally
> clean as presented (e.g. added-file controls referencing undefined
> symbols: C12 `CONFIG_URL`/`OriginError`, C16 `LABELS` — for an
> `added` file the reviewer cannot assume omitted module context, so
> those blockers are valid against the fixture input); and 55 coded
> matcher-vocabulary gaps express already-frozen expected defects in
> wording outside the frozen needles — they are not reviewer false
> blockers either. Consequently:
>
> - **T1.2 remains INCOMPLETE** pending the oracle-repair phase and a
>   fresh unchanged-reviewer N=5 dual-profile remeasurement; that
>   later run is the binding sensitivity floor for T1.3/T1.5.
> - The floors, per-family tables, and emitted-blocker aggregation
>   below are **diagnostic** of both the reviewer and the oracle; no
>   final T1.3 dominant-family target is named from this data.
> - Repair happens in a separate eval-semantics-only phase PR after
>   this bundle merges as historical evidence.

Frozen non-regression reference for T1.3/T1.5 (plan rev 5). The
unchanged reviewer (subject `46b9547` — merged T1.1 feature branch)
against the full 36-fixture corpus, N=5, both required profiles.

**Experimental feature-branch evaluation only — no deployment
qualification claim** (plan Deviation 4). Evidence-only stage: no
reviewer changes, no corpus adaptation, no state changes.

## Identity and spend

| | haiku | sonnet |
| --- | --- | --- |
| model | `anthropic/claude-haiku-4.5` | `anthropic/claude-sonnet-4.5` |
| report | `haiku-n5.json` | `sonnet-n5.json` |
| calls | 180 | 180 |
| prompt tokens | 241,115 | 241,115 |
| completion tokens | 76,389 | 74,327 |
| retries (stderr) | 0 | 0 |

- subject SHA: `46b9547b9b5a253687a16fb8cb74ccdad212cb5e` (both reports)
- oracle_version: `92683f53fb1f7e30` · rubric hash per report profile
- temperature 0.2, max_tokens 2000, N=5, timestamps in each report
- total provider attempts: **360** (360 logical + 0 retries) — within
  the authorized 400-call envelope
- identical prompt-token totals across profiles = deterministic
  prompt construction (audit signal)
- console logs: `*.stdout.log`, `*.stderr.log` (retry accounting)

## Sensitivity floors (frozen) — `floors.json`

Per-positive minimum expected-finding hits out of 5. T1.3/T1.5 gate
runs may not fall below these on the same profile (invariant 1):

| id | haiku | sonnet | | id | haiku | sonnet |
| -- | ----- | ------ |-| -- | ----- | ------ |
| M1 | 5 | 5 | | M12 | 1 | 2 |
| M2 | 5 | 5 | | M13 | 1 | 0 |
| M3 | 5 | 5 | | M14 | 5 | 5 |
| M4 | 2 | 0 | | M15 | 0 | 0 |
| M5 | 0 | 0 | | M16 | 5 | 4 |
| M6 | 1 | 0 | | M17 | 0 | 5 |
| M7 | 5 | 5 | | M18 | 0 | 5 |
| M8 | 5 | 5 | | M9 | 0 | 5 |
| M10 | 2 | 0 | | M11 | 5 | 5 |

## Per-family discrimination

| family | profile | controls clean | false blockers | positives detected |
| --- | --- | --- | --- | --- |
| hallucinated-fact | haiku | 0/4 | 22 | 1/4 |
| hallucinated-fact | sonnet | 0/4 | 36 | 2/4 |
| speculative-consequence | haiku | 0/3 | 31 | 1/3 |
| speculative-consequence | sonnet | 2/3 | 27 | 1/3 |
| risk-boilerplate | haiku | 0/4 | 41 | 1/4 |
| risk-boilerplate | sonnet | 0/4 | 46 | 0/4 |
| severity-inflation | haiku | 1/2 | 8 | 0/2 |
| severity-inflation | sonnet | 0/2 | 22 | 0/2 |
| absolute-consistency | haiku | 3/3 | 0 | 0/3 |
| absolute-consistency | sonnet | 2/3 | 3 | 2/3 |

## Key findings (frozen, unadapted)

1. **Dominant EMITTED failure family: `speculative-consequence`**
   (46 haiku / 68 sonnet human-coded false blockers), followed by
   the `unclassified` mass (64/86, decomposed below), then
   `severity-inflation` (20/43), `hallucinated-fact` (26/24), and
   `risk-boilerplate` (15/20). The fixture-family table above
   (risk-boilerplate 41/46) measures the discrimination AXIS being
   tested, not the failure actually emitted — the two are distinct
   measurements (see `derived-metrics.json` +
   `narrative-coding.jsonl`). **Diagnostic only: no final T1.3
   dominant-family target is named from this run — the emitted-failure
   table is contaminated by the oracle-validity defects above and by
   the corpus-artifact/matcher-gap mass; recompute after repair +
   remeasurement.**
2. **The `unclassified` mass decomposes into corpus artifacts, not
   reviewer failures**: 95 fragment/placeholder artifacts (symbols
   defined in the real module but absent from the self-contained
   fixture fragment — C12/M12 CONFIG_URL/OriginError, C16/M16
   LABELS, M7 imports; plus the placeholder-SHA class) and 55
   matcher-vocabulary gaps (narratives that DO state the intended
   defect — M9/M10/M12/M16/M6 — outside the frozen needles).
   Recorded as eval/corpus observations for human triage; they are
   NOT T1.3 targets.
3. **Grounding basis is not the failure mode**: most false blockers
   carry `cited-evidence` (93/110) or `inferred` (63/111) bases;
   pure `asserted` recitals are minority (15/20). The reviewer
   engages the diff — it grounds speculative and inflated claims.
4. **Profile asymmetry, not monotonic improvement**: sonnet detects
   M9/M17/M18 at 5/5 where haiku scores 0 — but loses M4/M10/M13/M6
   to 0 where haiku reaches 1–2. The probe's "stronger model made
   it worse" refines to "stronger model shifts the failure surface."
5. **GATING marginality (haiku)**: C4 and C7 violated zero-tolerance
   with exactly 1 false blocker each (4/5 CLEAR). Sonnet: clean.
   Recorded as measured evidence; **no state change** in this stage.
   The prior N=3 pass was not stable at N=5.
6. **Fail-closed parser robustness finding (M9/C9, haiku)**: 9/10
   runs INCONCLUSIVE. Root cause preserved in raw outputs: the model
   produces structurally invalid JSON on quoting-heavy bash content
   (the finding comment embeds jq/bash quoting and the JSON string is
   never terminated). The detection narrative is PRESENT in the raw
   output (5/5 for M9) but never survives parsing — fail-closed is
   correct behavior (malformed output must never become Clear), and
   this is reviewer robustness evidence directly relevant to T1.3's
   mechanism menu (output-format robustness), not a corpus defect.
7. **Absolute-consistency is nearly inverted across profiles**:
   haiku clean-controls/zero-detection vs sonnet 2/3+2/3 detection
   with 3 false blockers — the M5/C5 axis remains the sharp target.

## Derived artifacts (no model calls)

- `narrative-coding.jsonl` — every normalized BLOCKING finding across
  both profiles (584: 172 expected-defect, 412 false blockers),
  human-coded with class, family (or `unclassified`), grounding
  basis (`cited-evidence` / `inferred` / `asserted`), rationale,
  and a deterministic pointer into the frozen reports.
- `derived-metrics.json` — false-blocker aggregation by coded
  family × profile and basis × family × profile; `unclassified`
  decomposition; false-clear metrics per positive × profile.
- False-clear definition (plan rev 5): a defect-containing run
  whose normalized assessment is `CLEAR` **or** `INCONCLUSIVE`.
  False-clear counts (/5): M5 5·5, M15/M17/M18 5·0 (haiku·sonnet),
  M9 5·0, M4 0·5, M6 0·5 — the asymmetry signature again.

## Corpus-validity observations (recorded, NOT adapted)

Per the directing instruction, observations that might indicate
corpus rather than reviewer issues are recorded here for human
triage, with no changes made in this stage:

- **Fragment artifacts (95 coded FBs)**: self-contained fixture
  fragments reference symbols defined in the real module
  (C12/M12 `CONFIG_URL`/`OriginError`/`parse`, C16/M16 `LABELS`,
  M7 imports) — the reviewer correctly reads the visible fragment.
  Also the placeholder-SHA class (C1/C2 baseline fixtures).
- **Matcher-vocabulary gaps (55 coded FBs)**: narratives that state
  the intended defect in vocabulary outside the frozen needles
  (M9 message-vs-branch phrasing, M10 'matches anywhere' without
  'search', M12 docstring-violation without 'parse', M16
  fabricated-success without the needles, M6). Semantically
  detections; mechanically false blockers. Matcher needles are
  oracle semantics — any change is a T1.4+ decision, not this
  stage's.
- C12/M12 attracted the highest false-block counts in the corpus —
  the async/`ParseError` fixture may be unusually provocative; keep
  under observation in T1.3 iterations.
- M9/C9 quoting density correlates with malformed output on haiku
  (see finding 6); classified as reviewer behavior, flagged here
  because the fixture design amplifies it.

## Reproduction

```bash
export OPENROUTER_API_KEY=...   # caller's key; never stored here
python3 eval/run_corpus.py --model anthropic/claude-haiku-4.5  --n 5 \
  --out eval/evidence/track1-baseline-2026-09-05/haiku-n5.json
python3 eval/run_corpus.py --model anthropic/claude-sonnet-4.5 --n 5 \
  --out eval/evidence/track1-baseline-2026-09-05/sonnet-n5.json
```

Same checkout as subject (`46b9547`); oracle from the same tree.
Spend at this scale is pre-authorized by plan rev 5; retries beyond
the 400-attempt envelope require asking first (none occurred).
