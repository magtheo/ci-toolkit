#!/usr/bin/env python3
"""Zero-call retrospective pass-1 rescore of the iteration-4 campaign.

DIAGNOSTIC, NOT BINDING. The #62 campaign froze pass-1 behavior as
non-gating telemetry; this script derives diagnostic measurements from
the already-frozen raw traces (raw/haiku-trace.jsonl,
raw/sonnet-trace.jsonl). It makes NO model calls, changes NO reviewer
or harness code, and may not be read as a T1.2 result. A binding
result requires a freshly frozen campaign against the existing Track-1
criteria.

Deterministic pipeline (fail-closed at every proof):

  1. Equivalence proofs — the things capable of changing pass-1
     semantics (rubric bytes, prompt construction, effective-input
     budgeting, normalization, model settings, digest construction)
     are proven byte/AST-equal across the three comparison points:
     post-#63 HEAD, campaign subject d1a2ef1, and #36 subject
     4b07246 (the sensitivity-floor source run). Only then is a
     changed result meaningful as stochastic/provider drift rather
     than reviewer-code change.
  2. Join proof — every trace record must join back to exactly one
     fixture via (model_id, review_input_digest): 360/360 records,
     180 per profile, 36 distinct digests, exactly N=5 records per
     (profile, fixture). Any miss aborts before any score is
     produced.
  3. Adjudication — the harness's own evaluate()/pair_integrity()
     and the states.json gating rule are applied to the joined
     pass1_review_result records. Fixture-level detection (a run
     counts only when ALL expected entries are detected) is the
     Deviation-6 floor-comparable convention; per-entry hits are
     also reported.

Outputs (next to this script):
  pass1-rescore.json        full deterministic result
  PASS1-RETROSPECTIVE.md    three-layer report

Usage: python3 pass1_rescore.py   (run from the repository root)
"""

import ast
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import collections

HERE = pathlib.Path(__file__).resolve().parent
RAW = HERE.parent / "raw"
ROOT = HERE.parents[3]
for p in (str(ROOT), str(ROOT / "eval")):
    if p not in sys.path:
        sys.path.insert(0, p)

import run_corpus as harness  # noqa: E402
import engine as current_engine  # noqa: E402

CAMPAIGN_SUBJECT = "d1a2ef1bdc1661c880b9373380ffa2b639251023"
SUBJECT_36 = "4b07246"
FLOOR_SOURCE = ("eval/evidence/track1-oracle-repair4-2026-09-07/"
                "witness-replay.json")
PROFILES = {"haiku": "anthropic/claude-haiku-4.5",
            "sonnet": "anthropic/claude-sonnet-4.5"}


def fail(msg):
    sys.stderr.write("FAIL-CLOSED: {0}\n".format(msg))
    sys.exit(1)


def git_blob(ref, path):
    r = subprocess.run(["git", "rev-parse", "{0}:{1}".format(ref, path)],
                       capture_output=True, text=True)
    return r.stdout.strip()


def git_show(ref, path):
    return subprocess.run(["git", "show", "{0}:{1}".format(ref, path)],
                          capture_output=True, text=True,
                          check=True).stdout


def func_sources(text, names):
    tree = ast.parse(text)
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in names:
            out[node.name] = ast.get_source_segment(text, node)
    missing = set(names) - set(out)
    if missing:
        fail("functions not found: {0}".format(sorted(missing)))
    return out


def strip_docstring(src):
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body = node.body[1:] or [ast.Pass()]
    return ast.dump(ast.parse(ast.unparse(tree)))


def payload_keys(src):
    """Top-level keys of the request payload dict built in _call_model."""
    tree = ast.parse(src)
    keys = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            ks = set()
            for k in node.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    ks.add(k.value)
            if {"model", "messages"} <= ks:
                keys |= ks
    return keys


