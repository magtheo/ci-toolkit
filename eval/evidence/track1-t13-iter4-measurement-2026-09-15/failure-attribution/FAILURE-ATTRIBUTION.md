# Failure-attribution audit (DIAGNOSTIC — zero model calls)

Question: **is the single-stage reviewer primarily failing because it lacks necessary evidence, or because it fails to use/reconcile evidence already present?** This audit informs the iteration-5 design decision; it is not a mechanism proposal, not a new gate, and #64 remains a non-binding diagnostic sample.

Attributions are **human judgment** (claim table `claims.py`, sensitivity layer `sensitivity-diagnostics.jsonl`) applied to machine-derived provenance (`derive_population.py`) by deterministic aggregation (`build_summary.py`). Each record carries its own provenance: profile, fixture, run, trace index, (model_id, digest), raw finding text, rationale, and evidence pointers into the model-facing input.

## Layer 1 — population integrity

- Control false blockers: **91 haiku / 139 sonnet** — reconcile exactly to #64 (RECONCILED).
- Positive-side contamination: 101 records; by-family totals reconcile to #64 (see summary JSON).
- Every distinct finding cluster matched exactly one authored claim rule (fail-closed: uncovered clusters abort the build; overlapping patterns resolve first-match-wins, same attribution).
- All 331 records carry a known taxonomy bucket; every necessary-evidence-absent record names the missing information.
- Sensitivity diagnostics cover all 38 non-detecting runs of #64's floor-violation fixtures, validated against the frozen entry-detection matrix.

## Layer 2 — observed attribution (descriptive)

### Control false blockers by primary attribution

| bucket | haiku (91) | | sonnet (139) | |
|---|---|---|---|---|
| severity-miscalibration | 25 | 27% | 32 | 23% |
| speculative-harm-chain | 14 | 15% | 38 | 27% |
| counterevidence-present | 21 | 23% | 23 | 16% |
| necessary-evidence-absent | 8 | 8% | 34 | 24% |
| external-semantic-knowledge | 23 | 25% | 12 | 8% |

### Family x attribution cross-tab (control side; full table in the summary JSON)

| profile/family | attribution counts |
|---|---|
| haiku/hallucinated-fact | {'external-semantic-knowledge': 8, 'counterevidence-present': 7, 'severity-miscalibration': 3, 'speculative-harm-chain': 2} |
| haiku/risk-boilerplate | {'external-semantic-knowledge': 15, 'counterevidence-present': 1, 'severity-miscalibration': 9, 'speculative-harm-chain': 9} |
| haiku/severity-inflation | {'speculative-harm-chain': 2, 'necessary-evidence-absent': 2, 'severity-miscalibration': 1, 'counterevidence-present': 1} |
| haiku/speculative-consequence | {'severity-miscalibration': 12, 'speculative-harm-chain': 1, 'counterevidence-present': 12, 'necessary-evidence-absent': 4} |
| sonnet/hallucinated-fact | {'counterevidence-present': 10, 'severity-miscalibration': 15, 'external-semantic-knowledge': 3, 'speculative-harm-chain': 6, 'necessary-evidence-absent': 3} |
| sonnet/risk-boilerplate | {'speculative-harm-chain': 26, 'counterevidence-present': 2, 'necessary-evidence-absent': 9, 'external-semantic-knowledge': 4, 'severity-miscalibration': 3} |
| sonnet/severity-inflation | {'external-semantic-knowledge': 5, 'severity-miscalibration': 9, 'speculative-harm-chain': 5, 'necessary-evidence-absent': 10, 'counterevidence-present': 2} |
| sonnet/speculative-consequence | {'necessary-evidence-absent': 10, 'counterevidence-present': 5, 'severity-miscalibration': 4, 'speculative-harm-chain': 1} |

### Positive-side contamination by attribution

- haiku: {'speculative-harm-chain': 11, 'counterevidence-present': 8, 'necessary-evidence-absent': 7, 'severity-miscalibration': 6, 'mixed-or-ambiguous': 1}
- sonnet: {'necessary-evidence-absent': 29, 'severity-miscalibration': 15, 'external-semantic-knowledge': 12, 'speculative-harm-chain': 7, 'counterevidence-present': 3, 'mixed-or-ambiguous': 2}

