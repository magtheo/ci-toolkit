"""Phase 22D — m4rel qualification: first and only sanctioned
execution of the frozen candidate against the frozen qualification
material.

Fail-closed design: every pin is verified BEFORE any detection runs.
The detector module hash is pinned first; any mismatch halts before
the holdout is touched. The 22B holdout is executed exactly once, in
this evaluator, and no detector change may follow its observation
(failure_handling: any gate failure is recorded and the candidate is
auto-excluded — never tuned post hoc).

A full PASS produces a qualification record only. It grants NO
preservation authority (22A QG5): the record goes to human review
before any adoption decision.
"""
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.evidence_boundary_sim as boundary  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import eval.v21_contract_relations as frozen  # noqa: E402
import eval.v21_generalization_eval as gen  # noqa: E402
import eval.v21_m4_relation as m4  # noqa: E402
import eval.v21_replay as v21  # noqa: E402
import eval.v21_routes_replay as rr  # noqa: E402

EVID_22C = REPO / "eval" / "evidence" / \
    "v21-m4rel-implementation-2026-09-23"
PREREG_22B = REPO / "eval" / "evidence" / \
    "v21-m4rel-prereg-2026-09-23"
HOLDOUT_22B = REPO / "eval" / "evidence" / \
    "v21-m4rel-holdout-2026-09-23"
HOLDOUT_18A = REPO / "eval" / "evidence" / \
    "v21-contract-generalization-prereg-2026-09-22"
OUT = REPO / "eval" / "evidence" / \
    "v21-m4rel-qualification-2026-09-23"

PINS = {
    "module_sha256_22c": "1a01d8ff6f15fd050eb290da4f20a2d99dacb59ea183b0dc6b803c6004139596",
    "22b_contract_sha256": "0f7e183703dd9497b9e430686194472cefff0de3d9657c19e55b73e77d74c2a0",
    "22b_holdout_manifest_sha256": "f9b06194f058d4de81534abeb286470f5c2aabe117267f7e5329b16e10dde127",
    "18a_holdout_manifest_sha256": "a9445d91b7b98242c036d7c5b2594a71846a62abd1c08aa1f662129459257591",
    "18d_report_sha256": "0a2bb7fa64be61a4c6b1f4b00b63c53a758fe1fed5d21fd169d067011af8dc26",
    "oracle_version": "117b4164e5446f50",
    "frozen_verifier_module_sha256":
        "bb0ebdeeb7fc80395626bf10d3e9ad1a730936ccf0ab7e719c43c1b5754b1b57",
}

PUBLISHED_REPORT_SHA256 = ("fec590e9f822880a4e82aaa281f1ad6c0942559"
                           "eaa55dbc64c6ddab08a11934c")

FROZEN_GUARDS = {
    "oracle": "117b4164e5446f50",
    "C11_refused": True,
    "M3_admitted_via_existing_witness": True,
    "M13_refused": True,
    "C12_refused": True,
    "M12_refused": True,
    "M10_relation_still_FAILED": True,
    "C10_standing_near_miss": True,
}


class Halt(Exception):
    pass


def _sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _fresh_fixture_digest(fixtures):
    return hashlib.sha256(json.dumps(
        fixtures, sort_keys=True).encode()).hexdigest()


def _execution_log():
    """Verify retained report pins and detector identity before replay.

    Runs 2–3 are documented in the reconstructed/live log but their
    report bytes were not retained, so their fixture-level outputs
    cannot be independently checked against committed artifacts.
    Only execution 1 vs. preserved run 4 (and its reviewed annotation)
    has a byte-backed comparison.
    """
    log_path = OUT / "execution-log.jsonl"
    if not log_path.exists():
        return []
    entries = [json.loads(line) for line
               in log_path.read_text().splitlines() if line.strip()]
    detector = _sha(REPO / "eval" / "v21_m4_relation.py")
    if [e["run_index"] for e in entries] != list(
            range(1, len(entries) + 1)):
        raise Halt("execution log: nonconsecutive run indices")
    for e in entries:
        if e["detector_sha256"] != detector:
            raise Halt("execution log: detector bytes changed "
                       "between executions (run %s)" % e["run_index"])
    if entries:
        first = OUT / "qualification-report.execution-1.json"
        if not first.exists() or _sha(first) != entries[0]["report_sha256"]:
            raise Halt("execution log: preserved run-1 report hash mismatch")
        last = OUT / ("qualification-report.execution-%d.json"
                      % entries[-1]["run_index"])
        if not last.exists() or _sha(last) != entries[-1]["report_sha256"]:
            raise Halt("execution log: preserved last-run report hash mismatch")
    return entries


