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

corpus ad212335a1c37d6e · 36 fixtures (16 baseline + 20 new) · no run

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
