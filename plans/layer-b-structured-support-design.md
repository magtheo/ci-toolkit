# Layer (b) mechanism design — structured finding support + deterministic support validation

Status: PROPOSAL — zero model calls, zero eval changes. On approval this
doc becomes the implementation plan for the next T1.3 mechanism; the
main plan (`plans/reviewer-eval-baseline.md` §T1.3, lines 518–532)
pre-declares layer (b): *"finding schema + deterministic support
validation — blocking findings must carry structured support …
under-supported blocking findings are downgraded to advisory by the
deterministic layer (parse/engine), keeping the decision auditable."*

## 1. Measured basis (why this layer, why now)

Two rubric-only (layer a) iterations have failed the frozen hard
lifecycle in opposite directions, under the same governed protocol:

| | iteration 1 (#39→#41) | iteration 2 (#43→#46) |
|---|---|---|
| speculative-consequence FBs | 115→104 (improved) | 104→165 (regressed) |
| sonnet M17 (floor 5/5) | 0/5 — lost | 0/5 — still lost |
| C7 (GATING control) | clean both profiles | violated both profiles |
| control FBs | 78/112 (improved) | 83/142 (regressed) |
| new sensitivity collateral | none recorded | haiku M1 1/5, haiku M9 0/5, sonnet M13 0/5 |

Diagnosis recorded in #45: prose admissibility rules ask the model to
*weigh* whether evidence suffices — a judgment it performs unreliably
and inconsistently across families (chilling real detections while
still emitting speculative blockers). The dominant false-blocker family
(speculative-consequence) is defined by premises **absent from the
supplied input** — precisely the property a deterministic check can
test. And the genuine detections that prose chilled (M17's
contradiction, haiku M1/M9) are anchored in the input by construction —
precisely the property the same check protects.

Layer (b) moves the admissibility boundary from model judgment to a
mechanical contract: **if a blocking finding's premise cannot be
pointed at in the supplied input, it is downgraded by code, not by
persuasion.**

## 2. Mechanism design

### 2.1 Schema (additive, backward compatible)

`ReviewResult` findings gain an optional `support` field:

```json
{"file": "...", "comment": "...", "severity": "blocking",
 "line": 12, "suggestion": "...",
 "support": [{"quote": "<verbatim text from the review input>",
              "file": "optional path hint", "line": 42}]}
```

- `schema_version` stays `1` (additive optional field; consumers that
  ignore `support` are unaffected).
- Required for **blocking** findings; advisory findings may carry it
  (noise is counted, never gated).
- Any one valid support item satisfies the finding.

### 2.2 Deterministic validation (engine — the kernel)

Validation lives in `engine.py` (semantically pure: ReviewInput v1 →
ReviewResult v1, no transport, no GitHub concepts):

- Build the haystack once: the full supplied input text — diff bodies,
  PR description, provided context — whitespace-collapsed,
  case-folded.
- For each **blocking** finding: the finding passes iff at least one
  `support[i].quote`, whitespace-collapsed and case-folded, is a
  substring of the haystack.
- Fail ⇒ **downgrade to advisory** with a machine-generated suffix:
  `[downgraded by support validation: quote not found in review
  input]`. Never drop, never INCONCLUSIVE — the claim stays visible
  and the downgrade is reproducible and auditable.
- Findings with no `support` field at all take the same path (absence
  of support is under-support, not an exemption).
- Advisory findings are never validated and never promoted.

`parse_review.py` only extracts and structure-validates `support`
(array of objects with non-empty `quote` strings; never guesses).
`render.py` renders the quote and any downgrade note (presentation
consumer).

### 2.3 Rubric instruction (format contract, not judgment rule)

The rubric gains one format requirement, deliberately minimal:

> Every blocking finding must include `support`: at least one verbatim
> quote copied from the supplied review input (diff, description, or
> provided context) that the finding's premise rests on. If you cannot
> quote the input, the finding is advisory.

No admissibility prose, no family definitions, no hypothetical-harm
vocabulary — the two sentences that twice failed measurement. The
model is asked only to *point*, the same act the human reviewer rules
already demand ("No finding you cannot point at in the diff"); the
kernel then enforces what prose could not.

### 2.4 Why it generalizes (plan requirement, §T1.3)

- Family-wide by construction: every speculative-premise blocker lacks
  input-anchored support, whatever vocabulary it uses — the check does
  not chase narratives (contrast: repair-5 needles caught the #40 M16
  variants; #45 produced two new phrasings within one run).
- Structurally protective of sensitivity: validation can only demote
  findings whose quoted premise is absent from the input. A genuine
  same-input contradiction (M17 class) always has a quotable premise —
  the mechanism cannot eat it without the input itself changing.
- Auditable: every downgrade is deterministic, reproducible from the
  frozen inputs, and labeled in the rendered review.

## 3. Deliberate limits (recorded, not hidden)

- **Presence, not sufficiency**: a quote present in the input does not
  prove the *conclusion*; layer (b) targets the measured dominant
  failure (premise-absent blockers). Sufficiency remains judgment; if
  measurement shows a residual family, layer (d) must earn its
  existence per the plan.
- **Reflowed paraphrase risk**: a model that paraphrases instead of
  quoting will see genuine findings downgraded — a sensitivity risk.
  Mitigations: case-fold + whitespace-collapse matching; the rubric
  demands verbatim quotes; the governed measurement is the verdict,
  with the Deviation 6 floors (Repair-4 provenance, Repair-5 parity)
  as the hard sensitivity gate.
- **Token budget**: `support` adds output tokens; the freeze must
  watch INCONCLUSIVE rates (max_tokens stays 2000 unless the freeze
  records otherwise).

## 4. Phasing (sequential, one unmerged phase at a time; the eval/reviewer boundary is absolute)

```text
20a. this design doc — approval gate (no code)
20b. reviewer contract: schema + parse extraction + engine
     validation + deterministic tests (rubric untouched; suite
     proves the downgrade path against support-less outputs)
20c. rubric support-citation instruction (rubric.md only)
20d. eval-side freeze + human-authorized governed measurement
     (N=5 dual-profile, exactly-once; freeze records the success
     criteria: zero GATING, every Deviation 6 floor incl. sonnet
     M17 5/5, control-FB and speculative caps frozen pre-call)
```

Each of 20b/20c is reviewer-side only; 20d is eval-side only; no PR
ever mixes them. The oracle moves automatically with 20b/20c
(oracle_version hashes engine + parse_review); no fixture/state edits
are needed for the mechanism itself — floors and GATING states are
carried unchanged into the measurement.

## 5. What this phase is not

No engine/parse/rubric changes in 20a. No model calls anywhere in
this phase. No fixture, state, harness, or evidence changes. On
approval, 20b starts from the then-current feature head.
