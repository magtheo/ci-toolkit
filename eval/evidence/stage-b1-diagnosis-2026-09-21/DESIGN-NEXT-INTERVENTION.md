# Design — next intervention (Phase-08 output; NOT implemented here)

Status: design proposal derived from the frozen Stage-A/B1 evidence
and the Phase-08 replay. Nothing in this document changes the rubric,
the ReviewResult contract, or any campaign. Both proposals below are
reviewer-intelligence + oracle changes and therefore require a new
reviewed preregistration (with frozen fixtures and a measured
qualification loop) before any paid execution. B1.1 and B2 remain
not-started.

## 1. M3 policy resolution — contradicted file-local contract vs scope mismatch

### The decision to make

Can a **directly contradicted, file-local behavioral contract** be
blocking even when the resulting program remains operational?

### Proposed resolution (distinguishing M3 from C13)

Split the claims rule's mode (ii) into two paths with different
severity eligibility:

- **(ii-a) File-local contract contradiction — blocking-eligible.**
  The changed file's own central documented invariant (docstring,
  header comment) is directly contradicted by that same file's shown
  code. The defect is demonstrable without any assumption about code
  outside the diff: the contract and its violation live in the same
  hunk. Operational-but-wrong still counts: the guard exists to
  enforce its documented invariant; code that silently defeats it is
  broken as shipped. Examples that qualify: M3 (header promises
  parsed-date staleness; code measures mtime — the guard's own
  example case is defeated), M12 (clarified docstring promises
  malformed payloads propagate; code catches ParseError and masks it
  with `{}`).
- **(ii-b) Description/title-vs-diff mismatch — advisory by default.**
  The PR's stated purpose does not match the shipped behavior, but no
  in-file documented contract is contradicted. Blocking requires
  independently demonstrated in-diff harm. Example: C13 (title says
  "on merge"; trigger fires on PR events — a mismatch whose alleged
  harm lives in an unseen reusable workflow).

### Validation of the distinction against the frozen evidence

Applied to every B1 control finding, (ii-a)/(ii-b) classifies
correctly with zero false-blocks and zero lost positives:

| Finding family | Path | Severity outcome |
|---|---|---|
| C3 exit-code / missing-file | no claimed contract violated | advisory (correct — fixture CLEAR) |
| C12 KeyError-on-empty-cache | docstring says "raises"; it raises | advisory (correct) |
| C12 ParseError propagates | clarified contract says propagates | advisory (correct, post-Phase-08) |
| C13 trigger/title mismatch | (ii-b) | advisory (correct) |
| M3 mtime-vs-parsed-date | (ii-a), file-local | blocking-eligible (correct) |
| M12 ParseError masked | (ii-a), file-local | blocking-eligible (correct) |
| M16 swallow + fabricated success | broken behavior (correctness), plus the file's own comment claims "report the summary the caller expects" while the call may never have succeeded | blocking-eligible (correct) |

This is a rubric change: it must go through a new preregistration with
paired fixtures and measured qualification; it is deliberately NOT
implemented in Phase 08.

## 2. Structured blocking-evidence boundary

### Architecture question

B1 showed finding **discovery** is strong (M4 6/6 semantic, M16 3/3
semantic, M13 3/6 perception) while **permission to block** is the
failure surface (17/19 control blockers were rule violations: true
observations promoted to blocking on presumed harm). Proposal: keep
discovery probabilistic; make blocking permission substantially
deterministic by requiring machine-checkable evidence metadata on
every blocking finding, enforced by the parser — not by the model's
own judgment.

### Finding schema v2 (additive, optional field)

```json
{
  "file": "path/from/diff", "line": 12,
  "severity": "blocking" | "non-blocking",
  "comment": "what is wrong and why it matters",
  "evidence": {
    "kind": "in_diff_behavior" | "in_diff_contract_contradiction"
          | "external_fact" | "out_of_diff_assumption",
    "quote": "verbatim text from the cited diff file — the exact
              code the defect lives in — or null",
    "harm": "demonstrated" | "presumed"
  }
}
```

### Deterministic severity gate (parser-owned, mirrors "parser owns INCONCLUSIVE")

A finding with `severity == "blocking"` is **auto-downgraded** to
`non-blocking` with `machine_reason: "BLOCKING_EVIDENCE_INSUFFICIENT"`
unless ALL hold:

1. `evidence.kind != "out_of_diff_assumption"`;
2. `evidence.harm == "demonstrated"`;
3. `evidence.quote` is non-null and its normalized form appears in
   the normalized patch text of the cited file (the same
   normalization class as the Phase-08 matcher repair);
4. `file` exists in the diff and `line` (if present) falls inside a
   hunk of that file.

The downgrade is deterministic and recorded; the assessment is then
recomputed by the existing parser semantics (no blocking findings ->
CLEAR). V1 outputs (no `evidence` field) degrade gracefully: blocking
findings without evidence metadata are downgraded — that is the
fail-closed direction.

### Why quote-in-patch is the load-bearing check

C13's six B1 blockers cite `publish.yml` (a real in-diff file), so
citation-existence alone stops nothing; but the HARM in every one of
them rests on text that exists nowhere in the diff ("unreviewed PR
head code is built and published" — the called workflow; "if it
checks out the PR head ref"). Requiring a verbatim in-diff quote for
the harm-bearing claim severs exactly that chain. C3's "wired into
CI" and C12's "callers catching OriginError" fail the same way. The
true positives all quote in-diff text naturally (M3's `-mtime` line,
M16's `except Exception: pass` / `{"ok": True`, M12's except clause).

### Honest limits and replay requirement before preregistration

- V1 records carry no evidence fields, so a full replay is impossible;
  the pre-preregistration step must build a **quote-simulation
  replay**: extract candidate quotes from finding comments, match
  them against the cited patches, and report what fraction of
  Stage-A/B1 control blockers would have been downgraded and what
  fraction of true-positive detections would survive. (The Phase-08
  matcher replay is the template; the B1 low/high and Stage-A
  low/high/max frozen records are the corpus.)
- Prompt-side changes (asking the model to emit evidence metadata)
  are reviewer-intelligence changes; the parser gate is an engine-
  contract change (`ReviewResult` v2). Both land only through the
  standard feature/phase + preregistration workflow, never ad hoc.
- A measured qualification loop (N=5, >=4/5, paired controls,
  preregistered thresholds) remains the only path to any GATING
  promotion.

## 3. What Phase 08 shipped (context for the above)

- Accounting repair: summary spend derived from `records.jsonl`
  (all attempts); B1's under-reporting (~3x) is structurally fixed;
  ledger remains the ceiling authority.
- Matcher hardening: normalization + broadened semantic families;
  deterministic replay over frozen records shows exactly three
  run-level detection flips (all False -> True: M16 low run1, M4 low
  run2, M4 high run2), zero Stage-A movement, controls unchanged
  (`eval/evidence/matcher-repair-replay-2026-09-21/`).
- C12/M12 fixture contract clarification; oracle identity bumped to
  `cc12830159c251dc`; old M12 measurements are not perfectly
  apples-to-apples with future ones (fixture input changed; the
  Stage-A/B1 records themselves are frozen and unchanged).
