"""Phase-22B m4rel candidate preregistration checks.

Pins TARGETS_CONTRACT.json against live reality: targets and disjoint
ownership, the enumerated near-miss control set (re-derived with the
frozen vocabulary scan), extra-blocker handling, the fresh holdout's
hashes/labels/pairing/disjointness, the no-implementation guard, and
the frozen protocol language. Prereg only: nothing here runs a
candidate.
"""
import hashlib
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.evidence_boundary_sim as boundary  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import eval.v21_contract_relations as frozen  # noqa: E402
import eval.v21_replay as v21  # noqa: E402
import eval.v21_routes_replay as rr  # noqa: E402

PREREG = REPO / "eval" / "evidence" / "v21-m4rel-prereg-2026-09-23"
HOLDOUT = REPO / "eval" / "evidence" / "v21-m4rel-holdout-2026-09-23"
CONTRACT = json.loads((PREREG / "TARGETS_CONTRACT.json").read_text())
MANIFEST = json.loads((HOLDOUT / "MANIFEST.json").read_text())
C22A = json.loads(
    (REPO / "eval" / "evidence" /
     "v21-preservation-authority-prereg-2026-09-23" /
     "QUALIFICATION_CONTRACT.json").read_text())
PSD = "pinned_sha_demoted_to_branch"
M4_CLAIM = "All retry decisions flow through ProcessingError.retryable"
VOCAB = re.compile(
    r"docstring|\bcomment\b|\bclaim|document|assert|guarantee"
    r"|\bpromise|\babsolute\b", re.I)


def _rows():
    fixtures = {f["id"]: f
                for f in rc.load_corpus(REPO / "eval" / "fixtures")}
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
                rows.append({
                    "role": v21._role(finding, fixture),
                    "route": rr.route_of(finding, fixture, sim),
                    "g2": sim["g2_contract_aware"],
                    "preds": v21.predicate_names(finding, fixture),
                    "rels": set(frozen.relation_names(finding,
                                                      fixture)),
                    "fixture": fixture["id"],
                    "comment": finding.get("comment", ""),
                    "source": source, "ri": ri, "fi": fi,
                })
    return rows


def test_contract_pins():
    assert CONTRACT["status"] == \
        "prereg-only-no-implementation-no-execution"
    pins = CONTRACT["pins"]
    assert pins["oracle_version"] == rc.oracle_version()
    assert pins["frozen_verifier_module_sha256"] == hashlib.sha256(
        (REPO / "eval" / "v21_contract_relations.py")
        .read_bytes()).hexdigest()
    assert pins["22a_qualification_contract_sha256"] == hashlib.sha256(
        (REPO / "eval" / "evidence" /
         "v21-preservation-authority-prereg-2026-09-23" /
         "QUALIFICATION_CONTRACT.json").read_bytes()).hexdigest()
    assert pins["18d_report_sha256"] == hashlib.sha256(
        (REPO / "eval" / "evidence" /
         "v21-contract-generalization-eval-2026-09-22" /
         "generalization-report-18d.json").read_bytes()).hexdigest()
    assert pins["21a_contract_sha256"] == hashlib.sha256(
        (REPO / "eval" / "evidence" /
         "v21-false-blocker-prereg-2026-09-23" /
         "REDUCTION_CONTRACT.json").read_bytes()).hexdigest()
    assert pins["18a_holdout_manifest_sha256"] == hashlib.sha256(
        (REPO / "eval" / "evidence" /
         "v21-contract-generalization-prereg-2026-09-22" /
         "MANIFEST.json").read_bytes()).hexdigest()


