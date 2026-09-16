# Pass-1 retrospective rescore of the iteration-4 campaign

**Status: DIAGNOSTIC, NOT BINDING.** Pass-1 behavior was frozen as non-gating telemetry before anyone saw it; this derivation may not be read as a T1.2 result. A binding result requires a freshly frozen campaign against the existing Track-1 criteria.

Zero model calls. Derived deterministically from the byte-frozen raw traces.

## Layer 1 — join integrity (hard prerequisite)

Equivalence proofs: rubric blob and prompt/budget/post functions byte-identical across post-revert HEAD, campaign subject `d1a2ef1`, and #36 subject `4b07246`; request payload shape identical; harness sampling settings identical; digest construction identical. parse_review pass-1 semantics AST-identical (the campaign subject's pass-2 parser additions are off the pass-1 path and were stripped for comparison). A changed result is therefore meaningful as stochastic/provider/model drift, not reviewer-code change.

Join: 360/360 unique (model_id, digest) joins, every trace model_id validated, N=5 everywhere, no ambiguity

## Layer 2 — observed measurements and frozen comparisons

## haiku

| id | kind | det(fixture-level)/floor | FBs | noise | assessment stability | state |
|---|---|---|---|---|---|---|
| C1 | control | - | 7 | 3 | C0/I0/F5 | KNOWN_GAP |
| C10 | control | - | 5 | 2 | C0/I0/F5 | KNOWN_GAP |
| C11 | control | - | 6 | 1 | C0/I0/F5 | KNOWN_GAP |
| C12 | control | - | 17 | 3 | C0/I0/F5 | KNOWN_GAP |
| C13 | control | - | 8 | 1 | C0/I0/F5 | KNOWN_GAP |
| C14 | control | - | 9 | 4 | C0/I0/F5 | KNOWN_GAP |
| C15 | control | - | 0 | 5 | C5/I0/F0 | GATING-capable |
| C16 | control | - | 6 | 10 | C0/I0/F5 | KNOWN_GAP |
| C17 | control | - | 0 | 0 | C5/I0/F0 | GATING-capable |
| C18 | control | - | 0 | 0 | C5/I0/F0 | GATING-capable |
| C2 | control | - | 10 | 3 | C0/I0/F5 | KNOWN_GAP |
| C3 | control | - | 5 | 6 | C0/I0/F5 | KNOWN_GAP |
| C4 | control | - | 0 | 0 | C5/I0/F0 | GATING-capable |
| C5 | control | - | 0 | 2 | C5/I0/F0 | GATING-capable |
| C6 | control | - | 6 | 3 | C0/I0/F5 | KNOWN_GAP |
| C7 | control | - | 2 | 3 | C3/I0/F2 | KNOWN_GAP |
| C8 | control | - | 6 | 6 | C0/I0/F5 | KNOWN_GAP |
| C9 | control | - | 4 | 1 | C0/I3/F2 | KNOWN_GAP |
| M1 | positive | 5/5 | 0 | 2 | C0/I0/F5 | GATING-capable |
| M10 | positive | 5/5 | 0 | 3 | C0/I0/F5 | GATING-capable |
| M11 | positive | 5/5 | 1 | 1 | C0/I0/F5 | KNOWN_GAP |
| M12 | positive | 0/5 | 6 | 6 | C0/I0/F5 | KNOWN_GAP |
| M13 | positive | 0/0 | 9 | 1 | C0/I0/F5 | KNOWN_GAP |
| M14 | positive | 5/5 | 6 | 3 | C0/I0/F5 | KNOWN_GAP |
| M15 | positive | 0/0 | 0 | 4 | C5/I0/F0 | KNOWN_GAP |
| M16 | positive | 0/5 | 3 | 3 | C0/I0/F5 | KNOWN_GAP |
| M17 | positive | 0/0 | 0 | 0 | C5/I0/F0 | KNOWN_GAP |
| M18 | positive | 0/0 | 0 | 2 | C5/I0/F0 | KNOWN_GAP |
| M2 | positive | 5/5 | 0 | 0 | C0/I0/F5 | GATING-capable |
| M3 | positive | 0/5 | 2 | 3 | C0/I0/F5 | KNOWN_GAP |
| M4 | positive | 0/0 | 0 | 1 | C5/I0/F0 | KNOWN_GAP |
| M5 | positive | 0/0 | 0 | 0 | C5/I0/F0 | KNOWN_GAP |
| M6 | positive | 0/0 | 5 | 0 | C0/I0/F5 | KNOWN_GAP |
| M7 | positive | 5/5 | 1 | 5 | C0/I0/F5 | KNOWN_GAP |
| M8 | positive | 5/5 | 0 | 5 | C0/I0/F5 | GATING-capable |
| M9 | positive | 1/1 | 0 | 0 | C0/I4/F1 | KNOWN_GAP |

