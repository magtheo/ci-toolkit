# Layer (b) mechanism design — structured finding support + deterministic support validation

Status: PROPOSAL (rev 2, after #47 review) — zero model calls, zero
eval changes. On approval this doc becomes the implementation plan for
the next T1.3 mechanism; the main plan
(`plans/reviewer-eval-baseline.md` §T1.3, lines 518–532) pre-declares
layer (b): *"finding schema + deterministic support validation —
blocking findings must carry structured support … under-supported
blocking findings are downgraded to advisory by the deterministic
layer (parse/engine), keeping the decision auditable."*

## 0. Hypothesis (falsifiable form)

Layer (b) mechanically enforces that a blocking finding presents at
least one **non-trivial citation to model-visible review data**. It
does **not** prove that the citation entails the finding, that the
premise is relevant, or that the conclusion follows. The governed
measurement (20d) determines whether forcing and validating this
evidence pointer materially improves discrimination without violating
the Deviation 6 sensitivity floors. Nothing in this document builds
the desired outcome into the architecture; the measurement decides.

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
across families (chilling real detections while still emitting
speculative blockers). The dominant false-blocker family
(speculative-consequence) is defined by premises **absent from the
supplied input** — precisely the property a deterministic citation
check can test. Layer (b) replaces persuasion with a mechanical
citation requirement; the measurement — not this document — asserts
whether that materially separates the families.

## 2. Mechanism design

### 2.1 Model-visible support corpus (budget-identical, segment-local)

The engine already budgets what the model sees: `_budget()` caps the
file set and truncates assembled diffs; `_build_prompts()` uses only
`body[:2000]` of the PR body. Validation must use **exactly the same
effective input**:

```text
effective_review_input  (built ONCE by an engine helper)
    title
    body[:2000]
    selected file paths/statuses
    budgeted/truncated per-file diffs
        │
        ├── prompt construction (unchanged behavior)
        └── support validation (new consumer)
```

- The validator haystack is **never reconstructed independently** and
  never includes material outside the model's context — a quote that
  matches only un-budgeted or post-truncation content cannot validate.
- **Segment-local matching**: each source (title; body slice; each
  file's budgeted diff) is a separate segment. A quote must match
  within a single segment, so a citation cannot become valid by
  spanning the artificial boundary between the PR body and a file, or
  two files.
- **Excluded from matching**: policy/rubric text, synthetic prompt
  labels/markers, and any engine-added framing. The model can quote
  its instructions verbatim; that must never certify a finding.
- Matching normalization per segment: case-fold + whitespace-collapse,
  then substring test.

### 2.2 Schema (additive, minimal, no unvalidated hints)

`ReviewResult` findings gain an optional `support` field; `support`
items carry **only the quote**:

```json
{"file": "...", "comment": "...", "severity": "blocking",
 "line": 12, "suggestion": "...",
 "support": [{"quote": "<verbatim text from the model-visible input>"}]}
```

- `schema_version` stays `1` (additive optional field; consumers that
  ignore `support` are unaffected).
- Required for **blocking** findings; advisory findings may carry it
  (advisory findings are never gated by support, in any shape).
- **No `file`/`line` source hints in 20b.** The proposed draft had
  them, but only `quote` was validated — fake precision. When the
  engine resolves a quote, the engine (not the model) derives the
  matched-segment metadata. If measurement later shows source
  coordinates are worth model-supplied precision, the contract extends
  WITH validation of those fields; not before.

### 2.3 Support-validation semantics (under-support ≠ schema failure)

Support problems are **evidence problems, not structural problems**.
For a structurally valid finding:

- `"support": null`, `[]`, missing, or malformed shape (non-array,
  non-object items, empty/whitespace quotes) ⇒ **zero valid support
  items** ⇒ deterministic downgrade (blocking → advisory + reason).
  The completion is never made INCONCLUSIVE by support shape.
- Malformed `support` attached to an already-advisory finding is
  ignored; it cannot poison an otherwise valid response.
- A support item is **valid** iff `quote` is a string that (a) passes
  the anti-vacuity floor (§2.4) and (b) matches some model-visible
  segment (§2.1). Validity is judged per item; the finding needs one
  valid item.

### 2.4 Anti-vacuity floor

"Any one matching quote is enough" would let `{"quote": "if"}` certify
any blocker anywhere in any input. A support item must additionally
satisfy a deterministic minimum, frozen in code and recorded in the
20d freeze:

- normalized (case-folded, whitespace-collapsed) length **≥ 16
  characters**, AND
- **≥ 3 lexical tokens** (maximal alphanumeric runs).

Boundary cases (`"a"`, `"if"`, `"return"`, punctuation-only, exactly
at the thresholds) are locked by tests in 20b. The constants are
deliberately simple; their purpose is to make vacuous presence
impossible, not to approximate relevance.

### 2.5 Explicit post-support assessment pipeline (never-INCONCLUSIVE is about demotion, not about malformed evidence)

Normalization order is made explicit; the support stage sits between
structure validation and the final assessment:

```text
parse JSON                                  (fail-closed as today)
    ↓
validate core finding structure             (fail-closed as today)
    ↓
support validation (deterministic)
    ├─ supported blocker        → blocking
    └─ unsupported blocker      → advisory + downgrade reason
    ↓
deterministic final assessment
    ├─ ≥ 1 surviving blocker            → ISSUES_FOUND
    ├─ blockers present, all demoted    → CLEAR
    └─ structurally untrusted /
       label-evidence contradictory
       for NON-support reasons          → INCONCLUSIVE
```

- **Intentional deterministic demotion is not malformed evidence.** A
  blocker removed by support policy leaves a valid, internally
  consistent response — the assessment is CLEAR (advisories may
  remain), with the downgrade reasons attached to the demoted findings.
- The existing fail-closed path is untouched: JSON decode failure,
  schema-invalid findings, or an ISSUES_FOUND label with no validated
  blocking finding **for non-support reasons** remain INCONCLUSIVE
  (e.g. the C7-style label mismatch must still be INCONCLUSIVE —
  support demotion must not become a loophole that launders a
  contradictory label into CLEAR).
- 20b tests lock the distinction directly: (i) the C7-style
  label-mismatch case stays INCONCLUSIVE; (ii) a well-formed blocking
  finding demoted by support policy yields ISSUES_FOUND→CLEAR with
  the downgrade reason preserved; (iii) a surviving supported blocker
  yields ISSUES_FOUND.

### 2.6 Rubric instruction (format contract, not judgment rule)

The rubric gains one minimal format requirement:

> Every blocking finding must include `support`: at least one verbatim
> quote copied from the supplied review input (diff, description, or
> provided context) that the finding rests on. If you cannot quote the
> input, the finding is advisory.

No admissibility prose, no family definitions, no hypothetical-harm
vocabulary — the two sentences that twice failed measurement. The
model is asked only to *point*; the kernel enforces the pointing.

### 2.7 Why it might generalize (plan requirement, §T1.3 — stated as testable expectations, not guarantees)

- **Family-wide reach**: a speculative-premise blocker has no
  model-visible anchor for its premise, whatever vocabulary it uses —
  if the model cannot manufacture matching non-trivial quotes, the
  check does not chase narratives (contrast: repair-5 needles caught
  the #40 M16 variants; #45 produced two new phrasings within one
  run). Falsifiable risk, recorded: the model may quote real,
  relevant-looking lines while still making unsupported leaps; if 20d
  shows that, plain citation presence is measured insufficient and
  that evidence earns consideration of the next mechanism — it is not
  preemptively built here.
- **Auditability**: every downgrade is deterministic, reproducible
  from the frozen inputs, and labeled in the rendered review — the
  post-run record shows exactly which narratives lost support and why,
  whether the mechanism is kept or reverted.

## 3. Deliberate limits (recorded, not hidden)

- **Citation presence, not entailment** (see §0): a matching quote
  does not prove the finding; a genuine finding may be lost if the
  model paraphrases instead of quoting. Both failure directions are
  measured, not assumed away.
- **Budget coupling**: validation is only as generous as the prompt —
  by design. Content the model never saw can neither support nor be
  quoted.
- **Token budget**: `support` adds output tokens; the freeze must
  watch INCONCLUSIVE rates (max_tokens stays 2000 unless the freeze
  records otherwise).
- The mechanism does **not** retroactively touch frozen evidence; all
  prior bundles remain byte-immutable.

## 4. Identity semantics (corrected)

- `oracle_version()` hashes **eval-side** inputs only —
  `eval/run_corpus.py`, fixture bytes, `states.json` — and deliberately
  excludes the subject, so an old subject can be evaluated against a
  new oracle.
- Therefore: **20b (engine/parse contract) and 20c (rubric) produce a
  NEW subject / reviewer semantics; the oracle is unchanged unless
  eval semantics change.** No fixture, state, or harness edits are
  needed for the mechanism itself; the Deviation 6 floors (Repair-4
  provenance, Repair-5 parity) and GATING states carry unchanged into
  any 20d freeze.
- This is the desired property: the absolute reviewer/eval boundary is
  preserved — a governed 20d measurement against the *same* oracle is
  what makes pre/post discrimination comparable.

## 5. Phasing (sequential, one unmerged phase at a time; the eval/reviewer boundary is absolute)

```text
20a. this design doc — approval gate (no code)
20b. reviewer contract: schema + parse extraction + engine
     validation + effective-review-input helper + deterministic
     tests (rubric untouched; tests lock §2.3/§2.4/§2.5 semantics,
     including the C7-style contrast)
20c. rubric support-citation instruction (rubric.md only)
20d. eval-side freeze + human-authorized governed measurement
     (N=5 dual-profile, exactly-once; freeze records the success
     criteria: zero GATING, every Deviation 6 floor incl. sonnet
     M17 5/5, control-FB and speculative caps frozen pre-call,
     anti-vacuity constants recorded)
```

Each of 20b/20c is reviewer-side only; 20d is eval-side only; no PR
ever mixes them. **No model spend anywhere in 20a–20c.**

## 6. What this phase is not

No engine/parse/rubric changes in 20a. No model calls anywhere in
this phase. No fixture, state, harness, or evidence changes. On
approval, 20b starts from the then-current feature head.
