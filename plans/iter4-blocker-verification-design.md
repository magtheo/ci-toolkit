# T1.3 iteration 4 mechanism design — bounded blocker-verification pass

Status: PROPOSAL (rev 1) — zero model calls, zero eval changes. On
approval this doc becomes the implementation plan for the next T1.3
mechanism. The main plan pre-declares candidate layer (d):
*"dedicated discrimination pass — only if the single-pass form is
measured insufficient; a layer must earn its existence."* Three
measured failures (iter-1, iter-2, layer b) are that measurement.

## 0. Hypothesis (falsifiable form)

**H1 (working hypothesis, not established fact):** across the five
confirmed false-blocker families, a common failure mode dominates —
the model emits a blocking verdict whose justification requires an
inference the supplied evidence does not support (blocker
justification / inference validation), rather than five independent
per-family wording failures.

**H1 predicts** that inserting a narrow semantic verification stage —
which must independently derive the contradiction between the
candidate finding and the supplied evidence before any finding may
remain `blocking` — will reduce adjudicated false blockers across
MULTIPLE families simultaneously while retaining detection at or
above the Deviation 6 floors.

**H1 is falsified by the governed campaign if** verification behaves
as (a) a rubber stamp (confirmation rate ≈ 100% regardless of family;
false-blocker counts do not fall below caps) or (b) an over-trigger
(verification demotes genuine findings; any Deviation 6 floor is
violated; sonnet M17 falls below 5/5). Either outcome rejects the
mechanism under the frozen keep/revert lifecycle; neither can be
engineered away mid-campaign.

Distinction from layer (b): layer (b) asked *"is there evidence?"*
and measured that presence is not entailment. Iteration 4 asks
*"does the blocking conclusion follow from that evidence?"* — a
semantic question a deterministic substring check cannot answer.

## 1. Measured basis (why this layer, why now)

Three mechanisms have completed the frozen lifecycle and were
rejected; all three kept the single-pass form:

| | iter-1 (layer a) | iter-2 (layer a) | layer (b) |
|---|---|---|---|
| mechanism | grounding rubric wording | grounding + contradiction protection | structured support + deterministic validation |
| sonnet M17 (hard floor 5/5) | 0/5 | 0/5 | 0/5 |
| C7 (GATING control) | clean | violated both profiles | violated (sonnet) |
| spec-family FBs vs caps (53/50/103) | improved, not below | 165 — regressed | 60 — above cap |
| Deviation 6 floors | hard regression | 4 violations | **21 violations** (haiku aggregate 2/90 vs 51) |

Recorded diagnoses: prose admissibility rules ask the model to
*weigh* sufficiency — a judgment it performs unreliably (chilling
real detection while still emitting speculative blockers); and forced
citation *presence* does not establish entailment (false-blocking
narratives supplied valid verbatim quotes while remaining
semantically unsupported). The residual commonality across the five
families — speculative-consequence, hallucinated-fact, absolute-
consistency, severity-inflation, risk-boilerplate — is that each
blocking narrative contains an inferential step the input does not
license. No single-pass wording mechanism tested that step; layer (b)
tested only that a quote existed. Iteration 4 tests the step itself.

Layer (d) is therefore exercised per the main plan's pre-declaration.
The complexity budget stays deliberately small: **candidate
generation → candidate verification, nothing more.** No agents, no
debate graphs, no confidence scoring, no retrieval expansion, no
stronger judge model, no cross-profile verification (each profile
verifies its own findings — qualification semantics stay per-profile
and interpretable), no family-specific rules anywhere.

## 2. Mechanism design

### 2.1 Two-call review flow

```text
Pass 1 (unchanged):  current rubric, current engine/parse
                     → candidate ReviewResult (findings may be blocking)
        │
        ▼ deterministic: any blocking candidates?
 no → ReviewResult emitted byte-identically to today (single call)
        │ yes
        ▼
Pass 2 (new):        one verification call, SAME profile, containing:
                     - the review input (title/body/file set/diffs —
                       the same effective input pass 1 saw)
                     - each blocking candidate as CLAIMS
                       (title + detail + severity + cited location),
                       with stable candidate ids
                     - the challenge protocol (§2.2)
        │
        ▼ deterministic: apply verification policy
 confirmed    → finding remains blocking, content unchanged
 refuted      → demoted to advisory (canonical `non-blocking`
                severity, truthful reason `verification_refuted`)
 unparseable /
 refused      → review becomes INCONCLUSIVE (fail closed;
                parse owns INCONCLUSIVE, never guesses)
```

Hard invariants, all deterministic and testable without model calls:

- Pass 1 is **byte-identical** to the current reviewer subject: same
  prompts, same budget, same parse. The mechanism adds a stage; it
  does not touch pass-1 behavior.
- Zero-blocking-candidate reviews produce **byte-identical transport
  behavior** to today: exactly one model call, one engine
  normalization pass.
- Verification can only **keep or demote**. It never upgrades, never
  creates findings, never edits finding text or title.
- All-blockers-demoted → CLEAR retains its existing engine semantics
  (same as the reverted layer (b)); label is recomputed from final
  findings, so C7-style label/evidence mismatch remains possible and
  remains INCONCLUSIVE under the existing rule.
- The Deviation 6 floors remain the anti-vacuity guard: wholesale
  demotion collapses floors and fails the campaign by construction.

### 2.2 Verification challenge protocol (verifier prompt content)

For each candidate, the verifier answers five questions and returns a
strict verdict:

