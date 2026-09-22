# Offline v2.1 claim-route replay protocol

Design-study protocol, 2026-09-22. Not a promotion preregistration and
not an implementation approval. It fixes the route taxonomy, the
classification precedence, and the admission rules **before** the
result is recorded; `RESULTS.md` reports what the fixed rules produce
over frozen inputs. No rule may be edited after results are recorded;
a changed rule is a new protocol.

## Inputs (identical to Phase 15)

- the frozen 414-record Phase-09 population (276 blocking findings),
  fail-closed;
- the five sha-linked regression cases in
  `eval/evidence/v2-declaration-regression-freeze-2026-09-22/`;
- oracle identity `117b4164e5446f50` (must not move);
- the Phase-15 structural witness registry **verbatim, unmodified**
  (`eval/v21_replay.py.predicate_names`, cited-file scoped).

Zero provider calls; no schema, rubric, prompt, corpus, or parser
change.

## Route taxonomy

Every blocker is assigned exactly one claim route, by precedence
(first match wins; precedence is fixed to keep verifiable in-diff
claims from being masked by external vocabulary):

1. `out_of_diff` — the cited file is not in the diff. (R4)
2. `contract_contradiction` — the finding's comment carries
   contract-reference language AND contradiction language, using the
   Phase-09 simulator's own `CONTRACT_REF_RE` / `CONTRADICTION_RE`.
   (R2)
3. `witnessed_behavior` — at least one Phase-15 structural witness
   matches the cited file's patch and the comment. (R1-w)
4. `external_fact` — the comment references an external actor or
   resource outside the diff (`secret|credential|token\b|registry|
   publish|exfiltrat|leak|attacker|untrusted|pull_request_target|
   reusable workflow|deploy|privileg`) but no witness matched. (R3)
5. `unwitnessed_behavior` — an in-diff claim with neither contract
   signature, witness, nor external vocabulary. (R1-u)

## Admission rules (fixed)

All admission additionally requires the Phase-09 G1 quote gate
(quoted span in the cited patch); for the frozen five, the machine
admission status in the frozen `expected_result` stands in for the
quote gate, unchanged from Phase 15.

| route | offline admission |
|---|---|
| out_of_diff | never (already v2 behavior) |
| contract_contradiction | only with ≥1 registry witness acting as relation verifier |
| witnessed_behavior | yes (the witness is the independent check) |
| external_fact | never offline — requires a pinned external fact plus a mechanically bounded consequence; none exists in this replay |
| unwitnessed_behavior | never offline — requires static/execution witness infrastructure not present in this replay |

## Required reported measures

1. gate-level role table (quote-only vs Phase-15 closed-world vs
   route-typed) over all three roles;
2. the internal consistency identity: route-typed admission must
   equal Phase-15 closed-world admission exactly (both are
   "quote + registry witness"; routes only explain, never widen);
3. the route × role decomposition, in particular of the
   closed-world-refused true positives — this locates which
   verification infrastructure would recover recall;
4. the frozen five-case projection with each case's route and refusal
   or admission reason.

## Non-goals

No threshold selects a winner; no candidate is promoted; no schema or
prompt change is authorized; the external-fact route's future
infrastructure (pinned facts, bounded consequence checks) is research
specification only.
