# Phase 22C — m4rel implementation (in-sample only)

**Status: implemented against the frozen 22B contract using corpus /
in-sample development material only. The fresh holdout was NOT
executed against and remains sealed for the separately reviewed
qualification phase. No preservation authority is granted; nothing
outside `eval/v21_m4_relation.py` + this evidence + tests changed;
fixtures, labels, thresholds, target identities, and semantic scope
are byte-untouched.**

## What was built

`eval/v21_m4_relation.py` (`m4rel`, relation
`unsubstantiated_absolute_docstring_claim`, implementation
`22C-impl-v1`) — a deterministic detector with two entry points:

- `detect(fixture)` — runs on PR content only (title, body, added
  docstring/comment text). Returns a blocking finding per claimed
  file with the quoted clause and its out-of-diff referents.
- `covers(finding, fixture)` — row-level coverage mapping used by the
  frozen gates: same file AND the row's comment shares a 6-token window with the
  detected claim clause for normal claims. If either side is shorter
  than six tokens, linkage falls back only as far as necessary, with
  a 3-token minimum. The row must still be *about the detected claim*,
  not merely on the same file. `file_matches()` reports the
  looser same-file diagnostic separately; it is never gate input.

## The frozen semantic boundary, lexically operationalized

A docstring clause produces a finding only when ALL hold:

1. It carries a quantifying exclusivity marker (all / always / never /
   only / every / none / no other / exactly-N / guarantees / …) and
   **no** disclaimer or hedge marker ("does not define", "outside
   this", "belongs to", "defined by", "advisory", "typically",
   "may", …). Self-scoped and hedged clauses are never claims.
2. It names an **out-of-diff actor** (orchestrator, scheduler,
   watcher, …) that none of the change's defined symbols provide.
   Generic in-diff absolutes ("all parse failures are raised as
   ParseError") name no external actor and stay out of scope.
3. Nothing in the change **substantiates** the claim: no other diff
   file imports/consumes the claimed module (the C3
   `CLI_ENTRYPOINTS` substantiation pattern is respected).
4. The change's stated purpose is **documentation** (title/body).
5. Requirement statements ("must not be silently skipped") are not
   exclusivity claims — the marker list excludes them by design.

Per the frozen semantics note, the marker vocabulary is illustrative
recall; conditions 1–5 together are the detector. The implementation
is therefore a **lexically operationalized semantic candidate**, not
vocabulary-independent semantic understanding: marker, actor,
disclaimer, and hedge vocabularies are combined with structural checks. Runtime sees
fixture content only — no oracle roles, no record indexing. The
module imports nothing from the frozen Phase-17 verifier (QG3).

## In-sample results (corpus development material)

| Gate | Result | Requirement |
| --- | --- | --- |
| Targets (P-M4) | **2/2 covered** (stage-a-max r66, b1-low r44) | 2/2 |
| Corpus controls | **0/77 fired** | 0 |
| Extras | **0/34 claim-linked** (4 same-file M4 extras reported as file-match-only diagnostics) | recorded; zero-preserved |
| Family non-target TPs | 5/5 covered — recorded, permitted | recorded |
| `detect()` fired fixture set | exactly `{M4}` across all 36 corpus fixtures | — |

Seven development near-miss units (authored for 22C in new domains,
inline in the test module — holdout content was not reused) all pass:
requirement-statement, generic in-diff absolute, self-scoped
disclaimer, hedged actor claim, in-diff-substantiated consumer,
unsupported actor claim (fires), and no-documentation-purpose.

## Holdout seal

`eval/evidence/v21-m4rel-holdout-2026-09-23/`:
**executions during 22C = 0.** Development used corpus material and
the seven inline dev units only; no holdout fixture was read for
detection tuning and no holdout id is embedded in the evidence.
First sanctioned execution: the qualification phase, against the
frozen thresholds (2/2 · 0/77 · 0/30 existing controls · 6/6 · 0/6 ·
standing guards), feeding a human-reviewed record before any adoption
decision.

**Qualification interpretation:** the holdout is preregistered and
execution-sealed, but not blind to the implementation author. The same
agent authored it before implementation, and review confirmed that all
positive actor lexemes are represented in the candidate's `ACTORS`
vocabulary. A future PASS is therefore preregistered validation under
the frozen scope—not proof of vocabulary-independent or fully blind
generalization. QG5 human review remains responsible for that limit.

## Non-goals (unchanged)

No preservation-authority grant, no adoption preregistration, no
GATING, no deployed change, no edits to frozen modules/fixtures/
routes/parser/oracle, no eval/fixtures additions. The oracle and the
frozen verifier hashes are re-verified in tests.
