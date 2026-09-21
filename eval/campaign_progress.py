"""Phase-08: one human-readable campaign progress line from a
per-effort summary.json + the shared RAW ledger JSON — the corrected
replacement for the ad-hoc inline printers in campaign launch scripts.
The summary supplies records-derived effort spend/prices; the ledger
file supplies current aggregate token/reservation state. Offline and
side-effect free."""
import json
import pathlib


def _show(value):
    return "n/a" if value is None else value


def progress_line(summary_path, ledger_path, ceiling_usd=1.0):
    s = json.loads(pathlib.Path(summary_path).read_text())
    led = json.loads(pathlib.Path(ledger_path).read_text())
    sp = s.get("spend", {})

    settled_in = led.get("settled_in_tokens")
    settled_out = led.get("settled_out_tokens")
    reservations = led.get("reservations") or []
    outstanding_usd = sum((r.get("usd") or 0) for r in reservations)
    p_in, p_out = sp.get("price_input_per_1m"), sp.get("price_output_per_1m")
    aggregate = sp.get("aggregate_ledger") or {}
    ceiling = aggregate.get("ceiling_usd", ceiling_usd)

    invariant = "n/a"
    settled_usd = None
    if all(isinstance(v, (int, float))
           for v in (settled_in, settled_out, p_in, p_out, ceiling)):
        settled_usd = (settled_in * p_in + settled_out * p_out) / 1e6
        invariant = settled_usd + outstanding_usd <= ceiling + 1e-9

    return (
        "reviews=%s gens=%s escalations=%s inconclusive=%s | "
        "records-derived cost=$%s | ledger: settled_tokens=%s in/%s "
        "out settled=$%s outstanding=%s swept=%s halts=%s invariant=%s"
        % (_show(s.get("logical_reviews")),
           _show(sp.get("provider_generations_billed")),
           _show(s.get("escalations")), _show(s.get("final_inconclusive")),
           _show(sp.get("actual_cost_usd")),
           _show(settled_in), _show(settled_out),
           _show(round(settled_usd, 6) if settled_usd is not None else None),
           len(reservations), len(led.get("swept_orphans") or []),
           _show(led.get("halts", 0)), invariant))