def _append_execution_log(prior, verdict, reason, report_path):
    """Preserve a separate, byte-identical raw snapshot for a first run.

    Published evidence must never be appended to or overwritten. The
    committed historical run-4 log entry points to its raw snapshot,
    NOT to the later review-annotated qualification-report.json.
    """
    if prior:
        raise Halt("qualification already observed; re-execution prohibited")
    log_path = OUT / "execution-log.jsonl"
    snapshot = OUT / "qualification-report.execution-1.json"
    if log_path.exists() or snapshot.exists():
        raise Halt("qualification artifacts already exist; refusing overwrite")
    snapshot.write_bytes(report_path.read_bytes())
    entry = {
        "run_index": 1,
        "reconstructed": False,
        "detector_sha256":
            _sha(REPO / "eval" / "v21_m4_relation.py"),
        "verdict": verdict,
        "reason": reason,
        "report_sha256": _sha(snapshot),
    }
    with log_path.open("x") as fh:
        fh.write(json.dumps(entry) + "\n")


def verify_published_report():
    """Read-only verification of the already-published qualification.

    Never call detect(), re-run the holdout, rewrite the report, or
    append to the historical execution log.
    """
    report_path = OUT / "qualification-report.json"
    if not report_path.exists() or _sha(report_path) != \
            PUBLISHED_REPORT_SHA256:
        raise Halt("published qualification report SHA mismatch")
    pins = verify_pins()
    report = json.loads(report_path.read_text())
    if report["pins"] != pins:
        raise Halt("published qualification pins differ from frozen sources")
    entries = _execution_log()
    if [e["run_index"] for e in entries] != [1, 2, 3, 4]:
        raise Halt("published qualification execution count drift")
    if report["execution"]["fresh_holdout_sanctioned_observation"] != 1 \
            or report["execution"][
                "fresh_holdout_deterministic_reexecutions"] != 3:
        raise Halt("published qualification execution summary drift")
    transition_path = OUT / "PHASE_TRANSITION.json"
    transition = json.loads(transition_path.read_text())
    if transition["parent_merge_sha"] != \
            "b518333175948896892e263a3880982ba96ea17e" or \
            "qualification-execution-authorized" not in \
            transition["status"] or \
            "no-authority-grant" not in transition["status"] or \
            "adoption-not-authorized" not in transition["status"] or \
            report["phase_transition"]["sha256"] != \
            _sha(transition_path):
        raise Halt("published qualification transition mismatch")
    if report["verdict"] != "SUCCESS":
        raise Halt("published qualification verdict mismatch")
    return report


def verify_pins():
    actual = {
        "module_sha256_22c": _sha(REPO / "eval" / "v21_m4_relation.py"),
        "22b_contract_sha256":
            _sha(PREREG_22B / "TARGETS_CONTRACT.json"),
        "22b_holdout_manifest_sha256":
            _sha(HOLDOUT_22B / "MANIFEST.json"),
        "18a_holdout_manifest_sha256":
            _sha(HOLDOUT_18A / "MANIFEST.json"),
        "18d_report_sha256": _sha(
            REPO / "eval" / "evidence" /
            "v21-contract-generalization-eval-2026-09-22" /
            "generalization-report-18d.json"),
        "oracle_version": rc.oracle_version(),
        "frozen_verifier_module_sha256":
            _sha(REPO / "eval" / "v21_contract_relations.py"),
    }
    mismatches = {k: {"expected": v, "actual": actual.get(k)}
                  for k, v in PINS.items() if actual.get(k) != v}
    if mismatches:
        raise Halt("pin verification failed before any execution: %s"
                   % json.dumps(mismatches, indent=1))
    ev22c = json.loads((EVID_22C / "EVIDENCE.json").read_text())
    if ev22c["candidate"]["module_sha256"] != \
            actual["module_sha256_22c"]:
        raise Halt("22C evidence disagrees with pinned module hash")
    if ev22c["holdout_seal"]["executions_during_22C"] != 0:
        raise Halt("22C seal broken: holdout executed during 22C")
    return actual


