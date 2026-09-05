# Track 1 measured discrimination baseline (T1.2) — 2026-09-05

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

1. **Dominant failure family: `risk-boilerplate`** on both profiles
   (41/46 false blockers across C1/C2/C13/C14; M13 detection weak).
   `hallucinated-fact` second (0/4 controls clean both profiles).
2. **Profile asymmetry, not monotonic improvement**: sonnet detects
   M9/M17/M18 at 5/5 where haiku scores 0 — but loses M4/M10/M13/M6
   to 0 where haiku reaches 1–2. The probe's "stronger model made it
   worse" refines to "stronger model shifts the failure surface."
3. **GATING marginality (haiku)**: C4 and C7 violated zero-tolerance
   with exactly 1 false blocker each (4/5 CLEAR). Sonnet: clean.
   Recorded as measured evidence; **no state change** in this stage.
   The pass at the 2026-08-30 N=3 baseline reads as sample luck; the
   T1.3 non-regression gate applies to zero-false-blockers on ALL
   controls, which subsumes this.
4. **Fail-closed parser robustness finding (M9/C9, haiku)**: 9/10
   runs INCONCLUSIVE. Root cause preserved in raw outputs: the model
   produces structurally invalid JSON on quoting-heavy bash content
   (the finding comment embeds jq/bash quoting and the JSON string is
   never terminated). The detection narrative is PRESENT in the raw
   output (5/5 for M9) but never survives parsing — fail-closed is
   correct behavior (malformed output must never become Clear), and
   this is reviewer robustness evidence directly relevant to T1.3's
   mechanism menu (output-format robustness), not a corpus defect.
5. **Absolute-consistency is nearly inverted across profiles**:
   haiku clean-controls/zero-detection vs sonnet 2/3+2/3 detection
   with 3 false blockers — the M5/C5 axis remains the sharp target.

## Corpus-validity observations (recorded, NOT adapted)

Per the directing instruction, observations that might indicate
corpus rather than reviewer issues are recorded here for human
triage, with no changes made in this stage:

- C12/M12 attracted the highest false-block counts in the corpus
  (21 haiku / high sonnet) — the async/`ParseError` fixture may be
  unusually provocative; keep under observation in T1.3 iterations.
- M9/C9 quoting density correlates with malformed output on haiku
  (see finding 4); classified as reviewer behavior, flagged here
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
