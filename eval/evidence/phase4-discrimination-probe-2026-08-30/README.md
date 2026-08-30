# Phase 4 discrimination probe (2026-08-30)

Question: can M5 (same-diff consistency) pass pair integrity via a
rubric amendment at the current model profile?

Five full-corpus **experimental evaluation runs** (discrimination
probe), N=5 each — NOT qualification runs: runs 03/04 tested
uncommitted working-tree rubric variants. Qualification, under the
Phase-3 contract, means a merged trusted subject SHA against the
current oracle; experimental evaluation is exploratory and carries
no authorization meaning. Oracle
`a34a938a0ba350af` (identical across all runs — harness, corpus, and
GATING states unchanged throughout):

| # | subject | model | M5 | C5 (pair) | C7 | GATING verdict |
|---|---------|-------|----|-----------|----|----------------|
| 01 | rubric @ `85705d5` (pre-rule) | haiku-4.5 | 0/5 | clean | clean | green |
| 02 | r1: + consistency rule (PR #16) | haiku-4.5 | **5/5, 0 noise** | blocked 5/5 | 8 blockers | **red** |
| 03 | r2: + categorical exemption | haiku-4.5 | 5/5 | blocked 5/5 | clean | **red** |
| 04 | r3: + falsification-by-case | haiku-4.5 | 3/5 | blocked 5/5 | clean | **red** |
| 05 | r1 (same as 02) | sonnet-4.5 | 5/5 | 6 blockers | 4 blockers | **red** |

Rubric fingerprints per run are in each report's
`profile.rubric_hash`. The r1 text lives in git history (commit
`3b783c8`, PR #16). The uncommitted r2/r3 formulations are preserved
alongside (byte-exact, verified against the recorded hashes):

- `rubric-r2-categorical-exemption.md` — sha256[:16]
  `b68b5051d6d3c260` = run 03's `profile.rubric_hash`
- `rubric-r3-falsification-by-case.md` — sha256[:16]
  `b62861aa004b60be` = run 04's `profile.rubric_hash`

## Conclusion

**M5 detection was successfully induced, but every tested
implementation failed pair integrity because C5 was consistently
false-blocked.** Three rubric formulations and two models failed to
separate M5 from C5; the stronger model increased broader false
positives (run 05: C1 13 blockers, C2 15, M7 10 — versus 10/7/3 in
run 01). Therefore this is evidence of a **discrimination/grounding
ceiling, not a wording or model-selection problem**.

The blocking narratives shifted across formulations (readability
objection → subset/superset hyper-literalism) while the blocking
verdict never changed — wording steers which excuse the model gives,
not whether it blocks.

Secondary findings recorded for Track 1:

- rubric edits have global effects — run 02's collateral regression
  on C7 (0 → 8 blockers) was rule-induced, fixed only by a separate
  speculation guard (runs 03/04);
- pair integrity and the GATING ratchet stopped every failing
  variant before promotion — the machinery worked exactly as
  designed;
- a recurring false-block class in the reports: immutable full-SHA
  pinning flagged as a blocking security defect with floating
  version refs recommended as the "fix" — prime Track-1 material
  (controls C1/C2).

## Consequences

- `rubric.md` restored to the pre-#16 text (this PR); M5 remains
  `KNOWN_GAP`.
- Phase 4 → **BLOCKED** by a newly measured discrimination
  prerequisite (plan Deviation 2).
- Track 1 (discrimination / false-blocker reduction) resequenced
  ahead of the M5 retry as the next active capability stage
  (ROADMAP). It must address the broader measured false-blocker
  problem rather than special-case C5; **M5/C5 is its first sharp
  target**, with this bundle as baseline evidence.

Spend: 400 model calls (5 × 80), all against the directing human's
OpenRouter key, authorized for this qualification sequence.

This bundle is evidence only — not an oracle input (pinned by
`test_oracle_input_set_is_exactly_harness_fixtures_states`).
