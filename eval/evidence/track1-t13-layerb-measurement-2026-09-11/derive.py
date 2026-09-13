#!/usr/bin/env python3
"""Deterministic derivation for the 20d layer-(b) measurement bundle.

NO model calls: reads only the committed raw reports/logs and the
frozen fixture set. Writes derived-metrics.json, narrative-coding.jsonl,
and inconclusive-audit.json next to this script.

Family coding follows the frozen iteration-2 precedents
(../track1-t13-iter2-measurement-2026-09-09/narrative-coding.jsonl):
per-fixture narrative rules, applied in order, fail-closed — a false
blocker matching no rule is coded UNMATCHED-REVIEW, never guessed.
`genuine-defect-unmatched` is a CODING-ONLY class (a narrative that
expresses the fixture's planted defect but matched no oracle needle —
the #40 M11 reclassification precedent); it is not a taxonomy family.
"""

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from run_corpus import _finding_matches  # noqa: E402
from parse_review import parse_model_output  # noqa: E402

FLOORS = {
    "haiku": {"M1": 5, "M10": 5, "M11": 5, "M12": 5, "M13": 0, "M14": 5,
              "M15": 0, "M16": 5, "M17": 0, "M18": 0, "M2": 5, "M3": 5,
              "M4": 0, "M5": 0, "M6": 0, "M7": 5, "M8": 5, "M9": 1},
    "sonnet": {"M1": 5, "M10": 5, "M11": 5, "M12": 5, "M13": 1, "M14": 5,
               "M15": 0, "M16": 5, "M17": 5, "M18": 5, "M2": 5, "M3": 5,
               "M4": 0, "M5": 0, "M6": 0, "M7": 5, "M8": 5, "M9": 5},
}
CAPS = {"haiku": {"control_fb": 78, "spec": 53}, "sonnet": {"control_fb": 112, "spec": 50}}
SPEC_AGG_CAP = 103
PRICE = {"anthropic/claude-haiku-4.5": (1.0, 5.0),
         "anthropic/claude-sonnet-4.5": (3.0, 15.0)}