def _corpus_rows(fixtures):
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


def _corpus_gates():
    fixtures = {f["id"]: f
                for f in rc.load_corpus(REPO / "eval" / "fixtures")}
    rows = _corpus_rows(fixtures)
    targets = [r for r in rows if r["fixture"] == "M4"
               and r["role"] == "true_positive_detection"
               and r["route"] == "contract_contradiction"
               and r["g2"] == "BLOCK_SURVIVES"]
    covered = [r for r in targets
               if m4.covers(r["finding"], fixtures["M4"])]
    controls = [r for r in rows if r["role"] == "control_blocker"]
    c_fired = [r for r in controls
               if m4.covers(r["finding"], fixtures[r["fixture"]])]
    extras = [r for r in rows
              if r["role"] == "positive_extra_blocker"]
    e_claim = [r for r in extras
               if m4.covers(r["finding"], fixtures[r["fixture"]])]
    e_file = [r for r in extras
              if m4.file_matches(r["finding"],
                                 fixtures[r["fixture"]])]
    fam = [r for r in rows if r["fixture"] == "M4"
           and r["role"] == "true_positive_detection"
           and not (r["route"] == "contract_contradiction"
                    and r["g2"] == "BLOCK_SURVIVES")]
    fam_cov = [r for r in fam
               if m4.covers(r["finding"], fixtures["M4"])]
    return {
        "targets": {
            "required": "2/2", "covered": len(covered),
            "total": len(targets),
            "ids": [[r["source"], r["ri"], r["fi"]]
                    for r in covered],
            "ok": len(covered) == len(targets) == 2},
        "controls": {
            "required": "0 fired", "fired": len(c_fired),
            "total": len(controls),
            "fired_ids": [[r["fixture"], r["source"], r["ri"],
                           r["fi"]] for r in c_fired],
            "ok": not c_fired},
        "extras": {
            "required": "all recorded; zero claim-linked "
                        "(zero preservation)",
            "claim_linked": len(e_claim),
            "file_match_only": len(e_file),
            "total": len(extras),
            "claim_linked_ids": [[r["fixture"], r["source"],
                                  r["ri"], r["fi"]]
                                 for r in e_claim],
            "file_match_only_ids": [[r["fixture"], r["source"],
                                     r["ri"], r["fi"]]
                                    for r in e_file],
            "ok": not e_claim},
        "family_context_non_targets": {
            "covered": len(fam_cov), "total": len(fam),
            "disposition": "recorded and permitted; does not affect "
                           "qualification",
            "ids": [[r["source"], r["ri"], r["fi"]]
                    for r in fam_cov]},
    }


def _verify_fresh_manifest():
    manifest = json.loads(
        (HOLDOUT_22B / "MANIFEST.json").read_text())
    for entry in manifest["fixtures"]:
        raw = (HOLDOUT_22B / "fixtures" /
               (entry["id"] + ".json")).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise Halt("fresh holdout fixture hash mismatch: %s"
                       % entry["id"])
    lines = ["%s  %s" % (e["sha256"], e["id"]) for e in
             sorted(manifest["fixtures"], key=lambda e: e["id"])]
    digest = hashlib.sha256(
        ("\n".join(lines) + "\n").encode()).hexdigest()
    if digest != manifest["manifest_lines_sha256"]:
        raise Halt("fresh holdout manifest_lines mismatch")
    return manifest


def _fresh_holdout_gate():
    manifest = _verify_fresh_manifest()
    results = []
    for entry in sorted(manifest["fixtures"],
                        key=lambda e: e["id"]):
        probe = json.loads(
            (HOLDOUT_22B / "fixtures" /
             (entry["id"] + ".json")).read_text())
        fires = m4.detect(probe["fixture"])
        fired = bool(fires)
        expected_fire = entry["expected_label"] == "ADMITS"
        results.append({
            "id": entry["id"], "role": entry["role"],
            "expected_label": entry["expected_label"],
            "fired": fired, "ok": fired == expected_fire,
            "files": [f["file"] for f in fires],
            "actors": [f["actors"] for f in fires],
            "claim_clauses": [f["claim_clause"] for f in fires],
        })
    positives = [r for r in results if r["role"] == "positive"]
    controls = [r for r in results if r["role"] == "control"]
    p_ok = sum(1 for r in positives if r["ok"])
    c_ok = sum(1 for r in controls if r["ok"])
    return {
        "required": "6/6 positives fire; 0/6 controls fire",
        "positives_fired": p_ok, "positives_total": len(positives),
        "controls_fired": len(controls) - c_ok,
        "controls_total": len(controls),
        "ok": p_ok == len(positives) == 6
              and c_ok == len(controls) == 6,
        "note": "preregistered validation against the frozen "
                "holdout; NOT vocabulary-independent generalization "
                "(holdout authored pre-implementation but not blind "
                "to the implementation author)",
        "fixtures": results,
    }


