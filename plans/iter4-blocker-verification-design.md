# T1.3 iteration 4 mechanism design — bounded blocker-verification pass

Status: PROPOSAL (rev 2, after #56 review) — zero model calls, zero
eval changes. On approval this doc becomes the implementation plan
for the next T1.3 mechanism. The main plan pre-declares candidate
layer (d): *"dedicated discrimination pass — only if the single-pass
form is measured insufficient; a layer must earn its existence."*
Three measured failures (iter-1, iter-2, layer b) are that
measurement.

Rev-2 corrections from the #56 review (each verified against the
Phase-1 code, not memory):

1. the two-call loop lives in **`engine.py`**, not `review.sh` —
   the engine has always owned the model transport (`_call_model` /
   `_post_chat`, retry policy); `review.sh` owns "ONLY fetch + post",
   and `eval/run_corpus.py` invokes `engine.run_review` directly so
   production and evaluation exercise ONE model-facing pipeline;
2. **`rubric.md` does not change** — `_build_prompts()` embeds
   `review_input["policy"]` (the bundled rubric) into pass 1's system
   prompt, so any rubric edit breaks the pass-1 byte-identity
   invariant; the verifier protocol is a separate engine-owned
   pass-2-only prompt surface;
3. the anchoring claim is honest: findings carry
   `file/line/severity/comment/suggestion` — there is no
   title/detail split, and `comment` contains pass-1 reasoning by
   design; anchoring is a **measured risk**, not an architectural
   elimination;
4. fail-closed is split by failure domain: semantic verdict failure →
   INCONCLUSIVE; transport failure → existing retry policy → hard run
   failure (infrastructure is never scored as reviewer capability);
5. no confirmation-rate band; instead a **causal non-vacuity gate**
   measured pre→post within the same campaign (§4, criterion 6).

## 0. Hypothesis (falsifiable form)

**H1 (working hypothesis, not established fact):** across the five
confirmed false-blocker families, a common failure mode dominates —
the model emits a blocking verdict whose justification requires an
inference the supplied evidence does not support (blocker
justification / inference validation), rather than five independent
per-family wording failures.

**H1 predicts** that inserting a narrow semantic verification stage —
which must independently reconstruct the evidence → requirement →
contradiction chain for each blocking candidate before it may remain
`blocking` — will reduce adjudicated false blockers across MULTIPLE
families simultaneously while retaining detection at or above the
Deviation 6 floors.

**H1 is falsified by the governed campaign if** verification behaves
as (a) a rubber stamp (refutations ~never occur; false-blocker counts
do not fall below caps; criterion 6 non-vacuity fails) or (b) an
over-trigger (verification demotes genuine findings; any Deviation 6
floor violated; sonnet M17 below 5/5). Either outcome rejects the
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

### 2.1 Engine-owned two-call review flow

`engine.run_review()` owns the entire two-call review; `review.sh`
is unchanged and stays "ONLY fetch + post"; `eval/run_corpus.py` is
unchanged and keeps exercising the same `run_review` path as
production.

```text
run_review(review_input)
    ↓
pass 1: _build_prompts + _call_model          (UNCHANGED bytes)
    ↓
parse_review normalization                    (UNCHANGED)
    ↓
deterministic: any blocking candidates?
    ├─ no → ReviewResult, byte-identical to today (single call)
    └─ yes
         ↓
       build verification request
       (same effective input + candidate allegations + protocol)
         ↓
       pass 2: _call_model (same model, same retry policy)
         ↓
       strict verification parse (parse_review)
         ↓
       apply keep/demote policy
         ↓
       final ReviewResult (unchanged shape)
```

Hard invariants, all deterministic and testable without model calls:

- **Pass 1 is byte-identical** to the current reviewer subject: same
  prompts (`rubric.md` unchanged → `policy` unchanged → system
  prompt unchanged), same budget, same parse.
- **Zero-blocking-candidate reviews are byte-identical end to end**:
  exactly one model call, one normalization pass, ReviewResult equal
  to today's.
- Verification can only **keep or demote**. It never upgrades, never
  creates findings, never edits finding text. Demoted findings use
  the canonical `non-blocking` severity with truthful reason
  `verification_refuted`.
- All-blockers-demoted → CLEAR retains its existing engine semantics;
  label is recomputed from final findings, so C7-style label/evidence
  mismatch remains possible and remains INCONCLUSIVE under the
  existing rule.
- The Deviation 6 floors remain the anti-vacuity guard: wholesale
  demotion collapses floors and fails the campaign by construction.

### 2.2 Verification stage (verifier input, protocol, output)

**Verifier input (honest form).** The verifier receives the same
effective input pass 1 saw (title/body/file set/budgeted diffs via
the existing `_budget`/`_build_prompts` input path) plus each
blocking candidate as an allegation: its `file`, `line`, `severity`,
and its `comment`. Because `comment` is "what is wrong and why it
matters", the allegation **contains pass-1 reasoning**; there is no
deterministic way to extract "just the proposition" from that prose.
The verifier is therefore instructed to **independently reconstruct
the evidential chain** — evidence → requirement → contradiction —
from ReviewInput, not to audit the candidate's argument. Anchoring
remains an explicit **measured risk** (§5); the architecture does not
claim to eliminate it.

**Protocol (verifier prompt content, pass-2-only surface).** For
each candidate the verifier answers five questions:

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

**Structured verifier output (one strict JSON object for the whole
candidate set; per-candidate audit trail):**

```json
{"verdicts": {"<candidate-id>": {
  "evidence_establishes": "...",
  "applicable_requirement": "...",
  "contradiction": "...",
  "unstated_assumption": "...|none",
  "correct_implementation_possible": true|false,
  "verdict": "confirmed|refuted"}}}
```