def test_targets_and_disjoint_ownership():
    rows = _rows()
    targets = sorted(
        (r["source"], r["ri"], r["fi"]) for r in rows
        if r["fixture"] == "M4"
        and r["role"] == "true_positive_detection"
        and r["route"] == "contract_contradiction"
        and not r["preds"] and not r["rels"]
        and r["g2"] == "BLOCK_SURVIVES")
    frozen_ids = sorted(tuple(t[2:]) for t in CONTRACT["targets"]["ids"])
    assert targets == frozen_ids == [
        ("b1-low", 44, 0), ("stage-a-max", 66, 0)]
    assert CONTRACT["targets"]["qualification_requirement"] == \
        "fires on 100% of P_M4 (2/2)"
    slate = C22A["candidate_slate"]
    claimants = [c for c in slate
                 if "P_M4" in json.dumps(c) or "P-M4" in json.dumps(c)]
    assert [c["name"] for c in claimants] == ["m4rel"]
    assert CONTRACT["authority_separation"].startswith(
        "this preregistration freezes")


def test_target_finding_pins():
    rows = _rows()
    for source, ri, key in [("stage-a-max", 66, "stage-a-max_r66_f0"),
                            ("b1-low", 44, "b1-low_r44_f0")]:
        r = next(x for x in rows if x["fixture"] == "M4"
                 and x["source"] == source and x["ri"] == ri)
        pin = CONTRACT["targets"]["finding_pins"][key]
        assert pin["file"] == "apps/worker/exceptions.py"
        raw = (REPO / boundary.SOURCES[source]).read_text()
        rec = json.loads(raw.splitlines()[ri])
        f = rec["result"]["findings"][0]
        assert f["file"] == pin["file"] and f["line"] == pin["line"]
        digest = hashlib.sha256(json.dumps(
            {"comment": f["comment"], "file": f["file"],
             "line": f["line"]}, sort_keys=True).encode()).hexdigest()
        assert digest == pin["sha256"], key


def test_semantics_note_keyword_caveat():
    note = CONTRACT["candidate"]["semantics_note"]
    assert "illustrative, NOT the detector" in note
    assert "keyword-only matching is insufficient" in note
    assert CONTRACT["candidate"]["fire_condition"].startswith(
        "an in-diff docstring")


def test_family_context_non_targets():
    rows = _rows()
    fam = sorted(
        (r["source"], r["ri"], r["fi"]) for r in rows
        if r["fixture"] == "M4"
        and r["role"] == "true_positive_detection"
        and (r["source"], r["ri"], r["fi"]) not in {
            ("b1-low", 44, 0), ("stage-a-max", 66, 0)})
    assert fam == sorted(
        tuple(t[2:]) for t in
        CONTRACT["family_context_non_targets"]["rows"]) == [
        ("b1-high", 14, 0), ("b1-high", 29, 0), ("b1-high", 44, 0),
        ("b1-low", 14, 0), ("b1-low", 29, 0)]
    r29 = next(r for r in rows if r["fixture"] == "M4"
               and r["source"] == "b1-low" and r["ri"] == 29)
    assert r29["route"] == "unwitnessed_behavior"
    assert r29["g2"] == "BLOCK_SURVIVES"


def test_near_miss_enumeration_matches_frozen_scan():
    rows = _rows()
    controls = [r for r in rows
                if r["role"] == "control_blocker"]
    assert len(controls) == 77
    derived = sorted(
        (r["fixture"], r["source"], r["ri"], r["fi"])
        for r in controls if VOCAB.search(r["comment"]))
    contracted = sorted(
        tuple(x) for x in
        CONTRACT["near_miss_control_rows"]["enumerated_ids"])
    assert derived == contracted
    assert len(contracted) == 25
    assert "QG1" in CONTRACT["near_miss_control_rows"]["binding_rule"]


def test_extra_blocker_handling():
    rows = _rows()
    m4_extras = sorted(
        (r["source"], r["ri"], r["fi"]) for r in rows
        if r["fixture"] == "M4"
        and r["role"] == "positive_extra_blocker")
    assert m4_extras == sorted(
        tuple(t[2:]) for t in
        CONTRACT["extra_blocker_handling"]["m4_extra_rows"])
    total = [r for r in rows
             if r["role"] == "positive_extra_blocker"]
    assert len(total) == 34
    assert "preserving an extra blocker fails" in \
        CONTRACT["extra_blocker_handling"]["corpus_wide"]