detection total: **36/90** vs floor 51/66 aggregate (haiku); floor violations: ['M12', 'M16', 'M3']; GATING violations: ['C7']; pair-integrity violations: [{'positive': 'M1', 'control': 'C1', 'reason': 'control fails — detection indistinguishable from over-triggering'}, {'positive': 'M10', 'control': 'C10', 'reason': 'control fails — detection indistinguishable from over-triggering'}, {'positive': 'M2', 'control': 'C2', 'reason': 'control fails — detection indistinguishable from over-triggering'}, {'positive': 'M8', 'control': 'C8', 'reason': 'control fails — detection indistinguishable from over-triggering'}]; control FBs: 91 (caps 78/112); positive-side family FBs: {'hallucinated-fact': 2, 'risk-boilerplate': 15, 'severity-inflation': 3, 'speculative-consequence': 12, 'unattributed': 1}; control-side family FBs: {'hallucinated-fact': 20, 'risk-boilerplate': 34, 'severity-inflation': 6, 'speculative-consequence': 29, 'unattributed': 2}; controls failing: 13/18

## sonnet

| id | kind | det(fixture-level)/floor | FBs | noise | assessment stability | state |
|---|---|---|---|---|---|---|
| C1 | control | - | 11 | 5 | C0/I0/F5 | KNOWN_GAP |
| C10 | control | - | 8 | 3 | C0/I0/F5 | KNOWN_GAP |
| C11 | control | - | 0 | 5 | C5/I0/F0 | GATING-capable |
| C12 | control | - | 20 | 6 | C0/I0/F5 | KNOWN_GAP |
| C13 | control | - | 16 | 1 | C0/I0/F5 | KNOWN_GAP |
| C14 | control | - | 9 | 6 | C0/I0/F5 | KNOWN_GAP |
| C15 | control | - | 10 | 3 | C0/I0/F5 | KNOWN_GAP |
| C16 | control | - | 21 | 6 | C0/I0/F5 | KNOWN_GAP |
| C17 | control | - | 0 | 0 | C5/I0/F0 | GATING-capable |
| C18 | control | - | 0 | 0 | C5/I0/F0 | GATING-capable |
| C2 | control | - | 8 | 3 | C0/I0/F5 | KNOWN_GAP |
| C3 | control | - | 10 | 5 | C0/I0/F5 | KNOWN_GAP |
| C4 | control | - | 0 | 1 | C5/I0/F0 | GATING-capable |
| C5 | control | - | 0 | 6 | C5/I0/F0 | GATING-capable |
| C6 | control | - | 0 | 0 | C5/I0/F0 | GATING-capable |
| C7 | control | - | 7 | 3 | C1/I0/F4 | KNOWN_GAP |
| C8 | control | - | 7 | 8 | C0/I0/F5 | KNOWN_GAP |
| C9 | control | - | 12 | 5 | C0/I0/F5 | KNOWN_GAP |
| M1 | positive | 5/5 | 3 | 4 | C0/I0/F5 | KNOWN_GAP |
| M10 | positive | 5/5 | 4 | 1 | C0/I0/F5 | KNOWN_GAP |
| M11 | positive | 2/5 | 0 | 0 | C0/I0/F5 | KNOWN_GAP |
| M12 | positive | 0/5 | 12 | 5 | C0/I0/F5 | KNOWN_GAP |
| M13 | positive | 0/1 | 16 | 0 | C0/I0/F5 | KNOWN_GAP |
| M14 | positive | 5/5 | 2 | 5 | C0/I0/F5 | KNOWN_GAP |
| M15 | positive | 0/0 | 9 | 9 | C0/I0/F5 | KNOWN_GAP |
| M16 | positive | 0/5 | 8 | 7 | C0/I0/F5 | KNOWN_GAP |
| M17 | positive | 5/5 | 0 | 1 | C0/I0/F5 | GATING-capable |
| M18 | positive | 5/5 | 0 | 0 | C0/I0/F5 | GATING-capable |
| M2 | positive | 5/5 | 0 | 0 | C0/I0/F5 | GATING-capable |
| M3 | positive | 0/5 | 3 | 5 | C0/I0/F5 | KNOWN_GAP |
| M4 | positive | 0/0 | 0 | 0 | C5/I0/F0 | KNOWN_GAP |
| M5 | positive | 0/0 | 0 | 0 | C5/I0/F0 | KNOWN_GAP |
| M6 | positive | 0/0 | 0 | 0 | C5/I0/F0 | KNOWN_GAP |
| M7 | positive | 5/5 | 10 | 3 | C0/I0/F5 | KNOWN_GAP |
| M8 | positive | 5/5 | 0 | 6 | C0/I0/F5 | GATING-capable |
| M9 | positive | 5/5 | 1 | 2 | C0/I0/F5 | KNOWN_GAP |