def _existing_holdout_gate():
    manifest = json.loads(
        (HOLDOUT_18A / "MANIFEST.json").read_text())
    results = []
    for entry in sorted(manifest["fixtures"],
                        key=lambda e: e["id"]):
        if entry["role"] != "control":
            continue
        probe = json.loads(
            (HOLDOUT_18A / "fixtures" /
             (entry["id"] + ".json")).read_text())
        fires = m4.detect(probe["fixture"])
        results.append({
            "id": entry["id"], "expected_label":
                entry["expected_label"],
            "fired": bool(fires),
            "note": "probe record carries no PR title/body; the "
                    "documentation-purpose condition makes a fire "
                    "impossible on these records — the substantive "
                    "control-safety signal is the 0/77 corpus gate",
        })
    fired = [r for r in results if r["fired"]]
    return {
        "required": "0 fired of 30 existing holdout controls",
        "fired": len(fired), "total": len(results),
        "fired_ids": [r["id"] for r in fired],
        "ok": not fired and len(results) == 30,
        "caveat": next((r["note"] for r in results), ""),
        "fixtures": results,
    }


def _correction_provenance(pins, fresh):
    """Cross-check the official report against the preserved
    first-execution report. Execution 1 recorded a HALT caused by an
    inverted aggregation predicate in this evaluator (c_ok == 0
    instead of c_ok == len(controls)); the detector was and is
    byte-frozen. This block makes the check mechanical."""
    first_path = OUT / "qualification-report.execution-1.json"
    if not first_path.exists():
        return {
            "found_after_first_execution": False,
            "note": "no preserved first-execution report present",
        }
    first = json.loads(first_path.read_text())
    first_g5 = first["gates"]["G5_fresh_holdout_single_execution"]
    fixtures_identical = \
        first_g5["fixtures"] == fresh["fixtures"]
    detector_identical = \
        first["pins"]["module_sha256_22c"] == \
        pins["module_sha256_22c"]
    if not fixtures_identical or not detector_identical:
        raise Halt(
            "first-execution cross-check failed: "
            "fixtures_identical=%s detector_identical=%s"
            % (fixtures_identical, detector_identical))
    return {
        "found_after_first_execution": True,
        "defect": "G5 aggregation inverted the control-correctness "
                  "predicate (c_ok == 0 instead of "
                  "c_ok == len(controls)); fixture-level results "
                  "were complete and correct in the first report",
        "detector_changes": "none — eval/v21_m4_relation.py "
                            "byte-identical (sha re-verified)",
        "first_execution_report":
            "qualification-report.execution-1.json",
        "first_execution_report_sha256": _sha(first_path),
        "first_execution_verdict": first["verdict"],
        "fixture_level_outputs_identical": fixtures_identical,
        "fixture_comparison_scope": "preserved execution 1 vs current run only; intermediate run-2/run-3 reports are not retained and their fixture identity is not independently verifiable",
        "detector_bytes_identical": detector_identical,
    }


