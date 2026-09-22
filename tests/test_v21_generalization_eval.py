"""Phase-18B evaluation pins (frozen thresholds, exact outcomes)."""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.v21_generalization_eval as eval18b  # noqa: E402


def _report():
    return eval18b.evaluate()


def test_frozen_identity_and_standing_guards():
    report = _report()
    assert report["oracle_version"] == "117b4164e5446f50"
    assert report["frozen_verifier"]["merge_sha"] == \
        "0631b0956f795ab1ee6d13f68b0c1cebe8a6d23b"
    guards = report["standing_regression_guards"]
    assert guards["C11_refused"] and guards["M13_refused"]
    assert guards["C12_refused"] and guards["M12_refused"]
    assert guards["M3_admitted_via_existing_witness"]
    assert guards["M10_relation_still_FAILED"]
    assert guards["C10_standing_near_miss"]


def test_per_relation_verdicts_are_pinned():
    per = _report()["per_relation"]
    expected = {
        "pinned_sha_demoted_to_branch": (4, 0, "GENERALIZATION_PASS"),
        "preserved_claim_vs_dropped_call_result": (
            3, 0, "GENERALIZATION_FAIL"),
        "consume_before_validate_ordering": (1, 0, "GENERALIZATION_FAIL"),
        "secret_logged_by_echo": (3, 1, "GENERALIZATION_FAIL"),
        "doc_self_contradiction": (2, 2, "GENERALIZATION_FAIL"),
        "jsonl_format_vs_unslurped_jq": (3, 0, "GENERALIZATION_FAIL"),
    }
    for relation, (tp, leak, verdict) in expected.items():
        got = per[relation]
        assert got["positives_admitted"] == tp, relation
        assert got["controls_admitted"] == leak, relation
        assert got["verdict"] == verdict, relation


def test_failed_and_leaked_fixture_ids_are_exact():
    per = _report()["per_relation"]
    assert per["preserved_claim_vs_dropped_call_result"][
        "failed_positive_ids"] == ["pcd-P3", "pcd-P4"]
    assert per["consume_before_validate_ordering"][
        "failed_positive_ids"] == ["cbv-P2", "cbv-P3", "cbv-P4", "cbv-P5"]
    assert per["secret_logged_by_echo"]["failed_positive_ids"] == \
        ["sle-P4", "sle-P5"]
    assert per["secret_logged_by_echo"]["leaked_control_ids"] == ["sle-C3"]
    assert per["doc_self_contradiction"]["failed_positive_ids"] == \
        ["dsc-P3", "dsc-P4", "dsc-P5"]
    assert per["doc_self_contradiction"]["leaked_control_ids"] == \
        ["dsc-C1", "dsc-C2"]
    assert per["jsonl_format_vs_unslurped_jq"]["failed_positive_ids"] == \
        ["jfu-P2", "jfu-P5"]
    assert per["pinned_sha_demoted_to_branch"]["leaked_control_ids"] == []


def test_aggregate_is_no_blanket_promotion():
    aggregate = _report()["aggregate"]
    assert aggregate == {
        "positives_admitted": 16, "positives_total": 30,
        "controls_admitted": 3, "controls_total": 30,
        "relations_pass": 1, "all_pass": False,
    }


def test_psd_p4_invalid_defect_is_recorded():
    defects = _report()["fixture_defects"]
    assert set(defects) == {"psd-P4"}
    proof = defects["psd-P4"]["proof"]
    assert proof["lengths"] == [39]
    assert defects["psd-P4"]["disposition"].startswith("INVALID pair")


def test_fail_closed_on_verifier_drift():
    import copy
    manifest = copy.deepcopy(eval18b.json.loads(
        (eval18b.HOLDOUT / "MANIFEST.json").read_text()))
    manifest["frozen_verifier"]["module_sha256"] = "0" * 64
    try:
        eval18b._fail_closed(manifest)
    except RuntimeError as exc:
        assert "different verifier module" in str(exc)
    else:
        raise AssertionError("drifted verifier identity was accepted")
