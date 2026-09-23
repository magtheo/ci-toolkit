"""Phase-22C m4rel implementation checks.

Re-executes the in-sample gates live against the corpus, pins the
module and evidence hashes, enforces independence (no frozen-verifier
imports), the holdout seal, and the dev near-miss units. No test here
executes the candidate against the sealed holdout.
"""
import ast
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.evidence_boundary_sim as boundary  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import eval.v21_contract_relations as frozen  # noqa: E402
import eval.v21_m4_relation as m4  # noqa: E402
import eval.v21_replay as v21  # noqa: E402
import eval.v21_routes_replay as rr  # noqa: E402

EVID = REPO / "eval" / "evidence" / \
    "v21-m4rel-implementation-2026-09-23"
EVIDENCE = json.loads((EVID / "EVIDENCE.json").read_text())
HOLDOUT = REPO / "eval" / "evidence" / "v21-m4rel-holdout-2026-09-23"


def _rows(fixtures):
    rows = []
    for source, rel in boundary.SOURCES.items():
        records = [json.loads(line)
                   for line in (REPO / rel).read_text().splitlines()
                   if line.strip()]
        for ri, rec in enumerate(records):
            fixture = fixtures[rec["fixture"]]
            for fi, finding in enumerate(
                    (rec.get("result") or {}).get("findings", [])):
                if finding.get("severity") != "blocking":
                    continue
                sim = boundary.simulate_finding(finding, fixture)
                rows.append(dict(
                    role=v21._role(finding, fixture),
                    route=rr.route_of(finding, fixture, sim),
                    g2=sim["g2_contract_aware"],
                    fixture=rec["fixture"], source=source,
                    ri=ri, fi=fi, finding=finding))
    return rows


def test_module_identity_and_pins():
    assert m4.NAME == "m4rel"
    assert m4.RELATION == \
        "unsubstantiated_absolute_docstring_claim"
    assert EVIDENCE["phase"] == "22C"
    assert EVIDENCE["status"] == \
        "implemented-in-sample-only-no-authority-granted"
    assert EVIDENCE["candidate"]["module_sha256"] == hashlib.sha256(
        (REPO / "eval" / "v21_m4_relation.py")
        .read_bytes()).hexdigest()
    assert EVIDENCE["frozen_contract"]["sha256"] == hashlib.sha256(
        (REPO / "eval" / "evidence" /
         "v21-m4rel-prereg-2026-09-23" /
         "TARGETS_CONTRACT.json").read_bytes()).hexdigest()
    assert EVIDENCE["oracle_untouched"][
        "oracle_version"] == rc.oracle_version()
    assert EVIDENCE["oracle_untouched"][
        "frozen_verifier_module_sha256"] == hashlib.sha256(
        (REPO / "eval" / "v21_contract_relations.py")
        .read_bytes()).hexdigest()


