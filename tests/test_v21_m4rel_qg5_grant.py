"""Phase-22E m4rel QG5 grant record checks.

The grant is PROPOSED: these tests pin its scope, its evidence pins
(distinguished original/annotated/HALT reports), its mechanical
effect on the frozen corpus (exactly the two named rows; zero control
or extra preservation), the retained limitations, and the unresolved
PC2. Effectiveness is a human merge decision — the tests assert the
record says so.
"""
import hashlib
import json
import pathlib
import sys
from collections import Counter

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import eval.evidence_boundary_sim as boundary  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import eval.v21_contract_relations as frozen  # noqa: E402
import eval.v21_m4_relation as m4  # noqa: E402
import eval.v21_replay as v21  # noqa: E402
import eval.v21_routes_replay as rr  # noqa: E402

GRANT_DIR = REPO / "eval" / "evidence" / \
    "v21-m4rel-qg5-grant-2026-09-23"
RECORD = json.loads((GRANT_DIR / "GRANT_RECORD.json").read_text())
QUAL = REPO / "eval" / "evidence" / \
    "v21-m4rel-qualification-2026-09-23"

MODULE_SHA = "1a01d8ff6f15fd050eb290da4f20a2d99dacb59ea183b0dc6b803c6004139596"
RUN4_SHA = "a4ebaabac2dea4c662541f433aeb580bd91d301e45dde576ce3688eb4a422c1f"
ANNOTATED_SHA = "fec590e9f822880a4e82aaa281f1ad6c0942559eaa55dbc64c6ddab08a11934c"
HALT_SHA = "b368b5a4dcb7dbd9113e60cfbd514c8e17447722e60ca8748beae85620a13aa2"


def _sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def test_grant_is_proposed_not_effective():
    assert RECORD["status"] == \
        "proposed-grant--effective-only-upon-human-merge-" \
        "acceptance-of-the-22E-PR"
    assert "agents never grant authority" in RECORD["governance"]
    assert "human merge acceptance" in RECORD["governance"]


def test_scope_table_and_exclusions():
    scope = RECORD["grant_scope"]
    assert scope["authority_type"] == "preservation only"
    assert scope["candidate_sha256"] == MODULE_SHA
    assert scope["eligible_decision"] == \
        "an existing blocking row with g2_contract_aware == " \
        "BLOCK_SURVIVES"
    assert scope["route"] == "contract_contradiction only"
    assert "claim-linked, not merely same-file" in \
        scope["evidence_requirement"]
    assert scope["effect"].startswith(
        "exempt an eligible existing block")
    for excl in ("no admission", "no block creation",
                 "no extra-blocker preservation",
                 "no route expansion", "no GATING activation",
                 "no deployed change"):
        assert excl in scope["exclusions"]
    assert "NOT an unrestricted exemption" in \
        RECORD["scope_interpretation"]


def test_evidence_pins_distinguished():
    pins = RECORD["evidence_pins"]
    assert pins["original_run4_report"]["sha256"] == RUN4_SHA
    assert pins["original_run4_report"]["sha256"] == _sha(
        QUAL / "qualification-report.execution-4.json")
    assert pins["review_annotated_published_report"][
        "sha256"] == ANNOTATED_SHA
    assert pins["review_annotated_published_report"]["sha256"] == \
        _sha(QUAL / "qualification-report.json")
    assert pins["preserved_first_run_halt"]["sha256"] == HALT_SHA
    assert pins["preserved_first_run_halt"]["sha256"] == _sha(
        QUAL / "qualification-report.execution-1.json")
    assert pins["pr106_merge_sha"] == \
        "9a962c08dc90947ecdf5b6c3f67d212cf82915a2"
    assert pins["22d_phase_transition"]["sha256"] == _sha(
        QUAL / "PHASE_TRANSITION.json")
    assert pins["22b_contract_sha256"] == _sha(
        REPO / "eval" / "evidence" /
        "v21-m4rel-prereg-2026-09-23" / "TARGETS_CONTRACT.json")
    assert pins["oracle_version"] == rc.oracle_version()
    assert pins["frozen_verifier_module_sha256"] == _sha(
        REPO / "eval" / "v21_contract_relations.py")
    assert pins["original_run4_report"]["sha256"] != \
        pins["review_annotated_published_report"]["sha256"]