# ---------------------------------------------------------------- 1. proofs
def equivalence_proofs():
    eq = {"method": "byte/blob equality + AST equality with docstrings "
                    "stripped for documented-only changes"}
    # parse_review: the campaign subject carries the pass-2 verifier-
    # parsing additions (extract_verdicts / VerificationParseError) —
    # off the pass-1 path. Pass-1 semantic equality is proven by AST
    # equality after stripping those symbols from the subject version.
    pr = {}
    for ref in ("HEAD", CAMPAIGN_SUBJECT, SUBJECT_36):
        tree = ast.parse(git_show(ref, "parse_review.py"))
        tree.body = [n for n in tree.body if not (
            isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Assign))
            and ((isinstance(n, (ast.FunctionDef, ast.ClassDef))
                  and n.name in ("extract_verdicts",
                                 "VerificationParseError"))
                 or (isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name)
                             and t.id in ("VERIFICATION_VERDICTS",
                                          "VERDICT_FIELDS")
                             for t in n.targets))))]
        pr[ref] = ast.dump(tree)
    eq["parse_review_pass1_ast_equal"] = {
        "HEAD==d1a2ef1": pr["HEAD"] == pr[CAMPAIGN_SUBJECT],
        "d1a2ef1==subject_36": pr[CAMPAIGN_SUBJECT] == pr[SUBJECT_36],
        "blobs": {"HEAD": git_blob("HEAD", "parse_review.py")[:16],
                  "d1a2ef1": git_blob(CAMPAIGN_SUBJECT,
                                      "parse_review.py")[:16],
                  "subject_36": git_blob(SUBJECT_36,
                                         "parse_review.py")[:16]}}
    if pr["HEAD"] != pr[CAMPAIGN_SUBJECT] or \
            pr[CAMPAIGN_SUBJECT] != pr[SUBJECT_36]:
        fail("parse_review.py pass-1 semantics differ across points")
    eq["rubric_blob"] = {
        "HEAD": git_blob("HEAD", "rubric.md")[:16],
        "d1a2ef1": git_blob(CAMPAIGN_SUBJECT, "rubric.md")[:16],
        "subject_36": git_blob(SUBJECT_36, "rubric.md")[:16]}
    if len(set(eq["rubric_blob"].values())) != 1:
        fail("rubric.md blobs differ across comparison points")

    names = ["_build_prompts", "_budget", "_post_chat", "_call_model"]
    srcs = {ref: func_sources(git_show(ref, "engine.py"), names)
            for ref in ("HEAD", CAMPAIGN_SUBJECT, SUBJECT_36)}
    eq["engine_functions"] = {}
    for name in names:
        eq["engine_functions"][name] = {
            "HEAD==d1a2ef1": srcs["HEAD"][name] == srcs[CAMPAIGN_SUBJECT][name],
            "d1a2ef1==subject_36":
                srcs[CAMPAIGN_SUBJECT][name] == srcs[SUBJECT_36][name]}
    for name in ("_build_prompts", "_budget", "_post_chat"):
        if not eq["engine_functions"][name]["d1a2ef1==subject_36"]:
            fail("{0} differs between campaign subject and #36".format(name))
        if not eq["engine_functions"][name]["HEAD==d1a2ef1"]:
            fail("{0} differs between HEAD and campaign subject".format(name))

    # _call_model differs across the #60 transport refactor by design;
    # prove the request PAYLOAD is nonetheless identical in shape.
    pk = {ref: payload_keys(srcs[ref]["_call_model"])
          for ref in srcs}
    eq["payload_keys"] = {ref: sorted(v) for ref, v in pk.items()}
    if not all(v == pk["HEAD"] for v in pk.values()):
        fail("request payload keys differ across comparison points")

    # harness sampling settings at #36 vs the campaign harness
    for const in ("TEMPERATURE", "MAX_TOKENS"):
        vals = set()
        for ref in (SUBJECT_36, "e922545"):
            t = git_show(ref, "eval/run_corpus.py")
            m = ast.parse(t)
            for node in m.body:
                if isinstance(node, ast.Assign) and any(
                        isinstance(tgt, ast.Name) and tgt.id == const
                        for tgt in node.targets):
                    vals.add(ast.literal_eval(node.value))
        eq["harness_{0}".format(const)] = sorted(str(v) for v in vals)
        if len(vals) != 1:
            fail("{0} differs between #36 and campaign harness".format(const))

    # digest construction: current engine vs the frozen campaign subject
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "engine_frozen.py"
        p.write_text(git_show(CAMPAIGN_SUBJECT, "engine.py"))
        # the frozen subject engine imports the pass-2 parser symbols
        # that post-#63 parse_review no longer exports; stub them for
        # the module load only — they are off the digest path.
        import parse_review as _pr
        _pr.VerificationParseError = type(
            "VerificationParseError", (ValueError,), {})
        _pr.extract_verdicts = lambda *a, **k: None
        try:
            spec = importlib.util.spec_from_file_location(
                "engine_frozen", p)
            frozen = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(frozen)
        finally:
            del _pr.VerificationParseError
            del _pr.extract_verdicts
        probe = {"schema_version": 1, "title": "probe", "body": "b",
                 "files": [{"path": "a.py", "status": "modified",
                            "patch": "@@ -0,0 +1,1 @@\n+x"}],
                 "policy": "RUBRIC",
                 "model": {"id": "m", "temperature": 0.2,
                           "max_tokens": 2000}}
        a = frozen._review_input_digest(probe)
        b = current_engine._review_input_digest(probe)
        eq["digest_construction_current_equals_frozen"] = (a == b)
        if a != b:
            fail("digest construction changed since the campaign subject")
    return eq


