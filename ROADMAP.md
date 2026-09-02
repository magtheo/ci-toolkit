# ci-toolkit ROADMAP — Reviewer Capability Development

Authoritative direction for maturing the AI reviewer. Companion to
`plans/reviewer-eval-baseline.md` (measurement & qualification
machinery — Phase 1–6) and `AGENTS.md` (governance).

Last reviewed: 2026-08-30


## Philosophy

**We are not trying to "make the AI smarter" in an ad-hoc way. We are
systematically expanding demonstrated reviewer capabilities, while
deterministic machinery absorbs everything that does not require
semantic reasoning.**

The goal is NOT "catch any potential issue" — no review system can
guarantee that. The target:

> Catch a very high proportion of consequential defects inferable
> from the PR and accessible trusted context, at a very low
> false-blocker rate, with each capability's level demonstrated by
> measurement, not belief.

## The permanent development loop

Every capability advances only through this loop:

```text
measured miss
  → freeze fixture + paired control
  → baseline
  → smallest targeted implementation
  → qualification (no GATING regressions)
  → promotion to GATING only if earned (permanent)
```

Ad-hoc rubric stuffing ("check GitHub APIs", "look for races") is the
anti-pattern this roadmap exists to prevent.

## Current position (2026-08-30)

- eval-baseline plan Phases 1–3 complete (engine contract, corpus +
  measured baseline, qualification infrastructure).
- Phase 4 (M5) attempted and **rolled back**: detection was induced
  (5/5) but pair integrity failed in every formulation — C5
  false-blocked 5/5 across three rubric wordings and two models
  (`eval/evidence/phase4-discrimination-probe-2026-08-30/`).
  Phase 4 BLOCKED (plan Deviation 2); M5 remains KNOWN_GAP.
- Measured baseline: local defect detection decent; discrimination
  weak (5/8 controls false-blocked; probe: a stronger model made it
  worse); cross-file (M4) weak; state/lifecycle (M8) unproven via
  pair integrity.
- **Next active stage: Track 1 (discrimination)** — resequenced
  ahead of the M5 retry by Deviation 2.
- Deployment contract PENDING ACTIVATION (see plan Deviation 1).

## Capability tracks

| # | Capability | Evidence | State |
|---|------------|----------|-------|
| 1 | Discrimination / false-blocker reduction | baseline controls; phase-4 probe; #14 self-review FPs | **ACTIVE — next stage** (Deviation 2) |
| 2 | Same-diff consistency | M5 / miss #5 | blocked by Track 1 (probe: detection without separation) |
| 3 | Targeted trusted-base context retrieval | M4 (0/3) | identified; design needed |
| 4 | Cross-file contract reasoning | M4 (0/3), shared w/ track 3 | identified |
| 5 | State / lifecycle / concurrency reasoning | M8; publisher bug (human-caught) | identified; fixture family needed |
| 6 | External-contract reasoning | `/pulls/{n}` vs `/files` bug; M7 | identified; deterministic-first |
| 7 | Architectural invariant reasoning | states.json-not-in-oracle_version (human-caught) | identified |
| 8 | Acceptance / process truth | Phase-3/#10 circularity; #15 CLEAR-miss (both human-caught) | identified |
| — | Deterministic gate expansion (supporting track) | repeated LLM attention on machine-checkable facts | first candidate: actionlint |

Track 1 is the next active stage (resequenced ahead of the M5
retry by plan Deviation 2, after the Phase 4 probe falsified the
M5-first sequence). Track 2 (Phases 4–5) resumes under Track 1's
outcome. Tracks 3–8 start after the eval-baseline plan completes;
ordering thereafter is chosen from measured evidence, not this
table's number.

---

## 1. Discrimination / false-blocker reduction

- **Evidence:** baseline — C1/C2/C3/C6/C8 false-blocked (5/8 controls)
  while positives were detected; the reviewer's dominant failure mode
  is blocking on *looks risky* that is not *is incorrect*. Plus the
  #14 self-review false positives (appendix A): hallucinated absence,
  inverted conclusion from a true premise, and asserting a test gap
  without reading the test. Plus the phase-4 probe
  (`eval/evidence/phase4-discrimination-probe-2026-08-30/`): given a
  consistency rule, the reviewer blocked its own paired control 5/5
  under three wordings and two models — the blocking *narrative*
  changed with each wording while the blocking *verdict* never did.
- **Current state:** ACTIVE — the next capability stage (Deviation 2).
  First sharp target: M5/C5 separation. Scope guard: Track 1 must
  address the broader measured false-blocker problem (5/8 controls;
  stronger models make it worse), NOT special-case C5 — C5 passing
  while C1/C2/C3/C6/C8 still fail would be benchmark gaming, not
  capability. `promotion_eligible_positives` is diagnostic only.