def test_holdout_integrity():
    assert hashlib.sha256(
        (HOLDOUT / "MANIFEST.json").read_bytes()).hexdigest() == \
        CONTRACT["validation_material"]["fresh_holdout"][
            "manifest_sha256"]
    seen = set()
    for entry in MANIFEST["fixtures"]:
        raw = (HOLDOUT / "fixtures" /
               (entry["id"] + ".json")).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == entry["sha256"], entry["id"]
        assert raw not in seen
        seen.add(raw)
    entries = sorted(MANIFEST["fixtures"], key=lambda e: e["id"])
    lines = ["%s  %s" % (e["sha256"], e["id"]) for e in entries]
    assert hashlib.sha256(
        ("\n".join(lines) + "\n").encode()).hexdigest() == \
        MANIFEST["manifest_lines_sha256"] == \
        CONTRACT["validation_material"]["fresh_holdout"][
            "manifest_lines_sha256"]
    assert MANIFEST["counts"] == {
        "controls": 6, "pairs": 6, "positives": 6,
        "relation": 1, "total": 12}


def test_holdout_labels_pairing_and_disjointness():
    fixtures = {}
    for entry in MANIFEST["fixtures"]:
        j = json.loads(
            (HOLDOUT / "fixtures" /
             (entry["id"] + ".json")).read_text())
        fixtures[entry["id"]] = j
        assert j["relation"] == \
            "unsubstantiated_absolute_docstring_claim"
        assert j["probe"] is False
        assert (j["expected_label"] == "ADMITS") == \
            (entry["role"] == "positive")
        assert entry["expected_label"] == j["expected_label"]
    assert set(fixtures) == {
        "m4h-P%d" % i for i in range(1, 7)} | {
        "m4h-C%d" % i for i in range(1, 7)}
    for i in range(1, 7):
        assert fixtures["m4h-C%d" % i]["rationale"]
        p, c = fixtures["m4h-P%d" % i], fixtures["m4h-C%d" % i]
        assert p["role"] == "positive" and c["role"] == "control"
        assert MANIFEST["thresholds"]["controls_allowed_fired"] == 0
        assert MANIFEST["thresholds"]["positives_fired_min"] == 6
    # disjointness: the canonical M4 claim text appears nowhere
    for j in fixtures.values():
        blob = json.dumps(j)
        assert M4_CLAIM not in blob
    # scenario variety: six distinct module paths across positives
    paths = {fixtures["m4h-P%d" % i]["finding"]["file"]
             for i in range(1, 7)}
    assert len(paths) == 6
    # C3 carries the in-diff substantiation (two files)
    c3 = fixtures["m4h-C3"]["fixture"]["input"]["files"]
    assert len(c3) == 2 and any(
        f["path"] == "cli/main.py" for f in c3)


def test_no_implementation_exists():
    assert not (REPO / "eval" / "v21_m4_relation.py").exists()
    assert not list((REPO / "eval" / "evidence").glob(
        "v21-m4rel-qualification-*"))
    assert MANIFEST["authorship"][
        "authored_before_implementation"] is True
    assert MANIFEST["thresholds"][
        "threshold_frozen_before_first_execution"] is True
    assert MANIFEST["oracle_version"] == rc.oracle_version()
    assert MANIFEST["amendments"] == []


def test_protocol_and_standing_truths():
    protocol = (PREREG / "PROTOCOL.md").read_text()
    for phrase in ("preregistration only",
                   "before any candidate",
                   "oracle-role, source-record, or record-index",
                   "zero firings on all 77",
                   "preserving an extra blocker fails",
                   "zero of the 30 controls",
                   "before first",
                   "never tuned post hoc",
                   "never self-grants preservation",
                   "18C rule",
                   "2/2 fired",
                   "unsubstantiated_absolute_docstring_claim"):
        assert phrase in protocol, phrase
    r18d = json.loads(
        (REPO / "eval" / "evidence" /
         "v21-contract-generalization-eval-2026-09-22" /
         "generalization-report-18d.json").read_text())
    for name, rec in r18d["per_relation"].items():
        assert rec["verdict"] == (
            "GENERALIZATION_PASS" if name == PSD
            else "GENERALIZATION_FAIL")