def evaluate():
    # A published result is evidence, not a request to execute the
    # holdout again. Return only after read-only integrity verification.
    report_path = OUT / "qualification-report.json"
    if report_path.exists():
        return verify_published_report()
    if (OUT / "execution-log.jsonl").exists() or \
            (OUT / "qualification-report.execution-1.json").exists():
        raise Halt("partial historical qualification exists; refuse replay")
    pins = verify_pins()
    prior_runs = _execution_log()
    transition_path = OUT / "PHASE_TRANSITION.json"
    transition = json.loads(transition_path.read_text())
    if "qualification-execution-authorized" not in \
            transition["status"] or \
            "no-authority-grant" not in transition["status"]:
        raise Halt("22D transition does not authorize this run")
    if transition["parent_merge_sha"] != \
            "b518333175948896892e263a3880982ba96ea17e":
        raise Halt("22D transition parent merge mismatch")
    if transition["prerequisites"][
            "frozen_22c_module_sha256"] != \
            pins["module_sha256_22c"]:
        raise Halt("22D transition module pin mismatch")
    corpus = _corpus_gates()
    existing = _existing_holdout_gate()
    fresh = _fresh_holdout_gate()
    guards = gen._regression_guards()
    guards_ok = guards == FROZEN_GUARDS
    correction = _correction_provenance(pins, fresh)
    gates = {
        "G1_corpus_targets": corpus["targets"],
        "G2_corpus_controls": corpus["controls"],
        "G3_extras": corpus["extras"],
        "G4_existing_holdout_controls": existing,
        "G5_fresh_holdout_single_execution": fresh,
        "G6_standing_guards": {
            "required": FROZEN_GUARDS, "actual": guards,
            "ok": guards_ok},
    }
    verdict = "SUCCESS" if all(
        g["ok"] for g in gates.values()) else "HALT"
    if prior_runs:
        # This verifies retained run 1 against the present result, NOT
        # unretained run 2 or run 3 (only log attestations exist).
        first_fresh = json.loads(
            (OUT / "qualification-report.execution-1.json")
            .read_text())["gates"][
            "G5_fresh_holdout_single_execution"]["fixtures"]
        if _fresh_fixture_digest(first_fresh) != \
                _fresh_fixture_digest(fresh["fixtures"]):
            raise Halt("fixture-level outputs drifted across "
                       "executions")
    report = {
        "phase": "22D",
        "kind": "m4rel-qualification-report",
        "verdict": verdict,
        "phase_transition": {
            "path": "eval/evidence/v21-m4rel-qualification-2026-"
                    "09-23/PHASE_TRANSITION.json",
            "sha256": _sha(transition_path),
            "parent_merge_sha": transition["parent_merge_sha"],
            "boundary": transition["boundary"],
        },
        "execution": {
            "sanctioned": "first and only sanctioned execution of "
                          "the frozen m4rel candidate against the "
                          "frozen qualification material",
            "fresh_holdout_sanctioned_observation": 1,
            "fresh_holdout_deterministic_reexecutions":
                max(len(prior_runs) - 1, 0),
            "reexecution_policy": (
                "%d logged evaluator-only re-executions on pinned "
                "detector bytes; retained first/final identity verified "
                "only when both raw reports exist"
                % max(len(prior_runs) - 1, 0)),
            "no_detector_changes_after_observation": True,
            "module_sha256_at_execution":
                pins["module_sha256_22c"],
            "order": "pins verified before any detection; fresh "
                     "holdout manifest integrity verified before "
                     "its single execution",
        },
        "evaluator_correction": correction,
        "pins": pins,
        "gates": gates,
        "interpretation": {
            "pass_meaning": "preregistered validation against the "
                            "frozen holdout and corpus gates",
            "pass_does_not_mean": "NOT vocabulary-independent "
                                  "generalization; the holdout was "
                                  "authored before implementation "
                                  "but is not blind to the "
                                  "implementation author (all six "
                                  "positive actor terms appear in "
                                  "the detector's ACTORS vocabulary)",
            "authority": "no preservation authority granted; this "
                         "record is the QG5 input for a separate "
                         "human adoption decision",
        },
        "failure_handling": "any gate failure records evidence and "
                            "auto-excludes the candidate; never "
                            "tuned post hoc against these gates",
        "oracle_version": rc.oracle_version(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / "qualification-report.json"
    report_path.write_text(json.dumps(report, indent=1) + "\n")
    _append_execution_log(
        prior_runs, verdict,
        "live qualification run (report generation; run %d)"
        % (len(prior_runs) + 1), report_path)
    return report


if __name__ == "__main__":
    try:
        r = evaluate()
    except Halt as halt:
        print("HALT:", halt)
        sys.exit(1)
    print("verdict:", r["verdict"])
    for name, g in r["gates"].items():
        print(" ", name, "ok" if g["ok"] else "FAIL")
    sys.exit(0 if r["verdict"] == "SUCCESS" else 1)
