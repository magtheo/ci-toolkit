# Phase 22D — m4rel qualification results

**Verdict: SUCCESS — all six gates green.**

> This is **preregistered validation against the frozen holdout**, not
> vocabulary-independent generalization: the holdout was authored
> before implementation but is not blind to the implementation author
> (all six positive actor terms appear in the detector's ACTORS
> vocabulary). A PASS produces a qualification record only —
> **no preservation authority is granted**; adoption is a separate,
> human-decided QG5 step.

## Execution discipline

- **Authorization**: this run is bound to
  `PHASE_TRANSITION.json`
  (sha256 `b3eb2a4c8d9fe2a3353ec00cb423cc051abc96dda886412e227c7678b8f1a628`)
  — qualification-execution authorized; adoption, preservation
  authority, and GATING remain unauthorized and human-decided. The
  report embeds the transition's hash and verifies its pins before
  any detection.
- Pins (module sha first, then 22B contract, both holdout manifests,
  18D report, oracle, frozen verifier) verified **before any
  detection ran**; fresh-holdout manifest integrity verified before
  its execution.
- The 22B holdout was executed once as the sanctioned observation,
  then re-executed three times according to `execution-log.jsonl`.
  The detector hash is the same throughout the logged runs. **Original
  execution 1 and execution 4 reports are both retained**, with a
  separately hash-pinned review-annotated final report. Their 12
  fixture-level outputs are mechanically verified identical. Runs 2–3
  are logged but their report bytes were not preserved, so their
  fixture-level identities **cannot be independently verified** from
  this repository. Log entries 1–2 were retrospectively reconstructed;
  the log alone is not tamper-evident proof of execution order.
  No detector change is recorded after observation.

## Evaluator correction (disclosed, mechanically cross-checked)

Execution 1 recorded **HALT** with all fixture-level results correct:
the G5 aggregation had inverted the control-correctness predicate
(`c_ok == 0` instead of `c_ok == len(controls)`), failing six
correctly-refused controls. The first raw report is preserved
unmodified as `qualification-report.execution-1.json`
(sha256 `b368b5a4dcb7dbd9113e60cfbd514c8e17447722e60ca8748beae85620a13aa2`,
verdict HALT). The official report embeds a cross-check for
the retained **first versus run-4 versus reviewed-final** fixture
outputs and pins the
detector bytes. It does **not** independently establish intermediate
run-2/run-3 outputs. The
detector (`eval/v21_m4_relation.py`,
sha256 `1a01d8ff6f15fd050eb290da4f20a2d99dacb59ea183b0dc6b803c6004139596`)
never changed.

The original run-4 report is preserved separately as
`qualification-report.execution-4.json`
(sha256 `a4ebaabac2dea4c662541f433aeb580bd91d301e45dde576ce3688eb4a422c1f`),
which is the digest recorded in the run-4 execution log. The
review-annotated `qualification-report.json` is a distinct artifact;
its only substantive amendment is the explicit scope of the
cross-execution provenance claim. The preserved raw reports and
their fixture-level results have not been edited.

## Gates

| Gate | Required | Actual | Verdict |
| --- | --- | --- | --- |
| G1 corpus targets | 2/2 (stage-a-max r66, b1-low r44) | 2/2 | PASS |
| G2 corpus controls | 0 fired of 77 | 0 | PASS |
| G3 extras | 34 recorded; zero claim-linked | 0 claim-linked (4 same-file diagnostics, recorded) | PASS |
| G4 existing holdout controls | 0 fired of 30 | 0 (probe records carry no title/body — substantive signal remains the 0/77 corpus gate) | PASS |
| G5 fresh holdout (single sanctioned execution) | 6/6 positives · 0/6 controls | 6/6 · 0/6 | PASS |
| G6 standing guards | frozen set | frozen set | PASS |

## Fixture-level fresh-holdout results (exact evaluator output)

| Fixture | Label | Fired | Files |
| --- | --- | --- | --- |
| m4h-P1 | ADMITS | yes | jobs/priority.py |
| m4h-P2 | ADMITS | yes | telemetry/sampling.py |
| m4h-P3 | ADMITS | yes | cli/paths.py |
| m4h-P4 | ADMITS | yes | queue/markers.py |
| m4h-P5 | ADMITS | yes | watcher/debounce.py |
| m4h-P6 | ADMITS | yes | ops/restart.py |
| m4h-C1 | REFUSES | no | — |
| m4h-C2 | REFUSES | no | — |
| m4h-C3 | REFUSES | no | — |
| m4h-C4 | REFUSES | no | — |
| m4h-C5 | REFUSES | no | — |
| m4h-C6 | REFUSES | no | — |

Full machine-readable detail (every pin, every gate, per-fixture
claim clauses and actors, extras and family ids):
`qualification-report.json`
(sha256 `fec590e9f822880a4e82aaa281f1ad6c0942559eaa55dbc64c6ddab08a11934c`).

## Published-record immutability

The evaluator's completed lifecycle is **read-only**. Once
`qualification-report.json` exists, `evaluate()` checks its exact
SHA256, frozen source pins, the preserved first/run-4 report hashes,
execution-log sequence, and the 22D transition, then returns the
published report **without calling the candidate or touching the
holdout**. It must not overwrite the report or append a fifth run.
The regression test pins all four artifacts before/after
`evaluate()` and makes any call to `detect()` an immediate failure.
The original execution log continues to reference the preserved
raw run-4 bytes, not the separately reviewed report annotation.

## What this record is

The QG5 input for the human adoption decision: m4rel is
qualification-PASS against the 22B-frozen thresholds and material.
It is **not** a preservation-authority grant, not an adoption, not a
GATING activation, and not any deployed change. Per the frozen
failure-handling rule, had any gate failed, the candidate would be
recorded and auto-excluded with no post-hoc tuning.

**STOPPED for human review.**