- **Candidate mechanism:** a discrimination requirement on every
  blocking finding — state the invariant violated, the concrete
  failing execution path, and the diff/context evidence; anything
  that cannot be argued concretely is downgraded to advisory. Possibly
  a dedicated pass, but only if measurement shows the single-pass
  form insufficient (a layer must earn its existence — no big-bang
  pipeline redesign).
- **Acceptance criteria:** near-miss control fixtures reviewed without
  blockers while their paired defects are still caught, on an
  expanded control set.
- **Promotion criteria:** zero control false-blocks across the full
  corpus over qualification runs, with no detection regressions.

## 2. Same-diff consistency (M5)

- **Evidence:** miss #5 — PR body contradicting the diff itself,
  praised by the reviewer.
- **Current state:** fixture M5 frozen (KNOWN_GAP); eval-baseline
  Phase 4 (rule + implementation) and Phase 5 (promotion) are the
  first concrete capability stage and promotion stage.
- **Candidate mechanism:** rubric rule requiring claims in the
  description to be checked against the diff; output contract carries
  contradiction findings.
- **Acceptance criteria / Promotion criteria:** per
  `plans/reviewer-eval-baseline.md` Phases 4–5 (N=3 ≥2/3, then N=5
  ≥4/5 + controls clean + zero GATING regressions).

## 3. Targeted trusted-base context retrieval

- **Evidence:** M4 — a claim whose truth depends on code outside the
  diff; 0/3 detected.
- **Current state:** identified (student-platform plan already points
  at deeper context); no implementation design yet.
- **Candidate mechanism:** diff → identify unresolved
  claims/references → retrieve only the relevant BASE paths/symbols
  (trusted = merge-base, never PR head) → review diff + retrieved
  context. Targeted retrieval, not whole-repo dumps (prompt budget is
  a real constraint).
- **Acceptance criteria:** M4-class fixtures ≥2/3 detected with no
  increase in control false-blocks.
- **Promotion criteria:** standard loop, qualification N=5.

## 4. Cross-file contract reasoning

- **Evidence:** M4 / miss #4 — a cross-file contract claim ("no
  other signal") whose truth lives in code outside the visible diff;
  0/3 detected. Shares M4 with track 3 by design: track 3 is
  *acquiring* the necessary trusted context; track 4 is *reasoning
  correctly* over it.
- **Current state:** partially covered by local reasoning when the
  consumer is in the diff; weak otherwise.
- **Candidate mechanism:** builds on track 3 retrieval — check
  comments/docs/PR-body invariants against the actual implementations
  and call sites.
- **Acceptance criteria:** fixture family where the defect is a
  contract mismatch between files, ≥2/3 with controls clean.
- **Promotion criteria:** standard loop.

## 5. State / lifecycle / concurrency reasoning

