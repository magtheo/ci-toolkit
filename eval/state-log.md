# Fixture state recordings

Append-only record of classification decisions. Every entry cites the
report it was measured from. The harness never writes this file.

## 2026-08-30 — baseline (eval/baseline-2026-08-30.json)

corpus 3dbfbfcf8c0ffc33 · rubric 415d8a38cfed9d3a · haiku-4.5 · N=3 ·
48 calls (65079 prompt / 21183 completion tokens)

- **C4, C5, C7 → GATING**: measured 3/3 CLEAR, zero false blockers,
  minimal noise. Capability "no false blockers on clean self-scoped
  docs / retained-bounds code" is real today and becomes permanently
  protected.
- **M8 stays KNOWN_GAP despite passing 3/3**: pair integrity — its
  control C8 measured 3/3 ISSUES_FOUND on clean code. The detection
  is indistinguishable from over-triggering in the same topic area;
  a positive is only promotable while its control passes. (Recorded
  as the operative reading of the ratchet; to be written into the
  plan's permanent rules at next plan touch.)
- **C1, C2, C3, C6, C8 → KNOWN_GAP**: false blockers on every run
  (3–6 per fixture across N=3). The reviewer over-triggers on clean
  security-adjacent configuration — the dominant measured weakness.
- **M1, M2, M3, M7 → KNOWN_GAP**: intended defects detected 3/3, but
  contaminated by unexpected additional blockers (1–3). Detection
  exists; discrimination does not.
- **M4, M5, M6 → KNOWN_GAP**: 0/3 detection — the three documented
  miss classes reproduce synthetically. Owners: M4 → Stage 3; M5 →
  phases 4–5; M6 → future rule (not yet planned).

## 2026-09-04 — Track 1 T1.1 corpus growth (oracle change, not a measurement)

corpus 92683f53fb1f7e30 · 36 fixtures (16 baseline + 20 new) · no run

- T1.1 (plan rev 5): failure taxonomy frozen at
  `eval/evidence/track1-taxonomy-2026-09-04.md`; five families
  declared in `eval/run_corpus.py::FAMILIES`; existing pairs tagged
  where classification is solid; 20 new adversarial fixtures
  (M9-M18/C9-C18, >=2 new pairs per family).
- New fixture states are INITIALIZED to KNOWN_GAP — not measured
  classifications (the harness never writes states; these entries
  exist so states.json and the corpus stay in lockstep and
  `oracle_version` changes fail-closed per plan Deviation 4).
- No GATING changes; no reviewer behavior change (eval-semantics-only
  stage). T1.2 will measure the expanded corpus.

## 2026-09-05 — Track 1 T1.2 measured discrimination baseline

corpus 92683f53fb1f7e30 · subject 46b9547 (feature branch) ·
haiku-4.5 + sonnet-4.5 · N=5 each · 360 calls, 0 retries

- Bundle frozen at `eval/evidence/track1-baseline-2026-09-05/`
  (per-run raw outputs, per-fixture results, per-family aggregation,
  false-block/false-clear, paired discrimination, spend, floors).
- Sensitivity floors recorded per-positive per-profile
  (`floors.json`) — the T1.3/T1.5 non-regression reference.
- GATING violations measured (haiku: C4, C7 — 1 false blocker each,
  4/5 CLEAR; sonnet: none). **No state changes**: T1.2 is
  evidence-only; the marginality is recorded for T1.3's universal
  zero-false-blocker gate, which subsumes it.
- Fail-closed parser robustness evidence: quoting-heavy bash
  fixtures (M9/C9) induce structurally invalid JSON from haiku
  (9/10 INCONCLUSIVE; detection narrative present in raw output).
  Relevant to T1.3's mechanism menu; frozen unadapted.

## 2026-09-05 — T1.2 derived-evidence pass (no model calls)

- `narrative-coding.jsonl`: all 584 blocking findings across both
  profiles human-coded (172 expected-defect, 412 false blockers;
  family + grounding basis + rationale + report pointer).
- `derived-metrics.json`: emitted-false-blocker aggregation and
  false-clear metrics (CLEAR-or-INCONCLUSIVE on positives).
- Recomputed conclusion: dominant EMITTED family is
  speculative-consequence (46h/68s), NOT risk-boilerplate (15/20) —
  the fixture-family table measures the tested axis, not the emitted
  failure. unclassified mass (64/86) decomposes into corpus
  artifacts (95: fragment symbols, placeholder SHA) and
  matcher-vocabulary gaps (55: true detections phrased outside
  frozen needles) — recorded for human triage, not T1.3 targets.
- GATING wording corrected to the evidence-only formulation: the
  prior N=3 pass was not stable at N=5.

## 2026-09-05 — T1.2 status correction: diagnostic, not binding (oracle-validity discovery)

External review of the derived pass identified corpus/oracle
validity defects the run exposed: added-file controls that are not
genuinely self-contained (C12 CONFIG_URL/OriginError, C16 LABELS —
for added files the reviewer cannot assume omitted module context,
so those blockers are valid against the fixture input) and 55
matcher-vocabulary gaps expressing frozen expected defects outside
the frozen needles. Corrections of record:

- the 2026-09-05 360-call T1.2 run is a COMPLETED DIAGNOSTIC
  measurement, preserved immutable; it is NOT the final binding T1.2
  non-regression reference;
- T1.2 remains INCOMPLETE pending an eval-semantics-only oracle
  repair phase (audit all 95 fragment/placeholder codings; make
  controls self-contained and globally clean; keep positives
  minimal-delta on intended axes; extend matchers only where the
  narrative genuinely states the frozen expected defect;
  deterministic guards for the discovered validity classes; oracle
  bump; reviewer untouched) and a fresh unchanged-reviewer N=5
  dual-profile remeasurement — that later run is the binding floor;
- no final T1.3 dominant-family target is named from the current
  data (the emitted-failure table is contaminated by the validity
  defects).

## 2026-09-05 — Track 1 oracle repair (eval semantics only; plan Deviation 5)

corpus 92683f53fb1f7e30 -> 61380c91e84db0ef · 36 fixtures · 0 model calls

- Audited all 96 fragment/placeholder codings and all 55
  matcher-vocabulary gaps from the T1.2 diagnostic run
  (eval/evidence/track1-oracle-repair-2026-09-05/README.md).
- Repairs: C12/M12 + C16/M16 self-contained; C14/M14 env-var guards;
  C1/M1 realistic SHA + permissions + fork guard; C2/M2 realistic
  SHAs. M7 ruled valid as presented (modified-file context implied).
- Matcher extensions (monotonic, originals preserved, test-enforced):
  M9/M10/M12/M16/M2. M6 NOT extended (narratives misattribute the
  mechanism). Frozen diagnostic coding remains immutable; refined
  family judgments recorded in the repair README.
- New deterministic guards: placeholder-SHA, added-python
  self-containment, added-shell variable guards, matcher
  monotonicity.
- Human semantic audit of all 36 repaired fixtures frozen at
  fixture-audit.json BEFORE any remeasurement spend authorization.
- No GATING changes; family taxonomy unchanged; reviewer untouched.
  Binding T1.2 reference = the upcoming unchanged-reviewer N=5
  remeasurement (Deviation 5).

## 2026-09-05 — Oracle repair round 2: diff-structure validation + witness-tested matchers

corpus 61380c91e84db0ef -> 9fae85b26ff45dc6 · 0 model calls

- Embedded unified-diff validator added (oracle-hashed): hunk
  old/new counts must match bodies; canonical -0,0 added-file form;
  fail closed on malformed metadata. 19 fixtures carried stale or
  non-canonical headers (including Phase-2-era -1,0) — all
  recomputed. The patch string is reviewer input; malformed diff
  metadata was itself a corpus-validity artifact.
- Matcher validation strengthened beyond lexical union preservation:
  frozen #30 evidence frozen as a 122-witness set (69 genuine / 53
  not_expected, every gap narrative ruled explicitly). Final needles
  use semantically sufficient phrases; generic single tokens
  (search/parse/except) and M12's bare 'empty' dropped after the
  witness set showed false-acceptance. Enforced invariant: genuine
  detections stay accepted, audited genuine gaps become accepted,
  audited non-defect narratives stay rejected. Schema unchanged.
- 148 tests pass; states and family taxonomy unchanged; reviewer
  untouched.