### Sensitivity-regression diagnostics (entry-level, non-detecting runs)

| fixture/profile | diagnoses |
|---|---|
| haiku/M12 | {'expected-evidence-present-but-missed': 4, 'expressed-but-not-matched-by-oracle-wording': 1} |
| haiku/M16 | {'expected-evidence-present-but-missed': 1, 'expressed-but-not-matched-by-oracle-wording': 4} |
| haiku/M3 | {'expressed-but-not-matched-by-oracle-wording': 5} |
| sonnet/M11 | {'expressed-but-not-matched-by-oracle-wording': 3} |
| sonnet/M12 | {'expressed-but-not-matched-by-oracle-wording': 4, 'expected-evidence-present-but-missed': 1} |
| sonnet/M13 | {'expected-evidence-present-but-missed': 5} |
| sonnet/M16 | {'expected-evidence-present-but-missed': 5} |
| sonnet/M3 | {'expressed-but-not-matched-by-oracle-wording': 5} |

Legend: expected-evidence-present-but-missed; expected-evidence-absent-insufficient-input; expressed-but-not-matched-by-oracle-wording; model-semantic-misunderstanding; other-ambiguous

## Layer 3 — design implications (hypotheses, not conclusions)

Combined control-side shares: severity-miscalibration 24% (57/230), speculative-harm-chain 22% (52), counterevidence-present 19% (44), necessary-evidence-absent 18% (42), external-semantic-knowledge 15% (35).

**Answer to the framing question: Case 5 — mixed, with a clear center of gravity against pure evidence-absence.** No single bucket dominates; the two largest (severity-miscalibration and speculative-harm-chain, ~48% combined) are decision-policy failures — the reviewer converts defensible observations and hypothetical misuse chains into blocking severity — not evidence problems. counterevidence-present (~19%) shows the reviewer dismissing guards and contracts printed in its own input (reconciliation failures), and necessary-evidence-absent (~18%) is real but concentrated in opaque-parameter contracts (session/repo adapters, called-workflow internals, field schemas) rather than broad context starvation.

**Layer (c) 'evidence representation / context enrichment': NOT causally justified as the primary iteration-5 direction.** It addresses at most the ~18% absent-evidence share, and the audit's strict criterion (never counting ignored evidence as absent) is exactly what keeps that share honest. The distribution instead supports hypotheses in this order:

1. **Decision-policy / severity governance**: the largest share (~48% with speculative chains) — mechanisms that separate observation from blocking justification, enforce defect-present-vs-hypothetical distinctions, and reserve blocking for demonstrated failure paths.
2. **Reconciliation of visibly-present counterevidence** (~19%): documented contracts and visible guards being argued past rather than with — salience/claim-vs-evidence structure, not more context.
3. **Contract-completion for opaque parameters** (~18%, mostly sonnet): if pursued, the targeted form is interface-contract information (adapter/service schemas), not general context enrichment.

**Sensitivity side is a different phenomenon, as required:** 25 of 38 non-detecting runs are `expressed-but-not-matched-by-oracle-wording` — the model substantively stated the defect but not in the frozen repair-4 vocabulary (exact bigrams like 'filesystem metadata', 'indistinguishable from a successful', '{"ok"}', 'suppress/exit code'). This is an **oracle-vocabulary rigidity observation reported for maintainer review, not patched here** (frozen-matchers rule); it confounds floor comparisons to an unquantified degree. The remaining runs are attention failures (sonnet M13: security chains consumed the budget; the missing tag input was never noticed — salience, evidence present).

**Methodological limits:** attributions are single-auditor human judgment with recorded rationale and evidence pointers (reviewable, not algorithmic truth); findings are treated as primary-bucket exclusive by design; #64 is a single diagnostic sample (no variance estimate); nothing here reinterprets #64 as binding T1.2 evidence, and the sensitivity floors remain the frozen normative reference.