- **Evidence:** M8 — the intended resume-lifecycle defect WAS
  detected 3/3, but the capability is unproven: paired control C8
  false-blocked 3/3, so pair integrity correctly withheld promotion
  (the baseline's canonical discrimination lesson). Plus the original
  qualification-publisher branch-switch/untracked-record collision
  (human-caught). NB: the later claim that overwriting the tracked
  record inside the dedicated worktree was itself a bug is a reviewer
  false positive — Appendix A, item 3.
- **Current state:** fixture exists (M8); no capability stage.
- **Candidate mechanism:** teach explicit transition questions —
  what state exists before/after; can execution exit midway; what
  happens on retry / second execution (idempotency); can events
  arrive out of order; is state consumed before its prerequisite
  exists. Backed by a dedicated fixture family for ordering, retries,
  partial state, and races.
- **Acceptance criteria:** the fixture family ≥2/3 with paired clean
  orderings not blocked.
- **Promotion criteria:** standard loop.

## 6. External-contract reasoning

- **Evidence:** the dogfood verify-pin bug — `GET /pulls/{n}` queried
  for `.files[]` (wrong endpoint; empty result silently swallowed) —
  human-caught; M7 (curl/HTTP semantics).
- **Current state:** not systematically planned.
- **Candidate mechanism:** deterministic-first: wherever an exact
  validator can prove correctness (actionlint, schema validators,
  API-shape checks), it belongs BELOW the AI layer; the AI reasons
  only where no exact validator exists, and should flag
  externally-dependent assumptions explicitly.
- **Acceptance criteria:** fixture family of wrong-endpoint /
  wrong-semantic-argument defects with clean paired usage; ≥2/3 with
  controls clean.
- **Promotion criteria:** standard loop.

## 7. Architectural invariant reasoning

- **Evidence:** `oracle_version` not hashing `states.json` — identity
  must change whenever evaluation semantics change; the reviewer had
  to understand the architecture, not the line. Human-caught.
- **Current state:** not planned.
- **Candidate mechanism:** a compact, trusted, project-level
  invariant list supplied as review context (e.g. "oracle identity
  changes whenever evaluation semantics or GATING state changes") —
  a few lines, not prose dumps; the reviewer verifies implementations
  against named invariants and traces contributors.
- **Acceptance criteria:** fixture family where defects violate a
  stated invariant non-locally; ≥2/3 with controls clean.
- **Promotion criteria:** standard loop.

## 8. Acceptance / process truth

- **Evidence:** the Phase-3/#10 completion circularity (a process-state
  contradiction, not a code bug); the #15 CLEAR-miss — the AI reviewer
  passed a governance doc that described a not-yet-active control
  (`verify-pin` on `main`) as already in force (human-caught);
  methodology rule 5 (PR bodies must match contents) already exists
  but is enforced by humans.
- **Current state:** rule exists; no enforcement capability.
- **Candidate mechanism:** consistency pass over PR description, plan
  status, acceptance criteria, and dependency state — can the declared
  lifecycle actually be satisfied?
- **Acceptance criteria:** fixtures containing body/plan/impl
  contradictions caught; coherent ones not blocked.
- **Promotion criteria:** standard loop.

---

## Deterministic gate expansion (permanent supporting track)

Tests, type checking, linters, schema validators, `actionlint`, and
other exact project-specific checks.

**Principle: never spend LLM reasoning on something a deterministic
tool can prove cheaply and exactly.**

First candidate: `actionlint` on all workflows (pinned supply chain,
CI-only surface). Lands only as a tiny independent change that does
not derail the phase sequence — existing workflow patterns must be
verified clean (or explicitly waived) first.

---

## Appendix A — evidence: #14 self-review false positives (2026-08-30)

Preserved per directive; to be classified against existing miss
classes BEFORE any are frozen as fixtures.

1. **Hallucinated absence:** claimed `hashlib` was never imported
   while it was (line 32), contradicted by a passing test on the same
   head that executes the import path.
   → classification candidate: *grounding* subtype of discrimination —
   asserting a checkable falsehood about in-context evidence. Distinct
   from C-class pattern-suspicion (blocking on risky-looking clean
   code); likely a genuinely new subtype.
2. **Inverted conclusion:** correctly described argparse
   append+default behavior, then concluded enforcement was broken in
   the opposite direction of the actual (minor) wart, which was fixed.
   → classification candidate: *reasoning calibration* — true premise,
   wrong verdict. Same family as "distinguish bad from merely
   suspicious" (existing discrimination class).
3. **Phantom coverage gap:** claimed the E2E test missed the
   requalification case without reading the test that runs exactly
   that case twice.
   → classification candidate: *grounding* subtype — asserting
   absence of coverage without verifying. Same subtype as (1).

Working classification: 2/3 are assertion-without-verification
(grounding); 1/3 is conclusion calibration. Both fold into capability
1, but the grounding subtype may warrant its own fixture family —
decide when capability 1 work starts, with fresh measurement.

Additional evidence (2026-08-31, ci-local-runners reviews — the
external reviewer caught all three; ai-review was inoperative on
the affected repos):

4. **Runtime-dependency reasoning:** a lane image shipped without
   python3 while the pinned reviewer executes python — nothing asked
   "can the workload actually run here?" until a smoke job existed.
   Classification candidate: external-contract/runtime (tracks 5/6
   adjacent).
5. **Test self-defeat:** the acceptance script verifying "no token
   in argv" passed the live token to `grep`, placing it in a
   world-readable argv during its own scan. Classification
   candidate: reasoning about one's own mechanism (track 5 subtype).
6. **Infrastructure trust reasoning:** `config.sh --token`
   forwarding into world-readable `/proc/*/cmdline` on a shared
   host — required crossing the container/host boundary with an
   adversary model. Classification candidate: architectural
   invariant (track 7).

Side observation: while ai-review was inoperative (billing, then
the pin-fetchability investigation), the external human reviewer
carried the entire semantic review layer — consistent with the Review Model ordering
(deterministic gates → AI evidence → human judgment), and a live
reminder that the AI layer is evidence, not authority.

7. **Premise acceptance against own-infrastructure evidence:** the
   AI reviewer CLEAR'd the pin-governance docs and praised the
   "dead pin" diagnosis — while the reviewer's own successful run
   that same day (ci-toolkit 33377170635) had checked out that
   exact SHA. Classification candidate: grounding/evidence-integrity
   (track 1 subtype — a checkable contradiction with the system's
   own observable record). The diagnosis itself was also
   overgeneralized by the implementing agent; corrected in #20.

8. **Praising nonfunctional code:** on PR #22 the AI reviewer
   explicitly praised the credential-cleanup trap as reliable while
   a second EXIT trap silently disabled it (bash traps replace, not
   append) — functionality contradicted by reading the rest of the
   same file. Classification candidate: grounding (asserting a
   behavior checkable in-context), same subtype as (1)/(3).

