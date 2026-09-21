#!/usr/bin/env python3
"""Phase-12 execution wiring for the Phase-11 preregistered v2 trial.

Runs EXACTLY what eval/evidence/v2-trial-prereg-2026-09-21/
PREREGISTRATION.md froze — nothing else. This script adds no policy:
every pin (identities, prompt hashes, model/profile, fixture set,
ceiling) is PARSED FROM THE PREREG DOCUMENT and enforced against
reality BEFORE request 1. Any mismatch refuses (fail closed).

Modes:
  --check            full offline pre-flight; zero network; exit 0
                     READY / exit 2 BLOCKED (default mode)
  --authorize-spend  the explicit human act: requires
                     PM_QUALIFY_LIVE_AUTHORIZED=1 AND --out AND
                     recorded prices; executes the 10 N=1 low-effort
                     reviews with the evidence gate ON under the
                     preregistered $0.02 hard ceiling

This script NEVER computes a verdict. After execution it freezes
records + spend + a mechanical-count extract (survivors/downgrades)
and stops: adjudication is the human maintainer's, per the frozen
protocol.
"""
import hashlib
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import eval.profile_qualification as pq  # noqa: E402
import eval.run_corpus as rc  # noqa: E402
import transport  # noqa: E402

PREREG = ROOT / "eval" / "evidence" / "v2-trial-prereg-2026-09-21" \
    / "PREREGISTRATION.md"
EXTENSION = ROOT / "eval" / "v2_trial_prompt_extension.txt"
TRIAL_SCHEMA = ROOT / "eval" / "v2_trial_review_result_schema.json"
HEX = r"[0-9a-f]{16,64}"


def _sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def prereg_pins(doc):
    """Parse the frozen values out of the prereg document itself —
    the document is the single source of truth, not this script."""
    pins = {}
    for ln in doc.splitlines():
        if not ln.startswith("|"):
            continue
        m = re.search(r"`(%s)`" % HEX, ln)
        if not m:
            continue
        label = re.match(r"\|\s*`?([^`|]+?)`?\s*\|", ln)
        if not label:
            continue
        name = label.group(1).strip()
        name = name.split(" (")[0]
        if name.startswith("eval/"):
            name = name[5:]
        if name not in pins:
            pins[name] = m.group(1)
    body = doc[doc.index("Model/request profile frozen"):]
    model = re.search(r"model\s+`([^`]+)`", body).group(1)
    effort = re.search(r"reasoning effort `([^`]+)`", body).group(1)
    max_tokens = int(re.search(r"`max_tokens=(\d+)`", body).group(1))
    ceiling = float(re.search(r"\*\*Hard ceiling \$([\d.]+)\*\*",
                              doc).group(1))
    pairs = re.findall(r"\|\s*(\d+)\s*\|\s*(C\d+)\s*\|\s*(M\d+)\s*\|",
                       doc)
    fixtures = sorted({c for _, c, _ in pairs}
                      | {p for _, _, p in pairs})
    return {
        "pins": pins, "model": model, "effort": effort,
        "max_tokens": max_tokens, "ceiling_usd": ceiling,
        "fixtures": fixtures,
    }