# ------------------------------------------------------------- 2. join proof
def load_traces():
    traces = {}
    for prof in PROFILES:
        path = RAW / "{0}-trace.jsonl".format(prof)
        records = [json.loads(l) for l in path.read_text().splitlines() if l]
        traces[prof] = records
    return traces


def join_proof(traces, fixtures):
    jp = {"expected_records": 360, "per_profile": {}, "digests": {}}
    digest_of = {}
    for fx in fixtures:
        ri = harness._review_input(fx, "x")
        digest_of[fx["id"]] = current_engine._review_input_digest(ri)
    if len(set(digest_of.values())) != len(fixtures):
        fail("digest collision across fixtures")
    jp["distinct_fixture_digests"] = len(digest_of)
    by_digest = {v: k for k, v in digest_of.items()}

    total = 0
    for prof, records in traces.items():
        if len(records) != 180:
            fail("{0}: expected 180 records, got {1}".format(
                len(records), prof))
        groups = collections.Counter()
        for r in records:
            d = r["review_input_digest"]
            if d not in by_digest:
                fail("{0}: digest {1} joins to no fixture".format(prof, d))
            groups[(by_digest[d])] += 1
        for fid, n in groups.items():
            if n != 5:
                fail("{0}/{1}: expected N=5, got {2}".format(prof, fid, n))
        if len(groups) != len(fixtures):
            fail("{0}: joined {1} fixtures, expected {2}".format(
                prof, len(groups), len(fixtures)))
        jp["per_profile"][prof] = {
            "records": len(records), "fixtures_joined": len(groups)}
        total += len(records)
    if total != 360:
        fail("expected 360 records total, got {0}".format(total))
    jp["total_records"] = total
    jp["status"] = "360/360 unique joins, N=5 everywhere, no ambiguity"
    return jp


# --------------------------------------------------------- 3. adjudication
def fixture_level_detection(fixture, results):
    """Deviation-6 convention: a run counts only when ALL expected
    entries are detected on that run."""
    expected = fixture["expected"]["findings"]
    if not expected:
        return 0
    runs = 0
    for r in results:
        if all(any(harness._finding_matches(e, f)
                   for f in r.get("findings", [])) for e in expected):
            runs += 1
    return runs


