# Track 1 failure taxonomy (T1.1) — 2026-09-04

Derived from frozen evidence only, before any T1.3 mechanism design
(problem surface first; the taxonomy must not be shaped around a
candidate fix). Sources:

- `eval/baseline-2026-08-30.json` (per-fixture false-block counts,
  assessments) + `eval/state-log.md` (baseline entry);
- probe bundle `eval/evidence/phase4-discrimination-probe-2026-08-30/`
  — narrative sources: runs 01 (old rubric, haiku) and 05 (r1,
  sonnet) carry full per-finding comments;
- ROADMAP appendix A (#14 self-review false positives).

No model spend was needed: probe narratives + appendix A cover every
baseline false-blocker family. Spend for T1.1: 0 calls.

## Families

A false blocker is classified by **why blocking is wrong**, not by
topic. Primary family = the load-bearing failure; secondaries noted
per exemplar.

### 1. `hallucinated-fact`

A confident, checkable claim about tool/language/framework
semantics or diff content that is **false**, used as blocking
grounds. Includes hallucinated absence (guard present, claimed
missing) and inverted conclusions from true premises.

Exemplars (frozen):

- **C3** — narrative: "`find -mtime -30` matches files modified
  *within* the last 30 days … Logic is inverted" (run 01). The
  premise is true, the conclusion false: the code does exactly what
  its contract states. Sonnet variant (run 05): "Unreachable code:
  … `set -e` terminates the script before reaching" — also false
  (command lists in `if` conditions do not trip `set -e`).
- **C8** — "registers a new listener every time the widget is
  rebuilt" (run 01): false — `initState` runs once per `State`;
  "if initState runs multiple times (widget rebuild)" (run 05)
  repeats the false lifecycle premise.
- **C1/C2 (secondary)** — "without explicit trust boundary
  documentation or pinning" (run 01): pinning is present in the
  same diff (full SHA, both layers).
- **Appendix A** — inverted conclusion from a true premise;
  hallucinated absence; asserted test gap without reading the tests.

### 2. `speculative-consequence`

Blocking grounded not in a present defect but in a **conditional
harm chain** about what could happen if some external actor,
compromise, or future misuse occurs.

Exemplars (frozen):

- **C1/C2/M1** — "If the external workflow or its dependencies are
  compromised …" (run 01); "If a malicious P[R] …" chains.
- **C6** — "The condition `! jq -se …` negates … exit 0 … In CI
  pipelines, exit 0 signals success … if the inte[gration] …"
  (run 01): narrates the documented intended behavior, then blocks
  on a hypothetical downstream misuse.

### 3. `risk-boilerplate`

Guard-blind security-vocabulary recital: generic threat text fired
by pattern vocabulary (`pull_request_target`, secrets, external
refs) that **does not engage the guards present in the same diff**
(fork skip, SHA pins, least-privilege permissions). Recurrent shape
per the probe README: immutable full-SHA pinning flagged as a
blocking security defect with floating refs recommended as the
"fix" — the recommendation would make the code less safe.

Exemplars (frozen): **C1, C2, M1** (contamination), and the
floating-refs-recommendation class (probe README, runs 01/05).

### 4. `severity-inflation`

Advisory-grade material — style, naming, maintenance preferences,
documented design choices a reviewer disagrees with — marked
**blocking**.

Exemplars (frozen):

- **C2 (secondary)** — "Hardcoded commit SHA … creates a
  maintenance burden" (run 01): the pinning is the security design.
- **C3 (secondary)** — "Missing failure signal: script prints STALE
  but continues with exit 0" (run 05): the exit-0 status contract
  is documented in the fixture; a design disagreement.
- **C8 (secondary)** — listener hygiene / disposal as blocking even
  under the (false) premise.
- **M7 extras** — "return value not captured … must be consumed";
  "No error handling present" (run 01): hygiene at blocking
  severity contaminating a detected real defect.

### 5. `absolute-consistency`

Same-diff claim-vs-code consistency around unqualified absolutes:
either the miss (M5 — unqualified absolute not flagged) or the
false block (C5 — qualified claim blocked under a consistency rule,
5/5 across three wordings and two models; hyper-literal
subset/superset readings; wording changed the narrative, never the
verdict — probe runs 02–05).

Exemplars (frozen): **M5 / C5**.

## Unclassified (retained as such)

- **M4/C4, M7/C7** — no baseline false-block family: C4/C7 are the
  GATING-clean controls; M4 is an out-of-scope known miss
  (cross-file, owner Stage 3); M7 is detected-with-contamination
  whose extras classify as `severity-inflation` secondaries, but
  the pair's control passes — no pair-level axis to tag.
- Baseline **M3 false-clear side** (0/3 detection at baseline for
  M4/M5/M6 only; M3 is detected) — nothing to classify beyond the
  C3 control family.

## Fixture realism lesson (recorded for T1.4 authoring)

Sonnet (probe run 05) blocked C1 partly because the fixture SHA
`0123…4567` "appears to be a placeholder (repeating hex pattern)".
Placeholder-looking artifacts attract blocking that real diffs
would not. All new fixtures use realistic 40-hex SHAs; T1.4 holdout
authoring must do the same.

## Coverage after T1.1

| family | baseline tagged pairs | new frozen pairs (this stage) |
| --- | --- | --- |
| `hallucinated-fact` | M3/C3, M8/C8 | M9/C9 (jq -e semantics), M10/C10 (re.match anchoring) |
| `speculative-consequence` | M6/C6 | M11/C11 (exit-0 status contract), M12/C12 (stale-on-error fallback) |
| `risk-boilerplate` | M1/C1, M2/C2 | M13/C13 (publish workflow), M14/C14 (secret transport) |
| `severity-inflation` | — (secondaries only) | M15/C15 (validator style vs typo), M16/C16 (best-effort vs fabricated success) |
| `absolute-consistency` | M5/C5 | M17/C17 (caching docs), M18/C18 (deployment docs) |

Deterministic enforcement: `FAMILIES` is declared in
`eval/run_corpus.py` (inside the oracle hash — a family change is
an oracle change); fixtures carry a pair-consistent `family` field;
tests pin ≥2 new pairs per family; and paired inputs MUST differ
(loader guard) — identical positive/control inputs mean the pair
measures nothing. That last guard was added after T1.1 review
caught four silent template failures (M10/M12 lost their defects,
C17/C18 carried them); M13 was likewise reduced to a single
semantic delta vs C13 (floating tag vs pinned SHA) so reviewers are
not scored against unmodeled blockers.

Oracle consequence: corpus + states growth changes `oracle_version`
(fail closed, per plan Deviation 4). New fixtures enter as
`KNOWN_GAP`; no state promotions happen in T1.1.