def test_independence_no_frozen_imports():
    tree = ast.parse(
        (REPO / "eval" / "v21_m4_relation.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            mods = [node.module or ""]
        else:
            continue
        for mod in mods:
            assert "v21_contract_relations" not in mod, mod
            assert "relation" not in mod.lower(), mod


def test_in_sample_gates_live():
    fixtures = {f["id"]: f
                for f in rc.load_corpus(REPO / "eval" / "fixtures")}
    rows = _rows(fixtures)
    fired = {fid for fid, fx in fixtures.items() if m4.detect(fx)}
    assert fired == {"M4"}
    targets = [r for r in rows if r["fixture"] == "M4"
               and r["role"] == "true_positive_detection"
               and r["route"] == "contract_contradiction"
               and r["g2"] == "BLOCK_SURVIVES"]
    assert len(targets) == 2
    assert all(m4.covers(r["finding"], fixtures["M4"])
               for r in targets)
    controls = [r for r in rows if r["role"] == "control_blocker"]
    assert len(controls) == 77
    assert not any(
        m4.covers(r["finding"], fixtures[r["fixture"]])
        for r in controls)
    extras = [r for r in rows
              if r["role"] == "positive_extra_blocker"]
    assert len(extras) == 34
    assert not any(
        m4.covers(r["finding"], fixtures[r["fixture"]])
        for r in extras)
    fam = [r for r in rows if r["fixture"] == "M4"
           and r["role"] == "true_positive_detection"
           and not (r["route"] == "contract_contradiction"
                    and r["g2"] == "BLOCK_SURVIVES")]
    assert len(fam) == 5
    assert all(m4.covers(r["finding"], fixtures["M4"])
               for r in fam)


def test_evidence_matches_live():
    res = EVIDENCE["in_sample_results"]
    assert res["fixtures_fired"] == ["M4"]
    assert res["targets"]["covered"] == \
        res["targets"]["total"] == 2
    assert res["controls"]["fired"] == 0
    assert res["controls"]["total"] == 77
    assert res["extras"]["claim_linked"] == 0
    assert res["extras"]["file_match_only"] == 4
    assert res["extras"]["total"] == 34
    assert res["family_context_non_targets"]["covered"] == 5
    assert res["family_context_non_targets"]["total"] == 5
    assert EVIDENCE["dev_units"]["all_ok"] is True
    assert len(EVIDENCE["dev_units"]["results"]) == 7


def test_holdout_seal():
    seal = EVIDENCE["holdout_seal"]
    assert seal["executions_during_22C"] == 0
    assert seal["fixture_ids_embedded_in_this_evidence"] == []
    assert "qualification" in seal["first_sanctioned_use"]
    assert seal["dir"] == \
        "eval/evidence/v21-m4rel-holdout-2026-09-23"
    blob = json.dumps(EVIDENCE)
    for i in range(1, 7):
        assert "m4h-P%d" % i not in blob
        assert "m4h-C%d" % i not in blob
    assert (HOLDOUT / "MANIFEST.json").exists()


DEV_UNITS = [
    ("core/validate.py", "utils: document validation contract",
     "Documents the validator contract.",
     '"""Validation contract.\n\nThe validator must not be silently '
     'skipped when a rule is disabled.\n"""\ndef validate(x):\n'
     "    return x\n", False),
    ("core/parse.py", "parser: document error contract",
     "Documents the error contract.",
     '"""Parser error contract.\n\nAll parse failures are raised as '
     'ParseError; none are swallowed.\n"""\nclass ParseError('
     "Exception):\n    pass\n", False),
    ("core/flags.py", "core: document retry metadata",
     "Documents the RetryFlag metadata.",
     '"""Retry metadata.\n\nRetry decisions belong to the scheduler '
     'and are outside this module; this flag carries no behavioral '
     'contract.\n"""\nclass RetryFlag:\n    pass\n', False),
    ("index/hints.py", "index: document refresh ordering",
     "Documents the RefreshHint field.",
     '"""Refresh hints.\n\nThe indexer typically reads this hint '
     'first; ordering behavior is configured in the indexer '
     'itself.\n"""\nclass RefreshHint:\n    pass\n', False),
    ("index/route.py", "index: document shard routing contract",
     "Documents how shard routing consumes ShardRoute.",
     '"""Shard routing contract.\n\nThe indexer always consults this '
     'route when placing shards and uses no other placement '
     'signal.\n"""\nclass ShardRoute:\n    def __init__(self, key):\n'
     "        self.key = key\n", True),
]


def _dev_fixture(path, title, body, patch):
    lines = patch.splitlines()
    header = "--- /dev/null\n+++ b/%s\n@@ -0,0 +%d @@\n" % (
        path, len(lines))
    unified = header + "\n".join("+" + line for line in lines)
    return {"input": {"title": title, "body": body,
                      "files": [{"path": path,
                                 "status": "added",
                                 "patch": unified}]}}


def test_dev_near_miss_units():
    for path, title, body, patch, expect in DEV_UNITS:
        fires = m4.detect(_dev_fixture(path, title, body, patch))
        assert bool(fires) is expect, (path, expect, fires)


def test_substantiation_two_files():
    fixture = _dev_fixture(
        "index/select.py", "index: unify shard selection",
        "Switches the runner to the shared selector so every shard "
        "read goes through one mechanism.",
        '"""Shard selection contract.\n\nEvery shard read resolves '
        'through this selector and no other mechanism.\n"""\n'
        "class ShardSelector:\n    pass\n")
    fixture["input"]["files"].append({
        "path": "index/runner.py", "status": "added",
        "patch": "--- /dev/null\n+++ b/index/runner.py\n@@ -0,0 +5 @@\n"
                 "+from index.select import ShardSelector\n+\n+\n"
                 "+def run(shard):\n+    return ShardSelector().pick("
                 "shard)\n"})
    assert m4.detect(fixture) == []