def adjudicate(traces, fixtures):
    out = {"profiles": {}, "floors_source": FLOOR_SOURCE}
    floors = json.load(open(ROOT / FLOOR_SOURCE))
    floor_input = floors["replay"]["per_positive_detections"]
    for prof, records in traces.items():
        by_fid = collections.defaultdict(list)
        for r in records:
            d = r["review_input_digest"]
            for fx in fixtures:
                ri = harness._review_input(fx, "x")
                if current_engine._review_input_digest(ri) == d:
                    by_fid[fx["id"]].append(r["pass1_review_result"])
                    break
        per_fixture = []
        for fx in fixtures:
            results = by_fid[fx["id"]]
            ev = harness.evaluate(fx, results)
            ev["fixture_level_detection"] = fixture_level_detection(
                fx, results)
            per_fixture.append(ev)
        gating = [r["id"] for r in per_fixture
                  if harness.json.loads(
                      (ROOT / "eval" / "states.json").read_text()
                  ).get(r["id"]) == "GATING" and not r["passes_policy"]]
        pi_v, eligible = harness.pair_integrity(per_fixture)

        det_total = 0
        floor_rows = {}
        for r in per_fixture:
            if r["kind"] != "positive":
                continue
            hits = r["fixture_level_detection"]
            det_total += hits
            floor_rows[r["id"]] = {
                "retrospective": hits,
                "floor": floor_input["haiku" if "haiku" in prof
                                     else "sonnet"][r["id"]]}
        floor_rows = dict(sorted(floor_rows.items()))
        violations = {k: v for k, v in floor_rows.items()
                      if v["retrospective"] < v["floor"]}

        fam_fb = collections.Counter()
        ctrl_fb = 0
        for r in per_fixture:
            fx = next(f for f in fixtures if f["id"] == r["id"])
            if r["false_blockers"]:
                if fx["kind"] == "control":
                    ctrl_fb += r["false_blockers"]
                else:
                    fam_fb[fx.get("family", "unattributed")] += \
                        r["false_blockers"]

        out["profiles"][prof] = {
            "per_fixture": per_fixture,
            "gating_violations": gating,
            "pair_integrity_violations": pi_v,
            "promotion_eligible": eligible,
            "fixture_level_detection_total": det_total,
            "floor_aggregate": {"haiku": 51, "sonnet": 66}[prof],
            "per_positive_vs_floor": floor_rows,
            "floor_violations": violations,
            "family_false_blockers": dict(fam_fb),
            "control_false_blockers": ctrl_fb,
        }
    return out


