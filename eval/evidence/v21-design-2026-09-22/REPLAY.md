# v2.1 offline replay result

Method: `python3 eval/v21_replay.py` at oracle
`117b4164e5446f50`. Inputs are the 276 blocking findings drawn from

## Phase-09 corpus result

| role | quote-only (Phase-09 G1) | closed-world predicates | change |
|---|---:|---:|---:|
| control blockers | 27 / 77 | 0 / 77 | -27 |
| oracle-matching true-positive detections | 111 / 165 | 50 / 165 | -61 |
| positive extra blockers | 7 / 34 | 2 / 34 | -5 |

The registry removes every historical quote-gate control survivor,
severely.

## Frozen five-case projection

| case | quote-only | predicate registry | interpretation |
|---|---|---|---|
| C11 fabricated contradiction | admits | refuses | no registered predicate proves the claimed contract violation |
| M3 context-only quote | admits | admits (`parsed_date_vs_mtime`) | predicate independently sees both contract/date and `-mtime` structure; current quote remains insufficient by itself |
| M13 external extrapolation | admits | refuses | no in-diff predicate establishes the unseen reusable-workflow publication harm |
| C12 honest uncertainty downgrade | refuses | refuses | good control preserved |
| M12 non-contiguous quote downgrade | refuses | refuses | good control preserved (the record's separate honest survivor is deliberately not the target of this control projection) |

## Conclusion

The replay distinguishes all three confirmed declaration-failure
patterns **only by trading away 61/165 historical oracle-matching

1. quote existence plus a narrow structural witness is materially
   safer than quote existence alone;
2. that witness registry cannot be the whole v2.1 answer without
   unacceptable coverage loss.

The next design must combine typed claim routes with an independently
verified relation appropriate to the route. Typed
`contract_quote`/`implementation_quote` can correct M3's evidence
role, but C11 shows it cannot prove a contradiction by itself.
Executable falsification and dedicated static/tool verifiers remain
research candidates, not approved implementations.
