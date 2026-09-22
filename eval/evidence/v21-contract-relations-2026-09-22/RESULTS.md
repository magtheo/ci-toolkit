# Contract-relation verifier study result

Method: `python3 eval/v21_contract_relations.py` under `PROTOCOL.md`
(rules fixed before recording). Oracle `117b4164e5446f50` unchanged.
Inputs: frozen 414-record / 276-blocker Phase-09 population plus the
five sha-linked regression cases. Zero provider calls.

## Headline

Six of seven preregistered relations survived the pair test; one
FAILED exactly as the protocol demanded. The candidate gate recovers
**24 oracle-matching TP rows (+83% contract-route recall, 29 → 53 of
68)** with **zero control admissions (0/77 corpus-wide)** and **zero
new extra-blocker admissions**.

| gate (contract route only) | controls | oracle-matching TPs | extras |
|---|---:|---:|---:|
| Phase-16 baseline | 0 / 35 | 29 / 68 | 1 / 22 |
| + eligible relations | 0 / 35 | **53 / 68** | 1 / 22 |

The executable candidate gate preserves **all** Phase-16 admissions
before adding eligible contract relations. Therefore the corresponding
corpus-wide gate is **0/77 controls, 50 → 74 of 165 oracle-matching
TPs, and 2/34 extra blockers unchanged**. The 21 admitted
`witnessed_behavior` TPs and their one admitted extra remain untouched
by this study. Frozen-five outcomes are unchanged: C11, M13, C12, M12
refused; M3 admitted via the existing registry witness.

## Per-relation pair test

| relation | TPs admitted (fixtures) | controls | extras | verdict |
|---|---|---:|---:|---|
| `pinned_sha_demoted_to_branch` | 24 (M2) | 0 | 0 | eligible |
| `preserved_claim_vs_dropped_call_result` | 11 (M7) | 0 | 1 (M7) | eligible |
| `consume_before_validate_ordering` | 13 (M8) | 0 | 0 | eligible |
| `doc_contract_prefix_unanchored_match` | 9 (M10) | **3 (C10)** | 1 | **FAILED** |
| `secret_logged_by_echo` | 9 (M14) | 0 | 0 | eligible |
| `doc_self_contradiction` | 11 (M17, M18) | 0 | 0 | eligible |
| `jsonl_format_vs_unslurped_jq` | 7 (M6) | 0 | 0 | eligible |

TP counts are rows on which the relation fires; candidate admission
additionally requires the quote gate and the contract route, yielding
24 newly admitted rows: M18 7, M7 7, M8 5, M17 2, M6 2, M2 1.

## The FAILED relation is the study's most instructive result

`doc_contract_prefix_unanchored_match` was preregistered to catch
M10's unanchored `re.search(r"feature/", ref)` against the docstring
"Only refs under feature/ may run the privileged lane". But its
wording listed `re.match` among "unanchored" matching functions — and
**C10 is M10's near-miss twin**: same docstring, same file, with the
CORRECT anchored `re.match(r"feature/", ref)`. The relation fires on
both. The pair test caught what design inspection missed: a relation
worded loosely enough to admit the true positive also admits the
control that differs by exactly the anchor semantics.

Per protocol the relation is recorded FAILED and excluded — not
patched. A future protocol may preregister the precise amendment
(`search`/`find`/`in` only; `re.match` is anchored by definition),
which mechanically separates M10 from C10; that amendment is NOT
evaluated here. This is the AGENTS pair-integrity rule working as
designed: detection indistinguishable from over-triggering is not a
capability.

## Residual refusals (15 contract-route TPs still refused)

M12 4, M8 4, M4 2, M7 1, M14 1, M2 1, M10 1, M18 1 — quote-gate
failures on individual rows, M4's documented class exclusion, and the
FAILED M10 relation. Note the route interplay: most M2 TP rows claim
secret access in vocabulary that routes them `external_fact` under
the frozen Phase-16 precedence, where new relations do not apply; only
1 contract-routed M2 row was recovered.

## Honesty ledger

- Relations were designed by inspecting the frozen corpus; the pair
  test on the same corpus is necessary, not sufficient (protocol).
  Generalization requires unseen validation and ultimately a live
  trial.
- Two jq-regex implementation repairs were made to match preregistered
  semantics (no control impact; eligibility mechanically rechecked):
  acceptance of the shell `if ! jq` guard prefix and acceptance of
  `$VAR` forms. No relation semantics were changed. The M10 wording defect was NOT repaired —
  it is a semantic defect and was recorded FAILED.
- Extras: `preserved_claim_vs_dropped_call_result` fires on one M7
  extra blocker, which the candidate gate does not admit (quote/route
  conditions fail). Reported, not gated.
- No threshold, promotion, or implementation is authorized by this
  study.
