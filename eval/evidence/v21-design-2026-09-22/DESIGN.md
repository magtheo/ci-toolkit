# v2.1 semantic-entailment boundary: offline design and replay

Status: **design evidence only, 2026-09-22.** No parser, schema,
rubric, prompt, corpus, or provider change is proposed by this
artifact. The current v2 boundary remains default-OFF and
non-promotable.

## Research question

> What independently checkable information can authorize blocking
> severity when quote existence alone does not establish that the
> claimed harm follows from the quote?

The frozen v2 trial established that quote presence is necessary but
not sufficient:

- C11: real quote -> fabricated semantic contradiction;
- M3: correct contradiction -> quote carries only context;
- M13: real external fact -> unsupported extrapolation into unseen
  workflow behavior;
- C12/M12: honest uncertainty and an invalid contiguous quote were
  correctly downgraded.

The five inputs are pinned under
`eval/evidence/v2-declaration-regression-freeze-2026-09-22/` before
any design work. They are not a training set and must not be silently
optimized away.

## Candidate mechanisms

| Candidate | Independently checkable part | C11 | M3 | M13 | Limitation |
|---|---|---|---|---|---|
| A. Typed quote roles | `contract_quote` and `implementation_quote` both occur in the cited patch | still unresolved: both real quotes can support a false inference | detects context-only current quote | not applicable | presence of two quotes is not entailment |
| B. Executable falsification | a sandbox runs a declared reproducer / assertion against the shown change | can refute the claimed exit-status contradiction | potentially testable | cannot establish unseen workflow behavior | model-supplied execution is a security and reliability design problem |
| C. Static/tool verifier | a dedicated analyzer proves a narrow relation (shell control flow, action semantics, AST relation) | feasible for the shell wrapper class | uncertain for date semantics | can refuse unseen behavior | only covers tool-supported classes |
| D. Typed claim routes | behavioral atoms require execution/static route; external atoms require pinned spec route; prose quote is not a behavior route | routes false behavior claim to a verifier | routes contradiction to two-sided evidence | routes unseen actor to refusal | route typing needs a closed taxonomy |
| E. Second-model refuter | a separate generation attempts a counterexample | empirical only | empirical only | empirical only | correlated model error is not independent verification; not replayable offline |
| F. Closed-world predicates | a known patch predicate, independently checked, authorizes a known harm class | only if predicate models the contract relation correctly | can preserve known date mismatch | refuses absent predicate | deliberately sacrifices coverage |

Candidates A, D, and F are replayed as far as frozen offline inputs
permit. B/C/E are specifications for future research, not claims of
current capability.

## Replay candidate: F, closed-world predicate registry

`eval/v21_replay.py` implements a deliberately small registry and
requires both the existing Phase-09 quoted-span admission and a
matching structural predicate. Current predicates recognize only:

- parsed-date freshness contract implemented with filesystem mtime;
- hard-coded success status after discarded command outcome;
- caught parse/origin failure returning fallback content;
- swallowed generic exception followed by a success response;
- mutable action reference in a workflow.

This is **not proposed as v2.1**. It is a falsifiable lower-bound
candidate: if its coverage loss is unacceptable, a verifier-only
strategy cannot be the whole answer. If it fails C11/M13, quote-plus-
predicate is still not enough.

## Preregistered evaluation criteria for this design replay

Against the five frozen cases, a candidate is useful only if it:

1. refuses C11 and M13 (confirmed declaration failures);
2. preserves M3's real defect without treating its context-only quote
   as semantic proof;
3. preserves C12 and M12 downgrade behavior.

Against the frozen 414-record Phase-09 corpus, report rather than
hide all three role counts: control blockers, oracle-matching true
positive detections, and positive extra blockers. No post-hoc
threshold promotes a candidate in this phase.

## Design boundary

The replay may identify mechanisms worth a later v2.1
preregistration. It cannot authorize implementation, a provider run,
promotion, B1.1, or B2. Any implementation must name the frozen cases
it intentionally changes and amend their regression expectations in a
reviewed PR.
