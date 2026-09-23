"""Phase-18A holdout artifact validation.

Mechanical checks only: counts, pair structure, labels, uniqueness,
hash pins, frozen Phase-17 verifier identity. These tests must NOT
import or call the relation verifier on the holdout — evaluation is
Phase 18B, performed for the first time after this phase merges.
"""
import hashlib
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
HOLDOUT = REPO / "eval" / "evidence" / \
    "v21-contract-generalization-prereg-2026-09-22"

RELATIONS = (
    "pinned_sha_demoted_to_branch",
    "preserved_claim_vs_dropped_call_result",
    "consume_before_validate_ordering",
    "secret_logged_by_echo",
    "doc_self_contradiction",
    "jsonl_format_vs_unslurped_jq",
)
FROZEN_MERGE_SHA = "0631b0956f795ab1ee6d13f68b0c1cebe8a6d23b"
FROZEN_MODULE_SHA = ("bb0ebdeeb7fc80395626bf10d3e9ad1a730936ccf0a"
                     "b7e719c43c1b5754b1b57")
FROZEN_MANIFEST_SHA = ("a9445d91b7b98242c036d7c5b2594a71846a62abd1c0"
                       "8aa1f662129459257591")
SHORT = {
    "pinned_sha_demoted_to_branch": "psd",
    "preserved_claim_vs_dropped_call_result": "pcd",
    "consume_before_validate_ordering": "cbv",
    "secret_logged_by_echo": "sle",
    "doc_self_contradiction": "dsc",
    "jsonl_format_vs_unslurped_jq": "jfu",
}


def _manifest():
    return json.loads((HOLDOUT / "MANIFEST.json").read_text())


def _fixture(fid):
    return json.loads((HOLDOUT / "fixtures" / (fid + ".json")).read_text())


def test_counts_pair_structure_and_labels():
    manifest = _manifest()
    assert manifest["counts"] == {
        "relations": 6, "pairs_per_relation": 5,
        "positives": 30, "controls": 30, "total": 60}
    assert len(manifest["fixtures"]) == 60
    by_relation = {}
    for entry in manifest["fixtures"]:
        fixture = _fixture(entry["id"])
        assert fixture["id"] == entry["id"]
        assert fixture["relation"] == entry["relation"]
        assert fixture["role"] == entry["role"]
        assert fixture["expected_label"] == entry["expected_label"]
        assert fixture["expected_label"] == (
            "ADMITS" if fixture["role"] == "positive" else "REFUSES")
        assert fixture["probe"] == entry["probe"]
        assert fixture["finding"]["file"] == \
            fixture["fixture"]["input"]["files"][0]["path"]
        assert fixture["finding"]["comment"]
        assert "+" in fixture["fixture"]["input"]["files"][0]["patch"]
        assert fixture["rationale"]
        by_relation.setdefault(
            (fixture["relation"], fixture["role"]), []).append(
                fixture["id"])
    for relation in RELATIONS:
        positives = by_relation[(relation, "positive")]
        controls = by_relation[(relation, "control")]
        assert len(positives) == 5 and len(controls) == 5
        assert {p.rsplit("-", 1)[1] for p in positives} == \
            {"P1", "P2", "P3", "P4", "P5"}
        assert {c.rsplit("-", 1)[1] for c in controls} == \
            {"C1", "C2", "C3", "C4", "C5"}
        assert all(p.startswith(SHORT[relation] + "-")
                   for p in positives + controls)
    probes = {e["id"] for e in manifest["fixtures"] if e["probe"]}
    assert probes == {
        "cbv-P2", "cbv-P3", "cbv-P4", "cbv-P5",
        "pcd-P3", "pcd-P4",
        "sle-P4", "sle-P5",
        "jfu-P2",
    }
    assert not any(e["probe"] and e["role"] != "positive"
                   for e in manifest["fixtures"])


def test_hash_pins_and_uniqueness():
    manifest_path = HOLDOUT / "MANIFEST.json"
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == \
        FROZEN_MANIFEST_SHA
    manifest = _manifest()
    seen_content = set()
    for entry in manifest["fixtures"]:
        raw = (HOLDOUT / "fixtures" / (entry["id"] + ".json")).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == entry["sha256"], entry["id"]
        assert raw not in seen_content, "duplicate fixture content"
        seen_content.add(raw)
    entries = sorted(manifest["fixtures"], key=lambda e: e["id"])
    lines = ["%s  %s" % (e["sha256"], e["id"]) for e in entries]
    recomputed = hashlib.sha256(
        ("\n".join(lines) + "\n").encode()).hexdigest()
    assert recomputed == manifest["manifest_lines_sha256"]


def test_frozen_verifier_identity():
    manifest = _manifest()
    assert manifest["frozen_verifier"]["merge_sha"] == FROZEN_MERGE_SHA
    assert manifest["frozen_verifier"]["module"] == \
        "eval/v21_contract_relations.py"
    current = hashlib.sha256(
        (REPO / "eval" / "v21_contract_relations.py").read_bytes()
    ).hexdigest()
    assert current == FROZEN_MODULE_SHA
    assert manifest["frozen_verifier"]["module_sha256"] == \
        FROZEN_MODULE_SHA
    assert manifest["oracle_version"] == "117b4164e5446f50"


def test_protocol_contains_binding_rules():
    protocol = (HOLDOUT / "PROTOCOL.md").read_text()
    assert "must NOT be executed against the holdout during" in protocol
    assert "GENERALIZATION FAIL" in protocol
    assert "no blanket promotion" in protocol
    assert "reviewed amendment" in protocol
    assert FROZEN_MERGE_SHA in protocol
    assert "117b4164e5446f50" in protocol
    assert "C10 remains a standing near-miss" in protocol


# NOTE: by design, this module never imports or calls the Phase-17
# relation verifier against the holdout; evaluation is Phase 18B.