detection total: **47/90** vs floor 51/66 aggregate (sonnet); floor violations: ['M11', 'M12', 'M13', 'M16', 'M3']; GATING violations: ['C7']; pair-integrity violations: [{'positive': 'M2', 'control': 'C2', 'reason': 'control fails — detection indistinguishable from over-triggering'}, {'positive': 'M8', 'control': 'C8', 'reason': 'control fails — detection indistinguishable from over-triggering'}]; control FBs: 139 (caps 78/112); positive-side family FBs: {'hallucinated-fact': 8, 'risk-boilerplate': 21, 'severity-inflation': 17, 'speculative-consequence': 12, 'unattributed': 10}; control-side family FBs: {'hallucinated-fact': 37, 'risk-boilerplate': 44, 'severity-inflation': 31, 'speculative-consequence': 20, 'unattributed': 7}; controls failing: 12/18

## Layer 3 — diagnostic interpretation (hypotheses, not conclusions)

**Decision-matrix outcome: pass-1 clearly fails on both profiles.** Detection 36/90 vs the 51 floor (haiku) and 47/90 vs the 66 floor (sonnet); C7 GATING violated on both; control FBs 91/139 vs the 78/112 caps and vs #36's 90/135. Per the agreed sequence: **no paid pass-1 confirmation campaign**; the next step is an iteration-5 design decision informed by this distribution. That decision belongs to the maintainer.

Candidate hypotheses the distribution supports (each requires its own evidence before becoming a mechanism decision):

1. **Speculative-consequence remains a dominant positive-side family** (12 FBs haiku, 12 sonnet) — consistent with the standing taxonomy; it has survived four mechanisms.
2. **Over-blocking is the global failure shape, not under-detection of real defects**: 13/18 controls carry false blockers on haiku and 12/18 on sonnet, while most positives still detect their expected entries — the single-stage surface's defect is disproportionately false positives, which is also what made the layer-(b) and iteration-2 caps fail.
3. **The repair-4 matcher-extension families collapsed**: M12/M16/M3 at 0/5 on both profiles against floors of 5 earned by #36-era outputs. Whatever phrasing those needles were extended to recognize, the current provider's outputs no longer contain it — the strongest direct drift signal in this sample. (Alternative: #36-era hits were partly matcher-tolerance artifacts; the witness-replay invariants argue against but do not exclude this.)
4. **Sonnet M17 detection meets its frozen floor** (5/5 vs floor 5); haiku M17 remains at its frozen floor of 0. Absolute-consistency detection is therefore not part of the current failure distribution on sonnet.
5. **Control-side family distribution**: risk-boilerplate leads haiku control FBs (34) and sonnet control FBs (44); severity-inflation is sonnet's second (31). All positive/control splits are in pass1-rescore.json.

Reviewer-surface caveat: all comparisons are against #36-era numbers produced by the same rubric/prompt/settings bytes AND byte-equal model-facing fixture inputs (proven in Layer 1); differences are therefore attributable to the model/provider sampling layer, not to reviewer code. What no retrospective can answer: whether a *fresh* run would reproduce these exact numbers (single-sample variance is unquantified here) — one more reason this stays diagnostic and any binding claim needs a new frozen campaign.