```text
1. What observable proposition does the supplied evidence establish?
2. What requirement / invariant / stated contract applies?
3. What exact contradiction or failing behavior follows?
4. Does that conclusion follow from the evidence, or is an
   unstated assumption required?
5. Could the same supplied evidence plausibly describe a correct
   implementation?

If the defect cannot survive this challenge: REFUTED.
Else: CONFIRMED.
```

Output: one strict JSON object for the whole candidate set —
`{"verdicts": {"<candidate-id>": {"verdict": "confirmed|refuted",
"basis": "<short citation-grounded rationale>"}}}`. Any missing id,
extra id, malformed verdict value, or non-JSON body → that review is
INCONCLUSIVE (fail closed). No retries inside a governed run.

Anchoring control (design decision, reviewable): the verifier
receives the candidate's **claims** (what is asserted, where) but not
pass 1's narrative reasoning — it must derive the contradiction from
the input, not audit the candidate's argument. This is the strongest
available same-profile anti-rubber-stamp measure; the campaign
records per-family confirmation rates as telemetry so a rubber-stamp
failure mode is visible in the evidence regardless of the verdict
counts.

### 2.3 Transport contract (the honest architecture change)

`engine.py` stays semantically pure — no transport, no GitHub
concepts. Two model calls therefore require a transport-side loop:

- `engine.py` gains: verification-request construction (given
  effective input + candidate set, produce the pass-2 payload), and
  verification-policy application (given pass-1 ReviewResult +
  pass-2 verdicts, produce the final ReviewResult).
- `review.sh` gains the minimal loop: call model → normalize via
  engine → if engine declares a verification request, call model
  again with that payload → normalize verdicts via engine → emit
  final result. No new dependencies; curl-only, same as today.
- `parse_review.py` gains verdict extraction (strict schema, the
  INCONCLUSIVE fail-closed path).
- The renderer consumes an unchanged ReviewResult shape; demotion is
  expressed as existing severity + reason vocabulary.

### 2.4 Cost shape

A second call occurs **only** for reviews with ≥1 blocking candidate;
controls that pass cleanly stay single-call. Worst case for an N=5
dual-profile campaign: 360 reviews → up to 720 calls. Observed
layer-(b) spend was $3.06/360 calls; the doubled ceiling is estimated
at ≤ $7. Exact authorization is requested at freeze (25d) against the
frozen identity — never assumed here.

## 3. Lifecycle and phasing (mirrors the 20-series)

```text
25a  this design PR (reviewer-side design only; zero calls)
25b  engine + parse + review.sh orchestration + deterministic tests
     (byte-identity invariants; verification policy unit tests;
     INCONCLUSIVE fail-closed tests) — reviewer-side only
25c  rubric verification-protocol section (reviewer-side prompt
     content; separate PR for reviewability, same convention as
     20b/20c)
25d  freeze (identity: new subject, new rubric hash, oracle
     cb6870c5a4c635b2 UNCHANGED, corpus 72035a00b8db828d UNCHANGED)
     → ONE governed campaign, N=5 dual-profile, spend authorized
     exactly once → frozen interpretation applied → keep or revert
```

Eval semantics (fixtures, harness, states, floors) change in **no**
PR of this series; oracle/subject separation holds (25b/25c change
the subject; the oracle cannot move). If any 25b/25c review reveals a
needed eval-side change, the series stops and escalates.

## 4. Frozen interpretation (pre-declared; applied verbatim at 25d)

KEEP requires ALL of, in the single authorized campaign:

1. zero GATING violations on both profiles (C4/C5/C7);
2. every Deviation 6 per-positive sensitivity floor met on both
   profiles (haiku 51/90, sonnet 66/90 aggregates as the summary
   form; per-positive floors normative);
3. sonnet M17 = 5/5 (hard invariant);
4. speculative-consequence FBs ≤ 53 haiku / 50 sonnet / 103
   aggregate; overall control FBs ≤ 78 / 112;
5. every confirmed family shows separation (per-family table), with
   pair integrity (no positive promotable while its control fails).

Anything else → REVERT all three components (transport loop, engine
policy, rubric section) and record the negative result. No partial
keeps, no post-hoc criterion editing. On KEEP, the same campaign's
predicates are checked against the binding T1.2 reference and T1.3
stage exit; where they align, one bundle serves both — no second
campaign is run merely to duplicate identical gates.

## 5. Risks (recorded before measurement)

- **Rubber stamp (most likely failure):** same-profile verification
  may confirm nearly everything — narrative changes, verdict never
  does (the phase-4 probe failure mode at one abstraction up).
  Falsified by criterion 4/5 counts, visible early in per-family
  confirmation telemetry.
- **Over-suppression (layer-b echo):** a strict entailment challenge
  may demote genuine findings — falsified by the Deviation 6 floors
  (criterion 2) exactly as layer (b) was.
- **Latency/transport fragility:** two calls double the timeout
  surface; fail-closed INCONCLUSIVE makes transport flakiness a
  GATING-visible cost rather than a silent pass. Accepted: honesty
  over greenness.
- **Verifier sees less context than pass 1?** No: the verifier sees
  the same effective input, only not pass 1's narrative.
- **Scope creep:** the two-call loop is the entire architecture. Any
  "while we're here" (retrieval, agents, confidence, judge models,
  family rules) is out of scope by this document and the main plan.

## 6. What this document deliberately does NOT decide

- The exact verifier prompt wording (25c, after 25b's plumbing
  exists to test it deterministically).
- Spend ceiling (25d freeze, human-authorized).
- Whether H1 survives (the campaign decides; this document builds no
  outcome into the architecture).
