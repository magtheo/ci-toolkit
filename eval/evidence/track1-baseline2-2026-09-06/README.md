# Track 1 T1.2 remeasurement — BINDING CANDIDATE — 2026-09-06

> **STATUS: binding candidate, pending the human validity check.**
> The floors and tables below activate as the T1.3/T1.5
> non-regression reference ONLY if that check finds no remaining
> corpus defects or matcher misclassifications. See "Human validity
> check" at the end.

Unchanged reviewer (subject `4b07246`) × repaired oracle
`9fae85b26ff45dc6`, full 36-fixture corpus, N=5, both governed
profiles. Experimental feature-branch evaluation (Deviation 4/5) —
no deployment qualification claim.

## Identity and spend

| | haiku | sonnet |
| --- | --- | --- |
| model | `anthropic/claude-haiku-4.5` | `anthropic/claude-sonnet-4.5` |
| calls | 180 | 180 |
| prompt tokens | 243,615 | 243,615 |
| completion tokens | 79,430 | 76,005 |
| retries (stderr) | 0 | 0 |

- subject SHA `4b07246a114a9130b6ef3d6a67cd09a01faacace`, oracle
  `9fae85b26ff45dc6`, corpus hash per report profile
- **360 logical calls, 0 retries → 360 provider attempts** (authorized
  envelope 400); no restarts, no reruns
- identical prompt-token totals across profiles (deterministic prompts)
- console logs: `*.stdout.log` / `*.stderr.log`

## Repair validation (vs. the 2026-09-05 diagnostic)

- **`unclassified` collapsed 64/86 → 4/6**: the fragment-artifact and
  matcher-gap classes are gone. The repair did what it claimed.
- Extended matchers work in the wild: M10 **2→5 / 0→5** (h/s), M12
  **1→5 / 2→5**, M16 held 5/5, M2 clean 5/5 both.
- C4/C7 marginality: haiku **clean** this run (was 1 fb each); sonnet
  shows **1 C7 violation** — the marginality moved profiles rather
  than disappeared (GATING states unchanged; measurement recorded).

## Emitted false blockers by family (coded; the T1.3 ordering input)

| family | haiku | sonnet |
| --- | --- | --- |
| **speculative-consequence** | **59** | **81** |
| severity-inflation | 16 | 60 |
| hallucinated-fact | 34 | 30 |
| risk-boilerplate | 14 | 35 |
| unclassified | 4 | 6 |

Grounding basis (FBs): cited-evidence 45/44, inferred 68/133,
asserted 14/35 — the reviewer engages the diff; it grounds
speculative and inflated claims (confirmed from the diagnostic).

## Binding-candidate sensitivity floors (`derived-metrics.json`)

Per-positive minimum expected-finding hits / 5:

| id | h | s | | id | h | s |
| -- | - | - |-| -- | - | - |
| M1 | 3 | 5 | | M11 | 5 | 5 |
| M2 | 5 | 5 | | M12 | 5 | 5 |
| M3 | 5 | 5 | | M13 | 0 | 0 |
| M4 | 0 | 0 | | M14 | 5 | 5 |
| M5 | 0 | 0 | | M15 | 0 | 0 |
| M6 | 1 | 0 | | M16 | 5 | 5 |
| M7 | 5 | 5 | | M17 | 0 | 5 |
| M8 | 5 | 5 | | M18 | 0 | 5 |
| M9 | 2 | 5 | | M10 | 5 | 5 |

False-clears (CLEAR+INCONCLUSIVE / 5): M4 5·5, M5 5·5 (known-gap
misses), M15/M17/M18 5·0 on haiku, M6 0·5 on sonnet, M9 3·0 on
haiku (3 of them fail-closed INCONCLUSIVE — the quoting-heavy
malformed-JSON robustness finding persists, correctly never Clear).

## Human validity check (required before binding)

Judgment calls coded during derivation, surfaced for human
adjudication — each is flagged inline in `narrative-coding.jsonl`:

1. **`c12-session-semantics`** — C12/M12 narratives disputing the
   presented abstraction ("session.get never awaited / returns
   Response / OriginError unreachable / KeyError violates the
   docstring"). Coded as reviewer failures (the docstring contract
   implies the session wrapper's semantics; "empty cache raises" IS
   satisfied by the KeyError). **Question:** is the abstraction
   under-specified as presented (corpus gap), or is the reviewer
   contract-blind (as coded)?
2. **`c7-scope-wording`** — the sonnet GATING violation on C7
   ("scope violation — PR claims purely mechanical…"). Coded
   severity-inflation: it disputes description wording, not diff
   content. **Question:** acceptable wording, or does the fixture's
   PR-body claim genuinely overstate?
3. **`m16-novel-phrasing`** — M16 fabricated-success narratives in
   phrasings the frozen needles miss ("Returns \`{\"ok\": …}"
   behind a backtick; "falsely claiming success"; "a lie"). 4–6
   coded unclassified (mechanically FB, semantically detections).
   **Question:** matcher misclassification to fix in a future oracle
   change, or acceptable conservative measurement?

Also note (not flagged, recorded): M13 floating-tag detection 0/5 on
both profiles — a real detection gap, not a corpus artifact; M1
haiku 3/5 (down from 5) — the added safe-pattern lines give haiku
new blocking material.

## Reproduction

```bash
export OPENROUTER_API_KEY=...   # caller's key; never stored here
python3 eval/run_corpus.py --model anthropic/claude-haiku-4.5  --n 5 \
  --out eval/evidence/track1-baseline2-2026-09-06/haiku-n5.json
python3 eval/run_corpus.py --model anthropic/claude-sonnet-4.5 --n 5 \
  --out eval/evidence/track1-baseline2-2026-09-06/sonnet-n5.json
```
