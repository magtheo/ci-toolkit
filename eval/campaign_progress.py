"""Phase-08: one human-readable campaign progress line from a
per-effort summary.json + the shared ledger JSON — the corrected
replacement for the ad-hoc inline printers in campaign launch scripts
(the frozen B1 execute.sh read fields that do not exist
(`provider_generations`, ledger `settled_usd`) and silently printed
None; this helper reads only real fields and labels derived numbers).
Offline and side-effect free."""
import json
import pathlib


def progress_line(summary_path, ledger_path, ceiling_usd=1.0):
    s = json.loads(pathlib.Path(summary_path).read_text())
    led = json.loads(pathlib.Path(ledger_path).read_text())
    sp = s.get("spend", {})
    al = sp.get("aggregate_ledger", {})
    return (
        "reviews=%s gens=%s escalations=%s inconclusive=%s | "
        "records-derived cost=$%s | ledger: settled_tokens=%s in/%s "
        "out outstanding=%s swept=%s halts=%s invariant=%s"
        % (s.get("logical_reviews"),
           sp.get("provider_generations_billed"),
           s.get("escalations"), s.get("final_inconclusive"),
           sp.get("actual_cost_usd"),
           al.get("settled_in_tokens"), al.get("settled_out_tokens"),
           al.get("outstanding_reservations"), al.get("orphan_sweeps"),
           al.get("halts"), al.get("invariant_holds")))
