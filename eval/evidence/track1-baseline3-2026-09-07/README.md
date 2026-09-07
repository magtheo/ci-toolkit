# Track 1 baseline 3 — completed diagnostic T1.2 remeasurement (2026-09-07)

## STATUS: DIAGNOSTIC — NOT BINDING. T1.2 REMAINS INCOMPLETE.

- GATING control **C7 violated policy on both governed profiles, by two
  distinct mechanisms**:
  - **haiku — assessment/protocol-conformance violation**: zero blocking
    findings on C7, but 1/5 runs was refused by the deterministic
    normalizer as **"ISSUES_FOUND label with no validated blocking
    finding"** — the response parsed cleanly and carried 2 advisory-grade
    findings, but the fail-closed rule (`parse_review.assess`, untrusted
    label without blocking evidence → INCONCLUSIVE) broke the control's
    every-run-CLEAR requirement. Provisional classification:
    **labeling-protocol failure, NOT a discrimination false blocker**
    (the model's advisory instinct on a globally-clean diff was arguably
    right; the ISSUES_FOUND label was the protocol violation) — pending
    human confirmation. Normalizer causes for all 11 corpus-wide
    INCONCLUSIVE runs reproduced deterministically in
    `inconclusive-audit.json`: **10× JSON decode failure** (8× unescaped
    double quotes inside quoted shell snippets; 2× a second JSON object
    emitted after post-answer reconsideration), **1× the C7
    label-evidence mismatch above**. Markdown fencing is an observed
    surface property of these responses, NOT a causal factor —
    `parse_model_output` extracts the `{...}` span and accepts fenced
    objects.
  - **sonnet — blocking-finding violation**: 6 blocking findings on C7.
    All six individually human-coded against the presented ReviewInput in
    `c7-sonnet-adjudication.json`: **0/6 valid defects, 6/6 false
    blockers** (5 speculative-consequence, 1 severity-inflation; every
    one rests on counterfactual code outside the diff or a disputed
    design preference).
- **No sensitivity value from this run may be activated as a T1.3/T1.5
  floor. No T1.3 discrimination family has been selected. No further
  model spend is authorized.**
- Pair-integrity violations: haiku 6 (M1/M2/M3/M8/M10/M11 controls
  fail), sonnet 2 (M2, M8).

## Frozen run identity

| field | value |
|---|---|
| subject | `4b07246a114a9130b6ef3d6a67cd09a01faacace` (reviewer semantics unchanged; verified 0-diff on engine/render/parse/rubric vs subject) |
| oracle | `8c34a74047ad0144` (frozen pre-run at the phase boundary; recomputed identical post-run) |
| corpus | 36 fixtures (18 positive / 18 control) |
| N | 5 per fixture per profile |
| profiles | `anthropic/claude-haiku-4.5`, `anthropic/claude-sonnet-4.5` |
| generation | temperature 0.2, max_tokens 2000 |
| logical calls | 360 (180 per profile) |
| network failures / retries | 0 / 0 |
| generated (per profile) | see `*-n5.json` `profile.generated` (sonnet 2026-09-07T08:34:03.495974+00:00, haiku 2026-09-07T08:49:27.916906+00:00) |
| spend | sonnet 243,615 prompt / 76,424 completion tok; haiku 243,615 / 81,034; weekly-window spend at run end ≈ $2.51 (includes one $0.0004 deepseek smoke call, see state-log) |

Pre-run attempt record: the first launch on 2026-09-06 aborted on every
call with OpenRouter 403 (weekly key limit); 0 successful calls, no
spend — `attempt1-keylimit.*.stderr.log` (preserved byte-untouched).

## Diagnostic headline values (NOT floors)

| | haiku | sonnet |
|---|---|---|
| expected-finding detection hits | 51/90 | 66/90 |
| false-clears (CLEAR or INCONCLUSIVE with defect present) | 29 (0.322) | 15 (0.167) |
| control false blockers | 90 | 135 |
| …of which on GATING controls | 0 | 6 (all C7) |
| INCONCLUSIVE runs | 9 (8 JSON decode failures + 1 label-evidence mismatch) | 2 (2 JSON decode failures) |

Corpus-wide: 11 protocol failures = 10 JSON decode failures (8
unescaped-inner-quotes, 2 second-object-after-reconsideration) + 1
ISSUES_FOUND-without-blocking (the haiku C7 run); per-run reproduced
causes in `inconclusive-audit.json`.

## Emitted-family aggregation (324 false blockers, all human-coded)

| family | haiku | sonnet | total |
|---|---|---|---|
| speculative-consequence | 63 | 52 | 115 |
| hallucinated-fact | 20 | 50 | 70 |
| risk-boilerplate | 18 | 52 | 70 |
| severity-inflation | 16 | 39 | 55 |
| absolute-consistency | 6 | 8 | 14 |

Grounding: asserted 183, cited-evidence 75, inferred 66.
Full per-finding coding: `narrative-coding.jsonl` — **538 total entries
= 211 expected-expression + 324 false blockers + 3
defect-expression-unmatched** (invariant checked mechanically in
`derived-metrics.json: narrative_coding_summary`).

## Post-run oracle-validity audit (`oracle-validity-audit.json`)

Miss decomposition (63 non-detecting positive runs):
haiku — 4 protocol (JSON decode failures, all M9) + 35 reviewer-miss;
sonnet — 24 reviewer-miss.

**Three confirmed matcher-gap candidates (defect-expressing narratives
the frozen needles miss) — RECORDED, NOT REPAIRED in this PR:**
1. M12 masking phrasing family "serves stale without distinguishing the
   failure mode" (sonnet r2f2)
2. M16 third phrasing family "indistinguishable from a successful PUT /
   caller has no way to know" (haiku r4f1)
3. M3 parsed-date phrasing without the all-of needle `mtime` (sonnet
   r3f1)

The haiku M16 r2f2 response-shape finding ("Response vs dict
inconsistency") is **not** a gap: that semantic angle is a frozen
negative witness from Oracle repair 3 (#35) and remains a false blocker
(severity-inflation); frozen rulings are not reversed by later runs.

No control fixture was found to contain a genuine defect (no
fixture-validity escape). Any repair follows the witness-tested oracle
repair procedure as its own PR.

## Files (raw outputs byte-untouched)

- `haiku-n5.json`, `sonnet-n5.json` — raw harness reports
- `haiku.stdout.log`, `haiku.stderr.log`, `sonnet.stdout.log`,
  `sonnet.stderr.log` — run transport logs
- `derived-metrics.json` — all machine-derived aggregates
- `narrative-coding.jsonl` — per-finding human/regex-pre-pass coding
- `inconclusive-audit.json` — 11 protocol failures with reproduced
  normalizer causes: 2 cause categories (JSON decode failure; label /
  schema fail-closed rule), `surface_format` recorded as non-causal
  observation
- `c7-sonnet-adjudication.json` — the six sonnet C7 blockers, individually
  adjudicated
- `oracle-validity-audit.json` — miss decomposition + matcher gaps