def test_limitations_retained():
    lims = " ".join(RECORD["retained_limitations"])
    assert "NOT vocabulary-independent generalization" in lims
    assert "not blind to the implementation author" in lims
    assert "first and final reports only" in lims
    assert "disclosed execution log" in lims
    assert "evaluator aggregation defect" in lims
    assert "0/77 corpus gate" in lims


def test_mechanical_effect_rederived():
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
                rows.append(dict(
                    role=v21._role(finding, fixture),
                    route=rr.route_of(finding, fixture, sim),
                    g2=sim["g2_contract_aware"],
                    preds=v21.predicate_names(finding, fixture),
                    rels=set(frozen.relation_names(finding,
                                                   fixture)),
                    fixture=rec["fixture"], source=source,
                    ri=ri, fi=fi, finding=finding))
    assert len(rows) == RECORD["mechanical_effect_on_frozen_corpus"][
        "total_blocking_rows"] == 276

    def eligible(r):
        return (r["g2"] == "BLOCK_SURVIVES"
                and r["route"] == "contract_contradiction"
                and r["role"] == "true_positive_detection"
                and m4.covers(r["finding"], fixtures[r["fixture"]]))

    elig = sorted((r["source"], r["ri"], r["fi"])
                  for r in rows if eligible(r))
    assert elig == [("b1-low", 44, 0), ("stage-a-max", 66, 0)]
    assert elig == sorted(
        tuple(x[2:]) for x in
        RECORD["mechanical_effect_on_frozen_corpus"][
            "grant_eligible_rows"])
    assert not any(r["role"] == "control_blocker" and eligible(r)
                   for r in rows)
    assert not any(r["role"] == "positive_extra_blocker"
                   and eligible(r) for r in rows)
    norole = sorted(
        (r["source"], r["ri"], r["fi"]) for r in rows
        if r["g2"] == "BLOCK_SURVIVES"
        and r["route"] == "contract_contradiction"
        and m4.covers(r["finding"], fixtures[r["fixture"]]))
    assert norole == elig
    bare = [r for r in rows
            if r["g2"] == "BLOCK_SURVIVES"
            and r["route"] == "contract_contradiction"
            and not r["preds"] and not r["rels"]]
    by_role = dict(Counter(r["role"] for r in bare))
    assert by_role == {
        "control_blocker": 15, "positive_extra_blocker": 5,
        "true_positive_detection": 2}
    falls = dict(Counter(r["role"] for r in bare
                         if not eligible(r)))
    assert falls == {"control_blocker": 15,
                     "positive_extra_blocker": 5}
    surv = [r for r in rows if r["g2"] == "BLOCK_SURVIVES"]
    assert len(surv) == 145
    relcarried = [r for r in surv
                  if r["role"] == "true_positive_detection"
                  and r["route"] == "contract_contradiction"
                  and not r["preds"] and r["rels"]
                  and "pinned_sha_demoted_to_branch" not in
                  r["rels"]]
    assert len(relcarried) == 24


def test_pc2_unresolved_and_adoption_blocked():
    assert RECORD["pc2_dsc_p4"]["status"] == "UNRESOLVED"
    assert "would still be downgraded" in \
        RECORD["pc2_dsc_p4"]["statement"]
    assert len(RECORD["pc2_dsc_p4"][
        "resolution_paths_for_adoption_design"]) == 3
    prep = RECORD["adoption_prep"]
    assert prep["status"].startswith(
        "adoption design NOT started")
    assert "blocked until PC2" in prep["status"]
    assert prep["r1_prime"] == \
        "remains non-adoptable; this grant does not adopt it"
    assert set(prep["unchanged_invariants"]) == {
        "psd admission scope untouched",
        "no baseline decision changes",
        "no GATING activation",
        "no deployed change",
        "failed relations and M10 gain no authority from this grant",
        "no runtime oracle-role branching; zero control/extra preservation must be demonstrated for the future combined policy",
    }
    assert "NO runtime oracle-role condition" in RECORD[
        "grant_scope"]["role_condition"]


def test_grant_md_consistent():
    md = (GRANT_DIR / "GRANT.md").read_text()
    for phrase in ("PROPOSED grant",
                   "agents never grant authority",
                   "exactly", "Zero controls preserved",
                   "PC2 (dsc-P4) remains open",
                   "STOPPED for human review",
                   MODULE_SHA[:8], RUN4_SHA[:12],
                   ANNOTATED_SHA[:12], "9a962c08"):
        assert phrase in md, phrase
