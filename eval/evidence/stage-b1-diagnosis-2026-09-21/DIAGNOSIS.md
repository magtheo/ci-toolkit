# Stage B1 diagnosis — zero-call analysis of the frozen campaign records

Subject: B1 FAIL (PR #83 evidence, executed at merge `7412723`,
oracle `5472d990f3b946c3`, rubric `f13db500…`). 90/90 reviews, 0
transport failures, 0 INCONCLUSIVE, 0 escalations, 0 halts. Every
classification below was made against the frozen oracle
(`eval/fixtures/*.json`, `eval/run_corpus.py` matchers) and the frozen
revised rubric (`f13db500…`). No provider calls; no evidence modified.

---

## A. Control blocking findings — full reconciliation (19 findings)

Cause distribution: **17 MODEL_RULE_VIOLATION · 2 RUBRIC_AMBIGUITY ·
0 RUBRIC_LICENSED · 0 VALID_BLOCKER** (+2 flagged for human
adjudication inside the RUBRIC_AMBIGUITY pair).

### C3 — roadmap freshness guard (7 findings: low 5, high 2) — all MODEL_RULE_VIOLATION

Every finding observes something TRUE in the diff (no non-zero exit;
missing ROADMAP.md silently skipped) and promotes it to blocking. The
fixture's documented contract is the header comment — "flags
repositories whose ROADMAP file has not been modified in the last 30
days (rolling window on file mtime)" — and the code does exactly that
(this is the fixture's whole point; it is the pair-control for M3,
whose docs say PARSED DATE while the code does mtime).

- The models invented a deployment context ("Wired into CI, a STALE
  result would not fail the build" — low run1; "a guard whose STALE
  verdict does not affect exit status will pass any CI gate" — low
  run2): nothing in the diff claims CI wiring or exit-code semantics.
- Unclaimed design space (exit codes, missing-file handling) was
  treated as broken behavior, then licensed to blocking through the
  scope-mismatch rule's "shipped behavior is itself harmful" clause
  ("a repo can delete its roadmap to permanently go green" — high
  run0).

**Answer to the posed question:** the model is treating a guard-design
weakness as actual broken behavior; the fixture does NOT violate its
frozen oracle.

### C12 — last-good config fallback (6 findings: low 3, high 3)

- **KeyError findings (low run0, high run0, high run2) —
  MODEL_RULE_VIOLATION.** The docstring explicitly says "An empty
  cache raises — a fresh origin error must not be silently masked",
  and the frozen oracle note adjudicates precisely this: "empty cache
  surfaces KeyError rather than masking the failure." The findings
  assert invented intent ("the KeyError is accidental", "wrong
  exception type") and imagined caller expectations (unseen callers
  catching OriginError) — facts about code absent from the diff.
- **Session speculation (high run1) — MODEL_RULE_VIOLATION.** "It
  does NOT catch other exception types like network errors or
  timeouts, which are common failure modes for HTTP requests... Any
  real origin outage... will propagate as whatever exception the
  session library raises" — asserts the behavior of the injected
  `session`, which is the demonstrability rule's named example of
  unseen code ("an injected client"). The model also claims
  "OriginError is defined here but never raised anywhere in the
  diff" — true, and irrelevant: the diff also defines no caller; the
  raise sites are outside the diff by construction.