def compute_reality(prereg, pins):
    """Everything the trial will send or depend on, computed live."""
    ext_text = EXTENSION.read_text()
    trial_schema = json.loads(TRIAL_SCHEMA.read_text())
    engine = pq.load_subject_engine()
    profile = transport.load_profile(prereg["model"])
    prompts = {}
    chars = {}
    system_hash = None
    for fid in prereg["fixtures"]:
        fx = json.loads(
            (ROOT / "eval" / "fixtures" / f"{fid}.json").read_text())
        system, user = engine._build_prompts(
            rc._review_input(fx, prereg["model"]))
        final_user = user + "\n\n" + ext_text
        sh = hashlib.sha256(system.encode()).hexdigest()
        if system_hash is None:
            system_hash = sh
        assert sh == system_hash
        prompts[fid] = hashlib.sha256(final_user.encode()).hexdigest()
        # worst-case pre-request bound INCLUDES the suffix chars
        chars[fid] = len(system) + len(final_user)
    return {
        "oracle_version": rc.oracle_version(),
        "states.json": _sha(ROOT / "eval" / "states.json"),
        "engine.py": _sha(ROOT / "engine.py"),
        "parse_review.py": _sha(ROOT / "parse_review.py"),
        "rubric.md": _sha(ROOT / "rubric.md"),
        "transport.py": _sha(ROOT / "transport.py"),
        "model_profiles.json": _sha(ROOT / "model_profiles.json"),
        "review_result_schema.json":
            _sha(ROOT / "review_result_schema.json"),
        "honesty audit protocol": _sha(
            ROOT / "eval" / "evidence" / "honesty-audit-protocol-2026-09-21"
            / "PROTOCOL.md"),
        "prompt extension": _sha(EXTENSION),
        "trial v2 response schema": _sha(TRIAL_SCHEMA),
        "system": system_hash,
        "prompts": prompts,
        "profile_max_tokens": profile["max_tokens"],
        "profile_effort": profile["reasoning_effort"],
        "profile_structured": profile["structured_output"],
        "trial_schema_object": trial_schema,
        "extension_text": ext_text,
        "prompt_chars": chars,
    }


def preflight(prereg, reality):
    """Returns the list of violations; empty means READY."""
    bad = []
    pins = prereg["pins"]
    direct = ("oracle_version", "states.json", "engine.py",
              "parse_review.py", "rubric.md", "transport.py",
              "model_profiles.json", "review_result_schema.json",
              "honesty audit protocol", "prompt extension",
              "trial v2 response schema")
    for name in direct:
        want = pins.get(name)
        got = reality[name]
        if want is None:
            bad.append("prereg does not pin %r" % name)
        elif want != got:
            bad.append("%s: prereg %s != reality %s" % (name, want, got))
    if pins.get("(all)") != reality["system"]:
        bad.append("system prompt: prereg %s != reality %s"
                   % (pins.get("(all)"), reality["system"]))
    for fid, want in pins.items():
        if re.fullmatch(r"[CM]\d+", fid):
            got = reality["prompts"].get(fid)
            if got is None:
                bad.append("prereg pins fixture %s but it is not in "
                           "the trial set" % fid)
            elif got != want:
                bad.append("prompt %s: prereg %s != reality %s"
                           % (fid, want, got))
    for fid, got in reality["prompts"].items():
        if fid not in pins:
            bad.append("trial fixture %s has no preregistered prompt "
                       "hash" % fid)
    if prereg["effort"] != reality["profile_effort"]:
        bad.append("effort: prereg %r != profile %r"
                   % (prereg["effort"], reality["profile_effort"]))
    if prereg["max_tokens"] != reality["profile_max_tokens"]:
        bad.append("max_tokens: prereg %r != profile %r"
                   % (prereg["max_tokens"], reality["profile_max_tokens"]))
    if not reality["profile_structured"]:
        bad.append("profile structured_output is not enabled")
    corpus_ids = sorted(f["id"] for f in rc.load_corpus(
        ROOT / "eval" / "fixtures") if f["id"] in prereg["fixtures"])
    if corpus_ids != prereg["fixtures"]:
        bad.append("prereg fixture set %s not fully present in corpus"
                   % prereg["fixtures"])
    return bad