# per-fixture narrative rules: (family, regex) in priority order.
R = {
    "C1": [("speculative-consequence", r"same repo|same-repo|write acce|unverif|no verification|trusted|trust|pull_request_target|fork|secrets")],
    "C2": [("speculative-consequence", r"privilege|escalation|unverif|no verification|trusted|supply.?chain|unpin")],
    "C3": [("severity-inflation", r"exit|guard|set -e"),
           ("hallucinated-fact", r"mtime|invert|inverted|parsed date|PARSED DATE")],
    "C7": [("speculative-consequence", r"scope violation|testab|mock|configurab|mechanical|import statement")],
    "C8": [("speculative-consequence", r"listener|refire|fire|double|overwrite|race|error handling|resume")],
    "C9": [("hallucinated-fact", r"merge|mergedAt|merged"),
           ("speculative-consequence", r"stdin|valid json|malformed|empty")],
    "C10": [("speculative-consequence", r"anchor|traversal|\.\./|unauthorized|pass validation|privileged")],
    "C11": [("risk-boilerplate", r"suppression|hides|>/dev/null"),
            ("hallucinated-fact", r"exits 0|exit 0|logic error"),
            ("speculative-consequence", r"npx|harness failure|status=failed|debug")],
    "C12": [("severity-inflation", r"no validation|successful status code|4xx|5xx treated"),
            ("hallucinated-fact", r"(do|does) not raise|assumed to raise|propagate|bypass|ParseError|OriginError|never awaited"),
            ("speculative-consequence", r"compromised|malicious|inject|persist|attacker|misconfigured"),
            ("risk-boilerplate", r"no test|missing test")],
    "C13": [("absolute-consistency", r"anti.?pattern|scope violation|not on merge|every PR|critical|dangerous|vulnerab"),
            ("hallucinated-fact", r"PR branch|modifies? this (very )?file|read from the PR"),
            ("speculative-consequence", r"fork check|insufficient|bypass|same repo|same-repo|attacker|branch in the")],
    "C14": [("speculative-consequence", r"unquot|spaces|injection|payload\.json|not exist|fail fast|cryptic")],
    "C15": [("risk-boilerplate", r"no test|missing test"),
            ("severity-inflation", r"any object|type hint|None or empty"),
            ("speculative-consequence", r"format string|injection|log inj|XSS|sanitiz|interpolat|attacker")],
    "C16": [("hallucinated-fact", r"endpoint|per.?label|bulk|404|405|LABELS dict|array of label|POST/PATCH|requires authentication|missing authentication"),
            ("speculative-consequence", r"injection|SSRF|path traversal|AttributeError|generic session|\.\./"),
            ("severity-inflation", r"status code|4xx|5xx|RequestException|swallow|return type|Response object"),
            ("risk-boilerplate", r"no test|missing test")],
    "M1": [("speculative-consequence", r"fork|bypass|write acce|unverif|no verification|trusted|branch")],
    "M2": [("speculative-consequence", r"pull_request_target|@main|unpin|supply.?chain|reproducib|security context|pinned")],
    "M3": [("hallucinated-fact", r"mtime|parsed date|PARSED DATE|invert|misleading"),
           ("speculative-consequence", r"silent|skip|missing|malformed|no error handling|does not exist")],
    "M7": [("hallucinated-fact", r"OPENROUTER_URL|json module|not imported|NameError|timeout|connect.max.?time|socket"),
           ("speculative-consequence", r"response|captured|discarded|error handling|URLError|HTTPError|behavior")],
    "M8": [("risk-boilerplate", r"no test|missing test"),
           ("speculative-consequence", r"resume|restoreOrResume|overwrite|race|double|ordering|error handling|state mutation|ambiguit")],
    "M9": [("hallucinated-fact", r"invert|inverted|mergedAt|merged")],
    "M11": [("genuine-defect-unmatched", r"discarded|>/dev/null|suppress|exit code|hardcoded status|diagnostic"),
            ("speculative-consequence", r"printf|special characters|malformed JSON|single qu")],
    "M12": [("genuine-defect-unmatched", r"docstring|contract violation|raises.*empty|empty dict"),
            ("risk-boilerplate", r"no test|missing test"),
            ("speculative-consequence", r"_cache|thread|concurren|race|lock|async"),
            ("hallucinated-fact", r"does not raise|propagate|never awaited|KeyError|OriginError")],
    "M13": [("absolute-consistency", r"anti.?pattern|scope violation|not on merge|every PR|critical|dangerous|vulnerab|packages:write"),
            ("speculative-consequence", r"fork check|insufficient|bypass|same repo|same-repo|attacker|branch|write acce")],
    "M14": [("genuine-defect-unmatched", r"DEPLOY_TOKEN|token.*stderr|echoed|expose.*log"),
            ("speculative-consequence", r"payload\.json|not exist|cryptic|error handling")],
    "M15": [("risk-boilerplate", r"no test|missing test"),
            ("speculative-consequence", r"format string|injection|log inj|XSS|sanitiz|interpolat|attacker|__import__")],
    "M16": [("genuine-defect-unmatched", r"fabricated|misleading|lies about success|ok.: True|ok.: true|updated.: 2|updated.*len|no labels were actually|claiming success"),
            ("hallucinated-fact", r"endpoint|malformed URL|relative path|URL construction|base URL|404|405|array of label|expects an array|json=LABELS"),
            ("speculative-consequence", r"injection|SSRF|\.\./|untrusted|user-controlled"),
            ("severity-inflation", r"return type|Response object|status"),
            ("risk-boilerplate", r"no test|missing test")],
}


def code_one(fixture, comment):
    low = comment.lower()
    for family, pattern in R.get(fixture, []):
        if re.search(pattern, low, re.I):
            return family
    return "UNMATCHED-REVIEW"


