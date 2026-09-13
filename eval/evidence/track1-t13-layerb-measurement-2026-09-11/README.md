# 20d measurement — layer (b) support contract: **FAIL**

Governed run of the frozen layer (b) measurement
(`freeze.json` rev 2, subject `e87b6e4`, oracle `cb6870c5a4c635b2`,
corpus `72035a00b8db828d`). 360/360 calls served exactly once
(180 haiku + 180 sonnet, N=5 × 36 fixtures, temp 0.2, max_tokens
2000). Spend **$3.06** upper-bound (list pricing) against the $3.50
cap. Raw reports/logs are byte-immutable (`36106f3`); this bundle is
derived deterministically by `derive.py` (no model calls).

## Verdict

**The layer (b) support contract is REJECTED under the frozen
lifecycle.** Four of five success criteria fail, including both hard
invariants. Per the frozen `interpretation_on_pass`: reviewer-side
revert PRs (engine policy first, rubric second) follow this bundle.

## Causal summary

> Layer (b) improved apparent specificity, but primarily through
> broad attenuation rather than better discrimination. Valid citation
> presence was insufficient to distinguish supported defects from
> unsupported conclusions: false-blocking narratives frequently
> supplied valid matching citations despite remaining semantically
> unsupported, while genuine defect findings were disproportionately
> demoted for missing/non-matching support. The mechanism therefore
> violated the frozen sensitivity and GATING invariants and is
> rejected.

This is the design's own §2.7/§3 falsifiable risk, measured:
citation presence enforces nothing about relevance or entailment.

## Frozen-criterion results

| # | criterion | result | measured |
|---|---|---|---|
| 1 | zero GATING, both profiles | **FAIL** | sonnet C7: 4/5 ISSUES_FOUND, 4 FBs (see `gating_violations`) |
| 2 | Deviation 6 floors | **FAIL** | **19 violations** (list below); haiku aggregate **2/90** vs floor 51; sonnet **50/90** vs 66 |
| 3 | spec-family ≤ 53/50/103 | **FAIL** | sonnet speculative-consequence FBs = 60 (cap 50); aggregate 60 (cap 103) |
| 4 | control FBs ≤ 78/112 | pass | haiku 0, sonnet 67 — attenuation artifact, see causal summary |
| 5 | sonnet C7 clean | **FAIL** | entailed by #1 |

## The 19 floor violations (per-positive deltas)

haiku: M1 0/5 (−5), M2 0/5 (−5), M3 0/5 (−5), M7 0/5 (−5), M8 1/5
(−4), M9 0/1 (−1), M10 1/5 (−4), M11 0/5 (−5), M12 0/5 (−5), M14
0/5 (−5), M16 0/5 (−5) · sonnet: M1 4/5 (−1), M9 2/5 (−3), M10 0/5
(−5), M12 2/5 (−3), M13 0/1 (−1), M16 4/5 (−1), M17 **0/5 (−5, hard
invariant, third consecutive iteration)**, M18 0/5 (−5). Full table:
`derived-metrics.json` → `floor_violations`.

Haiku detection collapsed from the 51/90 floor to 2/90 — the
citation requirement did not make haiku more accurate; it stopped
haiku from blocking almost anything (218 `support_missing` demotions).

## Mechanism telemetry (360 calls)

| signal | value |
|---|---|
| demotions (post-policy, machine reason in comment) | **336** |
| — support_missing (no/empty/malformed support) | 218 (haiku 218, sonnet 0) |
| — support_not_found (non-vacuous quotes, none matched) | 116 (all sonnet) |
| — support_vacuous | 2 |
| surviving engine-annotated support | 194 annotations (diff 165 / body 22 / title 7; haiku+sonnet totals per profile in metrics) |
| INCONCLUSIVE | 8 (5 sonnet / 3 haiku — all pre-policy JSON-decode/schema; `inconclusive-audit.json`) |

The C7 false blockers are the decisive specimen: speculative
"scope violation / testability" narratives carrying perfectly
matched, non-vacuous, engine-annotated citations (e.g. the PR-body
quote "Purely mechanical port; behavior-preserving." resolved via
`engine_match {kind: body}`). The validator did exactly what it was
built to do; what it certified was not discrimination.

## False-blocker family coding (123 sonnet FBs, 0 haiku)

`narrative-coding.jsonl`, rule table v1 following the frozen
iteration-2 precedents, fail-closed (0 UNMATCHED):

| family | count |
|---|---|
| speculative-consequence | 60 |
| hallucinated-fact | 28 |
| absolute-consistency | 13 |
| risk-boilerplate | 12 |
| severity-inflation | 9 |
| genuine-defect-unmatched (coding note, not a taxonomy family) | 1 |

The single `genuine-defect-unmatched` row (sonnet M11, output/exit-
code suppression phrased past the needles) continues the #40
reclassification precedent — it marks an oracle matching gap, not a
model win.

## Spend, calls, incident log

| profile | calls | prompt tok | completion tok | cost (upper bound) |
|---|---|---|---|---|
| haiku-4.5 | 180 | 257,835 | 84,460 | $0.68 |
| sonnet-4.5 | 180 | 257,835 | 107,305 | $2.38 |
| **total** | **360** | 515,670 | 191,765 | **$3.06 / $3.50 cap** |

1. Attempt 1: blocked **at call 1** — OpenRouter http 403, key weekly
   limit. Zero governed calls served; log preserved verbatim in
   commit `dd59604`.
2. Authorization continuity: the directing human confirmed the key
   reset and explicitly re-authorized the identical frozen run
   against head `dd59604`. No frozen input changed between
   authorizations.
3. Attempt 2: 360/360 served; sonnet process exit 1 is the harness
   policy-failure signal (report complete; no transport errors).

## Disposition

Keep/revert is not a judgment call under the frozen lifecycle: hard
invariants failed ⇒ revert. Sequence (human-directed): merge this
negative-evidence bundle → revert engine/parse support policy
(reviewer-side) → revert the 20c rubric support citation (rubric.md
only) → exact-restoration check against the pre-layer-(b) subject →
choose the next T1.3 mechanism from this measured evidence. Layer (b)
is recorded as **measured insufficient**: forcing citation presence
does not separate unsupported conclusions from supported defects.