These reconstruction fields are **verifier telemetry/evidence**; they
are not added to ReviewResult v1 (shape unchanged). They are recorded
per run so the campaign can audit the reconstruction quality, not
just the verdict counts.

**Failure domains (split, both fail closed):**

```text
SEMANTIC (model responded 200 but unusable):
  malformed/non-JSON body, missing candidate id, extra id,
  invalid verdict value, refusal/non-answer
    → review is INCONCLUSIVE (parse_review owns INCONCLUSIVE;
      never guesses)

TRANSPORT (network/timeout/retryable HTTP):
  existing engine retry policy (3 attempts, backoff)
    → hard run failure if exhausted
```

An OpenRouter outage must never be scored as reviewer-capability
GATING evidence; equally, a malformed verdict must never become
CLEAR. No retries inside a governed run beyond the standing transport
policy.

### 2.3 Component surfaces (complete change map)

```text
review.sh             UNCHANGED (ONLY fetch + post)
rubric.md             UNCHANGED (pass-1 byte identity)
engine.py             pass-1 path untouched; adds verification-request
                      construction + policy application inside
                      run_review; adds the pass-2-only verifier prompt
                      builder (25c reviews this surface separately)
parse_review.py       adds strict verifier-result parsing (INCONCLUSIVE
                      fail-closed semantics)
eval/run_corpus.py    UNCHANGED (same run_review path)
ReviewInput v1        UNCHANGED
ReviewResult v1       UNCHANGED (demotion = existing severity/reason
                      vocabulary)
renderer              UNCHANGED
tests/                new deterministic suites for the above
```

### 2.4 Cost shape

A second call occurs **only** for reviews with ≥1 blocking candidate;
controls that pass cleanly stay single-call. Worst case for an N=5
dual-profile campaign: 360 reviews → up to 720 calls. Observed
layer-(b) spend was $3.06/360 calls; the doubled ceiling is estimated
at ≤ $7. Exact authorization is requested at freeze (25d) against the
frozen identity — never assumed here.

## 3. Lifecycle and phasing

```text
25a  this design PR (reviewer-side design only; zero calls)
25b  engine orchestration (conditional pass 2 + policy) +
     parse_review verifier parsing + deterministic tests
     (byte-identity invariants; keep/demote policy unit tests;
     semantic-INCONCLUSIVE vs transport-failure split tests)
25c  verifier prompt/protocol surface ONLY (pass-2 prompt builder
     content; separately reviewed for reviewability)
25d  freeze (identity: new subject, same oracle
     cb6870c5a4c635b2 UNCHANGED, same corpus 72035a00b8db828d
     UNCHANGED) → ONE governed campaign, N=5 dual-profile, spend
     authorized exactly once → frozen interpretation applied
     verbatim → keep or revert
```

`rubric.md` and `review.sh` change in **no** PR of this series. Eval
semantics (fixtures, harness, states, floors) change in **no** PR of
this series; oracle/subject separation holds (25b/25c change the
subject; the oracle cannot move). If any 25b/25c review reveals a
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
   pair integrity (no positive promotable while its control fails);
6. **causal non-vacuity (measured in the same campaign):** among
   control fixtures where pass 1 produced a blocking candidate,
   verification must refute/demote at least one such candidate in at
   least two confirmed families — i.e. the new layer demonstrably
   CAUSED an improvement across multiple families, with pre- and
   post-verification ReviewResults both recorded. This gate exists
   because pass 1 is unchanged: retention must not be earned by a
   lucky first-pass draw with an always-confirm verifier.

Internal telemetry is mandatory but never gated numerically:
confirmation/refutation rates per family and positive/control,
pre→post candidate deltas, per-family effects. There is **no**
confirmation-rate band — an arbitrary interval would be exactly the
benchmark-shaped proxy this project avoids; outcome gates decide.

Anything else → REVERT the mechanism components (engine pass-2
policy/prompt, verifier parsing) and record the negative result. No
partial keeps, no post-hoc criterion editing. On KEEP, the same
campaign's predicates are checked against the binding T1.2 reference
and T1.3 stage exit; where they align, one bundle serves both — no
second campaign is run merely to duplicate identical gates.

## 5. Risks (recorded before measurement)

- **Rubber stamp (most likely failure):** same-profile verification
  may confirm nearly everything — narrative changes, verdict never
  does (the phase-4 probe failure mode at one abstraction up).
  Falsified by criteria 4/5 and, mechanically, by criterion 6.
- **Anchoring (honest residual):** the verifier sees pass-1 reasoning
  inside `comment`; independent reconstruction is instructed, not
  enforced. Measured via the per-candidate reconstruction fields —
  refutations whose `contradiction` merely restates the allegation
  are visible as low-quality verification in the evidence.
- **Over-suppression (layer-b echo):** a strict entailment challenge
  may demote genuine findings — falsified by the Deviation 6 floors
  (criterion 2) exactly as layer (b) was.
- **Latency/fragility:** two calls double the timeout surface.
  Transport failure keeps its own failure domain (retry → hard run
  failure), so infrastructure flakiness costs wall-clock time, never
  semantic evidence; semantic verdict failure costs the review
  (INCONCLUSIVE), never silently passes.
- **Scope creep:** the conditional second call is the entire
  architecture. Any "while we're here" (retrieval, agents,
  confidence, judge models, family rules) is out of scope by this
  document and the main plan.

## 6. What this document deliberately does NOT decide

- The exact verifier prompt wording (25c, after 25b's plumbing
  exists to test it deterministically).
- Spend ceiling (25d freeze, human-authorized).
- Whether H1 survives (the campaign decides; this document builds no
  outcome into the architecture).