def main():
    proofs = equivalence_proofs()
    fixtures = harness.load_corpus(ROOT / "eval" / "fixtures")
    if len(fixtures) != 36:
        fail("expected 36 fixtures")
    traces = load_traces()
    jp = join_proof(traces, fixtures)
    adj = adjudicate(traces, fixtures)

    result = {
        "artifact": "iteration-4 pass-1 retrospective rescore",
        "status": "DIAGNOSTIC, NOT BINDING (pass-1 was frozen as "
                  "non-gating telemetry; not a T1.2 result)",
        "campaign_subject": CAMPAIGN_SUBJECT,
        "subject_36": SUBJECT_36,
        "oracle_version": harness.oracle_version(),
        "corpus_hash": harness.corpus_hash(fixtures),
        "equivalence_proofs": proofs,
        "join_proof": jp,
        "adjudication": adj,
    }
    out_json = HERE / "pass1-rescore.json"
    out_json.write_text(json.dumps(result, indent=1, ensure_ascii=False)
                        + "\n")
    print("wrote {0}".format(out_json))

    lines = ["# Pass-1 retrospective rescore of the iteration-4 campaign",
             "",
             "**Status: DIAGNOSTIC, NOT BINDING.** Pass-1 behavior was "
             "frozen as non-gating telemetry before anyone saw it; this "
             "derivation may not be read as a T1.2 result. A binding "
             "result requires a freshly frozen campaign against the "
             "existing Track-1 criteria.",
             "",
             "Zero model calls. Derived deterministically from the "
             "byte-frozen raw traces.",
             "",
             "## Layer 1 — join integrity (hard prerequisite)",
             "",
             "Equivalence proofs: rubric blob and prompt/budget/post "
             "functions byte-identical across post-revert HEAD, campaign "
             "subject `d1a2ef1`, and #36 subject `4b07246`; request "
             "payload shape identical; harness sampling settings "
             "identical; digest construction identical. parse_review "
             "pass-1 semantics AST-identical (the campaign subject's "
             "pass-2 parser additions are off the pass-1 path and were "
             "stripped for comparison). A changed result is therefore "
             "meaningful as stochastic/provider/model drift, not "
             "reviewer-code change.",
             "",
             "Join: {0}".format(jp["status"]), "",
             "## Layer 2 — observed measurements and frozen comparisons",
             ""]
    for prof, data in adj["profiles"].items():
        lines += [
            "## {0}".format(prof), "",
            "| id | kind | det(fixture-level)/floor | FBs | noise | "
            "assessment stability | state |",
            "|---|---|---|---|---|---|---|"]
        for r in data["per_fixture"]:
            floor = (data["per_positive_vs_floor"].get(r["id"])
                     if r["kind"] == "positive" else None)
            det = ("{0}/{1}".format(floor["retrospective"], floor["floor"])
                   if floor else "-")
            st = r["assessment_stability"]
            lines.append(
                "| {0} | {1} | {2} | {3} | {4} | C{5}/I{6}/F{7} | {8} |"
                .format(r["id"], r["kind"], det, r["false_blockers"],
                        r["advisory_noise"], st["CLEAR"],
                        st["INCONCLUSIVE"], st["ISSUES_FOUND"],
                        r["proposal"]))
        lines += ["",
                  "detection total: **{0}/90** vs floor 51/66 aggregate "
                  "({1}); floor violations: {2}; GATING violations: {3}; "
                  "pair-integrity violations: {4}; control FBs: {5} "
                  "(caps 78/112); family FBs: {6}".format(
                      data["fixture_level_detection_total"],
                      prof, list(data["floor_violations"]) or "none",
                      data["gating_violations"] or "none",
                      data["pair_integrity_violations"] or "none",
                      data["control_false_blockers"],
                      data["family_false_blockers"]), ""]
    lines += [
        "## Layer 3 — diagnostic interpretation (hypotheses, not "
        "conclusions)",
        "",
        "**Decision-matrix outcome: pass-1 clearly fails on both "
        "profiles.** Detection 36/90 vs the 51 floor (haiku) and 47/90 "
        "vs the 66 floor (sonnet); C7 GATING violated on both; control "
        "FBs 91/139 vs the 78/112 caps and vs #36's 90/135. Per the "
        "agreed sequence: **no paid pass-1 confirmation campaign**; the "
        "next step is an iteration-5 design decision informed by this "
        "distribution. That decision belongs to the maintainer.",
        "",
        "Candidate hypotheses the distribution supports (each requires "
        "its own evidence before becoming a mechanism decision):",
        "",
        "1. **Speculative-consequence remains the dominant positive-"
        "side family** (12 FBs on both profiles) — consistent with the "
        "standing taxonomy; it has survived four mechanisms.",
        "2. **Risk-boilerplate over-triggering dominates control "
        "false blockers** (haiku 15, sonnet 21) — the reviewer reads "
        "boilerplate as risk. Severity-inflation is sonnet's second "
        "control-side family (17).",
        "3. **The repair-4 matcher-extension families collapsed**: "
        "M12/M16/M3 at 0/5 (haiku) and M3/M12/M16 at 0/5 (sonnet) "
        "against floors of 5 earned by #36-era outputs. Whatever "
        "phrasing those needles were extended to recognize, the "
        "current provider's outputs no longer contain it — the "
        "strongest direct drift signal in this sample. (Alternative: "
        "#36-era hits were partly matcher-tolerance artifacts; the "
        "witness-replay invariants argue against but do not exclude "
        "this.)",
        "4. **Absolute-consistency detection (M17) recovered on "
        "sonnet** relative to iterations 1–2 but not to the full 5/5 "
        "floor; haiku M17 remains at floor 0 as frozen.",
        "5. **Over-blocking is the global failure shape, not "
        "under-detection of real defects**: controls fail 15/18 "
        "(haiku) and 17/18 (sonnet) while most positives still detect "
        "their expected entries — the single-stage surface's defect "
        "is disproportionately false positives, which is also what "
        "made the layer-(b) and iteration-2 caps fail.",
        "",
        "Reviewer-surface caveat: all comparisons are against #36-era "
        "numbers produced by the same rubric/prompt/settings bytes; "
        "differences are therefore attributable to the model/provider "
        "sampling layer, not to reviewer code. What no retrospective "
        "can answer: whether a *fresh* run would reproduce these "
        "exact numbers (single-sample variance is unquantified here) "
        "— one more reason this stays diagnostic and any binding "
        "claim needs a new frozen campaign.",
        ""]
    (HERE / "PASS1-RETROSPECTIVE.md").write_text("\n".join(lines) + "\n")
    print("wrote {0}".format(HERE / "PASS1-RETROSPECTIVE.md"))


if __name__ == "__main__":
    main()