def main():
    reports = {}
    for prof in ("haiku", "sonnet"):
        reports[prof] = json.loads((HERE / f"{prof}-n5.json").read_text())

    metrics = {"profiles": {}, "frozen_criteria": {}, "floor_violations": [],
               "demotion_telemetry": {}, "spend_accounting": {},
               "incident_log": []}
    coding_rows = []
    inconclusives = []

    for prof in ("haiku", "sonnet"):
        r = reports[prof]
        model_id = ("anthropic/claude-haiku-4.5" if prof == "haiku"
                    else "anthropic/claude-sonnet-4.5")
        pin, pout = PRICE[model_id]
        sp = r["spend"]
        cost = (sp["prompt_tokens"] * pin + sp["completion_tokens"] * pout) / 1e6
        det_total = 0
        control_fb = 0
        spec_fb = 0
        dem = {"support_missing": 0, "support_vacuous": 0, "support_not_found": 0}
        kinds = {}
        per_det = {}
        for f in r["per_fixture"]:
            fid, kind = f["id"], f["kind"]
            det = sum(e["hits"] for e in f["expected_detection"])
            det_total += det
            per_det[fid] = det
            if kind == "control":
                control_fb += f["false_blockers"]
            # expected entries for FB identification
            entries = [e["entry"] for e in f["expected_detection"]]
            for i, run in enumerate(f["runs_detail"]):
                if run["assessment"] == "INCONCLUSIVE":
                    obj = parse_model_output(run["raw_output"])
                    cause = ("json-decode-or-schema" if not obj
                             else "label-evidence-mismatch")
                    inconclusives.append(
                        {"profile": prof, "fixture": fid, "run": i,
                         "cause": cause})
                for fd in run["findings"]:
                    c = fd.get("comment", "")
                    m = re.search(r"\[downgraded by support validation: ([a-z_]+)\]", c)
                    if m:
                        dem[m.group(1)] = dem.get(m.group(1), 0) + 1
                    for it in (fd.get("support") or []):
                        em = it.get("engine_match")
                        if em:
                            kinds[em["kind"]] = kinds.get(em["kind"], 0) + 1
                    if fd.get("severity") != "blocking":
                        continue
                    if any(_finding_matches(e, fd) for e in entries):
                        continue  # expected expression, not a false blocker
                    family = code_one(fid, c)
                    if family == "speculative-consequence":
                        spec_fb += 1
                    coding_rows.append({
                        "profile": prof, "fixture": fid, "kind": kind,
                        "run": i, "class": "false-blocker",
                        "family": family, "comment": c,
                        "method": "rule-table-v1 (frozen iter-2 precedents)"})
        fb_total = sum(1 for row in coding_rows if row["profile"] == prof)
        metrics["profiles"][prof] = {
            "aggregate_detection": f"{det_total}/90",
            "floor_aggregate": FLOORS[prof] and (
                51 if prof == "haiku" else 66),
            "control_false_blockers": control_fb,
            "control_fb_cap": CAPS[prof]["control_fb"],
            "false_blockers_total": fb_total,
            "speculative_consequence_fb": spec_fb,
            "spec_cap": CAPS[prof]["spec"],
            "inconclusive": sum(1 for x in inconclusives if x["profile"] == prof),
            "per_positive_detection": per_det,
        }
        metrics["demotion_telemetry"][prof] = {
            "demotions_total": sum(dem.values()), "by_reason": dem,
            "engine_match_annotations": sum(kinds.values()),
            "engine_match_kinds": kinds}
        metrics["spend_accounting"][prof] = {
            "calls": sp["calls"], "prompt_tokens": sp["prompt_tokens"],
            "completion_tokens": sp["completion_tokens"],
            "cost_upper_bound_usd": round(cost, 2),
            "pricing": "list, no cache discount"}

    # frozen-criterion table
    h, s = metrics["profiles"]["haiku"], metrics["profiles"]["sonnet"]
    floor_viol = []
    for prof in ("haiku", "sonnet"):
        for fid, fl in FLOORS[prof].items():
            det = h if prof == "haiku" else s
            d = det["per_positive_detection"].get(fid, 0)
            if d < fl:
                floor_viol.append({"profile": prof, "fixture": fid,
                                   "detected": d, "floor": fl,
                                   "delta": d - fl})
    metrics["floor_violations"] = floor_viol
    metrics["frozen_criteria"] = {
        "1_zero_gating": {
            "haiku": reports["haiku"]["gating_violations"],
            "sonnet": reports["sonnet"]["gating_violations"],
            "pass": not reports["haiku"]["gating_violations"]
            and not reports["sonnet"]["gating_violations"]},
        "2_deviation6_floors": {"violations": len(floor_viol),
                                "pass": not floor_viol,
                                "sonnet_M17": s["per_positive_detection"]["M17"]},
        "3_spec_retention": {"haiku": h["speculative_consequence_fb"],
                             "sonnet": s["speculative_consequence_fb"],
                             "aggregate": h["speculative_consequence_fb"]
                             + s["speculative_consequence_fb"],
                             "caps": "53/50/103",
                             "pass": (h["speculative_consequence_fb"] <= 53
                                      and s["speculative_consequence_fb"] <= 50
                                      and h["speculative_consequence_fb"]
                                      + s["speculative_consequence_fb"] <= 103)},
        "4_control_fb_nonregression": {
            "haiku": h["control_false_blockers"], "sonnet": s["control_false_blockers"],
            "caps": "78/112",
            "pass": h["control_false_blockers"] <= 78
            and s["control_false_blockers"] <= 112},
        "5_sonnet_c7_clean": {
            "pass": not [f for f in reports["sonnet"]["per_fixture"]
                         if f["id"] == "C7" and not f["passes_policy"]]},
    }
    pair = reports["sonnet"]["pair_integrity_violations"]
    metrics["pair_integrity_sonnet"] = pair
    total_cost = round(sum(v["cost_upper_bound_usd"] for v
                           in metrics["spend_accounting"].values()), 2)
    metrics["spend_accounting"]["total_usd_upper_bound"] = total_cost
    metrics["spend_accounting"]["cap_usd"] = 3.5
    metrics["spend_accounting"]["calls_total"] = sum(
        v["calls"] for k, v in metrics["spend_accounting"].items()
        if isinstance(v, dict) and "calls" in v)
    metrics["incident_log"] = [{
        "attempt": 1,
        "event": "blocked at call 1 — OpenRouter http 403 key weekly limit",
        "governed_calls_served": 0,
        "evidence": "commit dd59604: haiku-n5.log (verbatim 403 body)",
        "resolution": "human confirmed key reset; explicitly re-authorized "
                      "the identical frozen run against head dd59604"},
        {"attempt": 2, "event": "360/360 calls served, exits: haiku 0, "
         "sonnet 1 (policy-failure signal; report complete, no transport "
         "errors)", "governed_calls_served": 360}]

    (HERE / "derived-metrics.json").write_text(
        json.dumps(metrics, indent=1) + "\n")
    with open(HERE / "narrative-coding.jsonl", "w") as fh:
        for row in coding_rows:
            fh.write(json.dumps(row) + "\n")
    (HERE / "inconclusive-audit.json").write_text(
        json.dumps({"total": len(inconclusives),
                    "entries": inconclusives}, indent=1) + "\n")

    fam = {}
    for row in coding_rows:
        fam[row["family"]] = fam.get(row["family"], 0) + 1
    print("coding totals:", fam)
    print("UNMATCHED-REVIEW rows must be 0 — reconcile before commit"
          if fam.get("UNMATCHED-REVIEW") else "coding: fully reconciled, fail-closed clean")
    print("criteria pass map:", {k: v["pass"] for k, v in metrics["frozen_criteria"].items()})
    print("floor violations:", len(floor_viol), "| spend: $%.2f" % total_cost)


if __name__ == "__main__":
    main()
