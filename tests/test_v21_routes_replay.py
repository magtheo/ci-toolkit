"""Offline Phase-16 claim-route replay (protocol-pinned)."""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.v21_routes_replay as routes  # noqa: E402


def _report():
    return routes.replay()


def test_population_and_gate_identity_are_frozen():
    report = _report()
    assert report["oracle_version"] == "117b4164e5446f50"
    assert len(report["phase09"]["rows"]) == 276
    gs = report["phase09"]["gate_summary"]
    assert gs["route_typed"] == gs["closed_world_predicates"] == {
        "control_blocker": {"admitted": 0, "total": 77},
        "true_positive_detection": {"admitted": 50, "total": 165},
        "positive_extra_blocker": {"admitted": 2, "total": 34},
    }
    assert gs["quote_only"]["control_blocker"] == {"admitted": 27, "total": 77}


def test_route_decomposition_is_pinned():
    summary = _report()["phase09"]["route_summary"]
    assert summary["witnessed_behavior"] == {
        "control_blocker": {"admitted": 0, "total": 0},
        "true_positive_detection": {"admitted": 21, "total": 23},
        "positive_extra_blocker": {"admitted": 1, "total": 5},
    }
    assert summary["external_fact"]["true_positive_detection"] == {
        "admitted": 0, "total": 45}
    assert summary["contract_contradiction"]["true_positive_detection"] == {
        "admitted": 29, "total": 68}
    assert summary["unwitnessed_behavior"]["true_positive_detection"] == {
        "admitted": 0, "total": 29}
    assert all(cell["total"] == 0
               for cell in summary["out_of_diff"].values())


def test_frozen_five_projection_is_pinned():
    cases = {c["case_id"]: c for c in _report()["frozen_cases"]}
    c11 = cases["C11-fabricated-contract-contradiction"]
    assert c11["route"] == "contract_contradiction"
    assert c11["route_typed"] is False
    assert c11["admission_reason"] == "no registered relation verifier"
    m3 = cases["M3-context-only-evidence-quote"]
    assert m3["route_typed"] is True
    assert m3["witnesses"] == ["parsed_date_vs_mtime"]
    m13 = cases["M13-external-fact-extrapolation"]
    assert m13["route"] == "external_fact" and m13["route_typed"] is False
    for key in ("C12-honest-uncertainty-downgrade",
                "M12-contiguous-quote-downgrade"):
        assert cases[key]["route_typed"] is False
        assert cases[key]["admission_reason"] == \
            "BLOCKING_EVIDENCE_INSUFFICIENT"


def _fixture(patch, path="wf.yml"):
    return {"input": {"files": [{"path": path, "patch": patch}]}}


def test_out_of_diff_precedes_contract_language():
    finding = {"file": "missing.py", "comment": "documented contract is "
               "contradicted by the code"}
    assert routes.route_of(finding, _fixture("+x = 1")) == "out_of_diff"


def test_witness_precedes_external_vocabulary():
    finding = {"file": "wf.yml",
               "comment": "an attacker could leak secrets because the "
                          "build reports success and discards failures"}
    patch = "+status=ok || true\n+echo done"
    assert routes.route_of(finding, _fixture(patch)) == "witnessed_behavior"
    assert "hardcoded_success_status" in routes.v21.predicate_names(
        finding, _fixture(patch))