def mechanical_counts(out_dir):
    """Counts only — explicitly NOT verdicts."""
    records_path = out_dir / "records.jsonl"
    extract = []
    for line in records_path.read_text().splitlines():
        r = json.loads(line)
        result = r.get("result") or {}
        audit = (r.get("evidence_gate") or {}).get("audit") or []
        survivors = sum(1 for f in result.get("findings") or []
                        if f.get("severity") == "blocking")
        downgrades = sum(1 for a in audit
                         if a.get("permitted") is False)
        extract.append({
            "fixture": r["fixture"], "run_index": r["run_index"],
            "assessment": result.get("assessment"),
            "blocking_survivors": survivors,
            "gate_downgrades": downgrades,
        })
    return extract


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="offline pre-flight only (default)")
    mode.add_argument("--authorize-spend", action="store_true",
                      help="execute the trial; requires "
                           "PM_QUALIFY_LIVE_AUTHORIZED=1, --out, and "
                           "recorded prices")
    ap.add_argument("--out", default=None,
                    help="evidence directory for the run")
    ap.add_argument("--price-input-per-m", type=float, default=None)
    ap.add_argument("--price-output-per-m", type=float, default=None)
    ap.add_argument("--price-source", default=None)
    args = ap.parse_args(argv)

    doc = PREREG.read_text()
    prereg = prereg_pins(doc)
    reality = compute_reality(prereg, prereg["pins"])
    bad = preflight(prereg, reality)

    if bad:
        print("BLOCKED — preregistration mismatches (fail closed, "
              "nothing was sent):")
        for b in bad:
            print("  -", b)
        return 2
    print("READY: all preregistered identities, prompt hashes, and "
          "profile pins verified against reality "
          "(model=%s, effort=%s, max_tokens=%d, fixtures=%s, "
          "ceiling=$%.2f)"
          % (prereg["model"], prereg["effort"], prereg["max_tokens"],
             ",".join(prereg["fixtures"]), prereg["ceiling_usd"]))

    if not args.authorize_spend:
        return 0

    if os.environ.get("PM_QUALIFY_LIVE_AUTHORIZED") != "1":
        print("spend refused: --authorize-spend additionally requires "
              "PM_QUALIFY_LIVE_AUTHORIZED=1")
        return 2
    if not args.out:
        print("spend refused: --out is required for execution")
        return 2
    if (args.price_input_per_m is None or args.price_output_per_m is None
            or not args.price_source):
        print("spend refused: ceiling enforcement requires recorded "
              "prices (--price-input-per-m, --price-output-per-m, "
              "--price-source)")
        return 2

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    profile, overrides = pq.measurement_profile(
        prereg["model"], prereg["effort"], prereg["max_tokens"])
    spend = pq.SpendGuard(prereg["ceiling_usd"], args.price_input_per_m,
                          args.price_output_per_m,
                          reality["prompt_chars"])
    spend.price_source = args.price_source
    from eval.spend_ledger import SpendLedger
    ledger = SpendLedger(out_dir / "spend-ledger.json", spend)

    pq.live(out_dir,
            [f for f in pq.corpus() if f["id"] in prereg["fixtures"]],
            1, prereg["model"], profile, overrides,
            run_index=None, spend=spend, ledger=ledger,
            evidence_gate=True, prompt_suffix=reality["extension_text"],
            response_schema=reality["trial_schema_object"])

    records_path = out_dir / "records.jsonl"
    spend_meta = pq._spend_from_records(
        pq._load_records(records_path), spend)
    actual = spend_meta["actual_cost_usd"]
    state = {
        "trial": "v2-evidence-declaration-calibration-N1",
        "preregistration_sha256": _sha(PREREG),
        "status": "EXECUTED_PENDING_ADJUDICATION",
        "ceiling_usd": prereg["ceiling_usd"],
        "actual_cost_usd": actual,
        "price_source": args.price_source,
        "records_sha256": _sha(records_path),
        "mechanical_counts": mechanical_counts(out_dir),
        "note": "counts only — verdicts require the frozen honesty "
                "protocol's human adjudication; this script computes "
                "no GO/NO-GO",
    }
    with (out_dir / "trial-state.json").open("w") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("EXECUTED_PENDING_ADJUDICATION: actual $%.6f of $%.2f "
          "ceiling; adjudication is the human maintainer's"
          % (actual, prereg["ceiling_usd"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