- **ParseError findings (low run1, low run2) — RUBRIC_AMBIGUITY.**
  These are fully in-diff and factually accurate: `_decode` raises
  `ParseError`, only `OriginError` is caught, so a malformed payload
  propagates instead of serving last-good. The ambiguity is real:
  `ParseError` is defined in-file as an origin-failure variant
  ("Origin returned a malformed config payload"), so "on origin
  failure serve the last-good cached config" is either contradicted
  (blocking) or satisfied-for-transport-failures-as-designed
  (advisory). Under claims-rule mode (ii) the line between "broken"
  and "functional though different" is a judgment call, and the
  models chose blocking.
  **FLAG (human adjudication recommended, C11 precedent):** the
  frozen oracle note does not explicitly rule on the ParseError
  reading. If you adjudicate that the docstring's "on origin failure"
  includes malformed payloads, C12's CLEAR is an oracle defect and
  the two findings are VALID_BLOCKER against a mis-set oracle. If you
  adjudicate the contract as transport-failure-scoped, the findings
  stay RUBRIC_AMBIGUITY severity overreach. Either way this is an
  oracle adjudication, not a model-behavior question — and it changes
  nothing about B1 (both readings leave the other 17 findings
  classified as above; B1's FAIL does not rest on C12 alone).

### C13 — publish workflow (6 findings, all runs both efforts) — all MODEL_RULE_VIOLATION

All six runs blocked on the title/trigger mismatch, despite the
preregistered human adjudication (C13 CLEAR; the revised rubric's own
mode-(ii) example: functional-but-different stays advisory).

**The exact alternate rubric language that still licensed blocking:**

1. Scope-mismatch rule: "blocking only when the shipped behavior is
   itself harmful" — the models classified "images published from
   unmerged PR heads with REGISTRY_TOKEN" as the shipped harm.
2. Claims rule (ii): "block when the behavior is broken or unsafe."
3. External-facts rule: "If the fact makes the code incorrect as
   written, the finding may be blocking" — the models cited the TRUE
   `pull_request_target` lifecycle fact, then chained it to an
   ASSUMED fact ("publishes PR-head code") that is wrong by default
   (`pull_request_target` checks out the base ref; head checkout
   would be a choice made inside the called workflow — which is
   pinned by full SHA in this fixture and is outside the diff).
4. The Security priority ("permission widening, destructive
   operations without guards") pulls severity up.

The demonstrability rule names this exact case ("a called workflow")
and should have severed the chain; where runs acknowledged the
dependency they hedged-then-blocked ("If the called reusable workflow
checks out the PR head ref (common for pull_request_target patterns),
unreviewed code runs with registry write credentials" — low run0).
Primary classification is therefore MODEL_RULE_VIOLATION (demonstrability
ignored, external fact misapplied); secondary RUBRIC_AMBIGUITY note:
the "harmful/unsafe" escape hatches in (1) and (2) carry no explicit
requirement that the harm itself be demonstrable from the diff.

---

## B. Low-effort M3/M16 regressions (vs Stage-A baseline 3/3)

- **M3 low (2/3): run1 severity downgrade.** Run1 SAW the mtime-vs-
  parsed-date contradiction (correct file, line, and substance — its
  text would match the oracle if severity were blocking) and rated it
  non-blocking, reasoning "The mtime-based behavior is functional…"
  in its summary. Stage-A runs (old rubric) blocked it 3/3. This is
  **materially related to the changed rubric**: the revised claims
  rule's mode-(ii) advisory branch ("keep it advisory when the shipped
  behavior is functional though different from what the claim
  promises") supplied the downgrade path. The miss is real per oracle
  (the fixture's documented example — reviewed yesterday, dated last
  month — is exactly the case mtime defeats), so "functional though
  different" is a misreading of mode (ii), not variance.
  Classification: RUBRIC_AMBIGUITY-licensed severity downgrade.
  Not perception; not phrasing; not ordinary variance (2/3 runs still
  block).
- **M16 low (2/3): run1 oracle-matcher phrasing miss, equivalent
  semantic detection.** Run1 produced the CORRECT blocking finding
  ("bare `except Exception: pass` discards every failure… falls
  through to return {\"ok\": True…") but its vocabulary ("discards",
  "falls through to return") contains none of alternative 1's needles
  ("swallow/silently/ignor/fabricat/mask/returns {"), and alternative
  2's comment_any needles also miss. Stage-A runs happened to use
  "swallows". Classification: matcher phrasing sensitivity —
  plausibly ordinary vocabulary variance interacting with a sparse
  needle list. NOT a rubric defect; NOT a perception or severity
  change (the finding was blocking in all three B1 runs).

## C. M4 — the revised claims rule DID buy the capability (measured 2/3 undercounts it)

All six runs (3 low + 3 high) produced a blocking finding with the
same reasoning path, in the rule's own vocabulary: "absolute guarantee
about code outside the diff (the orchestrator) … nothing in the
supplied evidence establishes it … central to the PR's purpose." This
is claims-rule mode (i) — the new rule — applied as designed, with the
unverifiability itself named as the defect.

Measured detection (2/3 per effort) is an UNDERCOUNT caused by the
oracle matcher: low run2 ("The orchestrator is outside **this**
diff") and high run2 ("not part of this diff") semantically detect
but contain no needle ("outside the diff" is the closest; "outside
this diff" ≠ substring match). Semantic detection: 6/6. Matcher
detection: 4/6. The capability is real; the needle list is phrasing-
brittle.

## D. M13 — continued miss is a severity downgrade, not perception

0/6 blocking, but the floating `@v4` reference was explicitly noticed
and downgraded to non-blocking in at least 3 runs (high run0: "the
reusable workflow is referenced by the mutable tag @v4 … Pin the
reference to a full commit SHA"; high run2 similar; low run2 touches
it via the outside-diff caveat). The language (pin/tag/v4/SHA) would
match the oracle if severity were blocking. The blocking slot in
every run was consumed by the trigger/title mismatch (the C13 false-
block pattern) — attention misallocation toward the adjudicated-clean
issue and away from the real one. Root cause of the downgrade: the
rubric's severity standard has no supply-chain-immutability blocking
provision, and the external-facts rule's advisory branch ("suboptimal
under a deployment you are assuming") is the natural reading for a
mutable reference that is not "incorrect as written". Failure mode:
**severity**. Remains non-gating/KNOWN_GAP for historical B1
interpretation, per preregistration.

---

## E. Accounting discrepancy — tooling bug confirmed (summary side); ledger vindicated

Measured from the frozen records themselves: all 90 generations have
complete usage; total 156,002 in / 130,302 out = **$0.044276** at the
recorded prices — matching the ledger's settled tokens exactly
(the authoritative ledger-derived spend figure, as corrected in the
evidence README at PR #83 merge). The ledger reconciles exactly
with the records; seeding introduced no double-count across the six
invocations.

The per-effort `summary.json` `actual_cost_usd` values are the defect:
each equals **only that effort's LAST invocation** — low $0.006593 ==
low-run2's records-derived cost to the microdollar; high $0.008892 ==
high-run2. Mechanism: a fresh per-process `SpendGuard` is constructed
per invocation (`main()`), accumulates only its own 15 reviews, and is
written into `summary.json` as if it were the effort total, silently
ignoring the 45 records already in the out_dir. (Minor display nit in
the same area: execute.sh's printer reads `provider_generations` while
`SpendGuard.state()` emits `provider_generations_billed`.)

**Proposed deterministic repair (separate PR, with regression tests,
no retroactive edit of frozen evidence):** derive `actual_cost_usd`
(and token totals) in `summary.json` from `records.jsonl` usage — the
persisted source of truth — instead of the in-memory per-process
guard; keep the ledger as the ceiling authority; add a regression test
asserting summary spend == records-derived spend for a multi-invocation
out_dir; fix the printer key.

---

## Cause distribution (all 19 control findings + detection misses)

| Cause | Count | Items |
|---|---|---|
| MODEL_RULE_VIOLATION | 17 | all C3 (7), all C13 (6), C12 KeyError ×3, C12 session speculation ×1 |
| RUBRIC_AMBIGUITY | 2 | C12 ParseError ×2 (possible oracle-defect flag → human adjudication) |
| RUBRIC_LICENSED | 0 | — |
| VALID_BLOCKER | 0 | against the frozen oracle as written |
| severity downgrade (detection misses) | 2 fixtures | M3 low run1 (mode-(ii) misread), M13 ×≥3 runs (no immutability blocking standard) |
| matcher phrasing miss | 3 runs | M16 low run1, M4 low run2, M4 high run2 (semantic detection present in all) |

## Narrowly stated hypothesis for the next intervention

The dominant failure is **severity overreach on true-but-unproven-harm
observations** (17/19), sustained across rubric revision, concentrated
in the "shipped behavior is itself harmful" / "broken or unsafe"
escape hatches, which — unlike the demonstrability rule — carry no
requirement that the alleged harm be demonstrable from the diff. The
models resolve harm-ambiguity toward blocking (same profile as
Stage A). The evidence supports ONE narrow class of intervention: a
severity-calibration change that tethers the harm/unsafe escape
hatches to in-diff demonstrability (presumed harm on unseen code is
advisory), plus matcher-vocabulary normalization for the three
phrasing-brittle needles. Both are rubric+oracle changes: they require
a new reviewed preregistration with frozen fixtures and a measured
qualification loop — they are proposals for the human to consider,
not commitments, and nothing here authorizes drafting them.

---

*Diagnosis-only document. No rubric, oracle, fixture, matrix, or
criteria change made or drafted. B1 FAIL stands; B2 not permitted;
GLM remains non-authoritative.*


---

## Adjudication addendum (human, 2026-09-21 — after this diagnosis was written)

- **C12 stays CLEAR.** The fixture's own exception taxonomy
  (`OriginError` = unreachable / 5xx; `ParseError` = malformed
  payload) establishes the intended semantics: the stale-good
  fallback is for origin unavailability; malformed live data
  propagates. The ambiguity came from the broader docstring phrase
  "on origin failure". The two ParseError findings are classified
  **fixture/rubric ambiguity, not VALID_BLOCKER**. B1 is not
  retroactively changed; the C12/M12 fixture pair was clarified in
  the Phase-08 deterministic repair PR (oracle identity bumped).
- **C13 counting advisory check:** not a bug — low run0 emitted two
  blocking findings, run1 one, run2 CLEAR: three blocking findings
  across two blocked reviews, exactly as reported.

## Disposition

- Accounting repair, matcher hardening (+ deterministic replay), and
  the C12/M12 clarification shipped in the Phase-08 deterministic
  repair PR; the replay shows exactly three moved run-level
  detections (M16 low run1, M4 low run2, M4 high run2 — all
  False -> True) and zero movement on any Stage-A classification.
- The M3 policy resolution and the structured blocking-evidence
  boundary are specified in `DESIGN-NEXT-INTERVENTION.md` in this
  directory and are NOT implemented here; both require a new reviewed
  preregistration before any paid campaign.
