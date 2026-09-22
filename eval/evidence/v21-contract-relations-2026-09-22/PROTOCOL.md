# Offline contract-relation verifier study protocol

Design-study protocol, 2026-09-22. Not a promotion, not an
implementation approval, and **not a rubric/prompt/schema change**.
It preregisters seven candidate relation verifiers for the
`contract_contradiction` route, their admission rule, and the paired
evaluation they must survive, before results are recorded.

## Scope and honesty constraints

- Target set: the Phase-16 `contract_contradiction` route — 68
  oracle-matching TPs (39 admitted refused: fixtures M2, M4, M6, M7,
  M8, M10, M14, M17, M18) versus 35 near-miss controls (C2, C3, C4,
  C8, C12, C13, C16) plus 22 extra blockers.
- The relations were **designed by inspecting this frozen corpus**.
  The paired test on the same corpus is therefore a NECESSARY, not
  sufficient, gate; generalization requires future unseen validation
  (ultimately a live trial). Recorded here so no result can be read
  as an out-of-sample claim.
- **Pair discipline (binding):** a relation is kept only if it admits
  ≥1 oracle-matching TP while admitting **zero controls** corpus-wide
  (all 77, not just route-local). Any relation that leaks into any
  control is recorded as **FAILED and excluded** from the candidate
  gate — it is not silently tightened.
- M4 is **out of scope**: the class was excluded from GATING with a
  documented schema-coverage gap (Phase-11 preregistration). No
  relation targets it; M4 TPs are expected to remain refused and
  this is reported, not fixed.
- Hard invariants for the candidate gate: control admissions 0/77
  corpus-wide; frozen-five outcomes unchanged (C11, M13, C12, M12
  refused; M3 admitted); oracle identity `117b4164e5446f50` unmoved;
  quote gate remains mandatory for every admission.

## Admission rule (fixed)

Candidate admission = Phase-16 route admission **OR**
(`route == contract_contradiction` AND quote gate AND ≥1 new relation
verifier below). No other route is touched.

## Candidate relation registry (v1, as designed)

Each relation anchors BOTH the claimed defect family in the finding's
comment (minimal claim vocabulary) and the verifiable structure in the
**cited file's patch only** (same-file rule inherited from Phase 15).
Where a contract side exists it must be found in the patch's doc
region — never taken from the model's assertion.

1. `pinned_sha_demoted_to_branch` — removed 40-hex ref, same file adds
   a mutable branch ref (`uses:…@main|master` or `*_ref: main|master`);
   claim vocab: pin/mutable/supply/`@main`/branch. (M2 class)
2. `preserved_claim_vs_dropped_call_result` — patch claims preserved
   semantics, added I/O call result syntactically discarded (bare
   `urllib.request.urlopen(...)` with no assignment/return);
   claim vocab: preserve/same semantics/contract/discarded/no longer.
   (M7 class)
3. `consume_before_validate_ordering` — added `…state = null` occurs
   before a later `if (…== null) return` guard over the consumed
   value; claim vocab: cleared/consumed/before/race/dropped. (M8
   class; C8's validate-then-consume ordering must not match)
4. `doc_contract_prefix_unanchored_match` — doc region states an
   "only … under <seg>/" prefix contract, code matches `<seg>/`
   unanchored (`re.search`/`match`/`find` without `^`); claim vocab:
   bypass/privileged/substring/anywhere/prefix. (M10 class)
5. `secret_logged_by_echo` — echo/printf/log/print of a variable named
   `*TOKEN|*SECRET|*PASSWORD|*KEY|*CREDENTIAL`; claim vocab:
   leak/credential/token/secret/log. (M14 class)
6. `doc_self_contradiction` — doc region contains BOTH a universal
   claim sentence (`all|every|always|never|only|no human`) AND an
   exception sentence (`bypass|approval|unless|manual`), comment
   claims a contradiction/inconsistency. (M17/M18 class; C12's
   case-differentiated docstring and C13's comment-only
   "contradicts" must not match)
7. `jsonl_format_vs_unslurped_jq` — the patch itself documents JSONL
   production (`jq -c … >>"VAR"`) and a consumer `jq` reads `VAR` with
   an array filter (`.[]`) and no `-s|--slurp`; claim vocab:
   format/input/per line/jq. (M6 class)

## Required reported measures

1. per-relation pairwise table: oracle-matching TPs newly admitted
   (with fixture ids), controls admitted (must be 0), extra blockers
   admitted (reported, not gated);
2. candidate gate table vs Phase-16 baseline over all three roles;
3. frozen-five projection with reasons (invariants above);
4. relations failing the pair test, if any, recorded as FAILED with
   the leaking row;
5. classes that remain unreachable offline (expected: M4 by
   exclusion; any TP class whose contract lives outside the diff).
