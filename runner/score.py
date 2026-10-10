import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from learner.normalize import to_decimal
from learner.matching import match_rows
from runner.validation import load_json, validate_invoice

import pandas as pd

# USD per million tokens (input, output).
# Verify against https://ai.google.dev/gemini-api/docs/pricing before publishing.
PRICES = {
    "gemini-3.1-flash-lite": (0.25, 1.50),
    # 3.x Flash prices are valid through December 31, 2026 (then $1.50 / $7.50).
    # Source: https://ai.google.dev/gemini-api/docs/pricing
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.7-flash": (0.75, 3.75),
    "gemini-3.6-flash": (0.75, 3.75),
}

SCALAR_FIELDS = ["invoice_number", "vendor", "invoice_date", "currency", "subtotal", "tax", "total"]
MONEY_FIELDS = {"subtotal", "tax", "total"}


def norm_text(x):
    return re.sub(r"\s+", " ", str(x)).strip().lower()


def money_equal(a, b):
    da, db = to_decimal(a), to_decimal(b)
    return da is not None and db is not None and abs(da - db) < Decimal("0.005")


def parse_response(text):
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        obj = load_json(text)
        validate_invoice(obj, partial=True)
    except (ValueError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None


def score_line_items(truth_items, pred_items):
    if not isinstance(pred_items, list):
        return 0.0, "line_items missing or not a list"
    pairs = match_rows(truth_items, pred_items)
    denom = max(len(truth_items), len(pred_items))
    value = len(pairs) / denom if denom else 1.0
    return value, f"{len(pairs)}/{len(truth_items)} lines matched, model returned {len(pred_items)}"



def score_invoice(truth, pred):
    """Returns ({field: 0.0..1.0}, {field: explanation of what went wrong})."""
    validate_invoice(truth)
    if pred is not None and not isinstance(pred, dict):
        pred = None
    scores, notes = {}, {}
    for f in SCALAR_FIELDS:
        got = None if pred is None else pred.get(f)
        if f in MONEY_FIELDS:
            ok = money_equal(got, truth[f])
        elif f == "currency":
            ok = got is not None and str(got).strip().upper() == truth[f]
        elif f == "invoice_date":
            ok = got is not None and str(got).strip() == truth[f]
        else:
            ok = got is not None and norm_text(got) == norm_text(truth[f])
        scores[f] = 1.0 if ok else 0.0
        if not ok:
            notes[f] = f"expected {truth[f]!r}, got {got!r}"
    if pred is None:
        scores["line_items"] = 0.0
        notes["line_items"] = "no parseable JSON"
    else:
        scores["line_items"], detail = score_line_items(truth["line_items"], pred.get("line_items"))
        if scores["line_items"] < 1:
            notes["line_items"] = detail
    return scores, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/synthetic", help="folder with <level>/<id>.json answer keys")
    ap.add_argument("--raw", default="results/raw", help="folder with <model>/<id>.json runner output")
    ap.add_argument("--out", default="results", help="where the three CSVs are written")
    args = ap.parse_args()
    data_dir, out_dir = Path(args.data), Path(args.out)

    rows, failures, api_errors = [], [], []
    for model_dir in sorted(Path(args.raw).iterdir()):
        if not model_dir.is_dir():
            continue
        model = model_dir.name
        price = PRICES.get(model)
        for path in sorted(model_dir.glob("*.json")):
            res = json.loads(path.read_text())
            truth = json.loads((data_dir / res["level"] / f"{res['id']}.json").read_text())
            pred = parse_response(res["response_text"])
            scores, notes = score_invoice(truth, pred)
            billed_out = res["output_tokens"] + res["thinking_tokens"]  # thinking tokens are billed as output
            cost = (res["input_tokens"] * price[0] + billed_out * price[1]) / 1e6 if price else None
            rows.append({
                "model": model, "level": res["level"], "id": res["id"],
                "accuracy": sum(scores.values()) / len(scores),
                "exact": all(v == 1.0 for v in scores.values()),
                "seconds": res["seconds"], "cost_usd": cost,
                "api_error": res["error"] is not None,
                "parse_error": pred is None and res["error"] is None,
                **{f"f_{k}": v for k, v in scores.items()},
            })
            if res["error"] is not None:  # no answer was produced, so there is no extraction mistake to list
                api_errors.append({"model": model, "level": res["level"], "id": res["id"],
                                   "error": res["error"]})
                continue
            for field, note in notes.items():
                failures.append({"model": model, "level": res["level"], "id": res["id"],
                                 "field": field, "detail": note})

    if not rows:
        raise SystemExit("No raw responses found. Check --raw; no result files were written.")
    df = pd.DataFrame(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "per_invoice.csv", index=False)
    pd.DataFrame(failures, columns=["model", "level", "id", "field", "detail"]).to_csv(
        out_dir / "failures.csv", index=False)
    pd.DataFrame(api_errors, columns=["model", "level", "id", "error"]).to_csv(
        out_dir / "api_errors.csv", index=False)

    ok = df[~df.api_error]  # API failures are infrastructure problems, not model mistakes
    summary = ok.groupby(["model", "level"]).agg(
        n=("id", "count"),
        accuracy_pct=("accuracy", lambda s: round(s.mean() * 100, 1)),
        exact_invoice_pct=("exact", lambda s: round(s.mean() * 100, 1)),
        avg_seconds=("seconds", lambda s: round(s.mean(), 1)),
        cost_per_invoice_usd=("cost_usd", lambda s: round(s.mean(), 5)),
        total_cost_usd=("cost_usd", lambda s: round(s.sum(min_count=1), 4)),
        parse_errors=("parse_error", "sum"),
    ).reset_index()
    summary.to_csv(out_dir / "summary.csv", index=False)
    print(summary.to_string(index=False))

    fields = [c for c in df.columns if c.startswith("f_")]
    print("\nPer-field accuracy (%):")
    print((ok.groupby("model")[fields].mean() * 100).round(1).T.to_string())
    print(f"\nAPI errors (excluded above, listed in {out_dir / 'api_errors.csv'}): {int(df.api_error.sum())}")
    for model, n in df[df.api_error].groupby("model").size().items():
        print(f"  {model}: {n}")


if __name__ == "__main__":
    main()