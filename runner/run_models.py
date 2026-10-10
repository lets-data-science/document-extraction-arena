import argparse
import json
import time
from pathlib import Path
import os
import re
import hashlib
from datetime import datetime, timezone

from dotenv import load_dotenv
from google import genai
from google.genai import types

_client = None


def make_client(api_key=None):
    """A client with the runner's 90 s timeout. No key given: the library reads GEMINI_API_KEY."""
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=90_000, retry_options=types.HttpRetryOptions(attempts=1)))


def get_client():
    """Created on first use, so importing this module (tests, --dry-run) needs no API key."""
    global _client
    if _client is None:
        load_dotenv()
        _client = make_client()
    return _client

PROMPT = (
    "You are reading an invoice image. Return ONLY a JSON object with these keys: "
    "invoice_number (string), "
    "vendor (the company name that issued the invoice: name only, no address), "
    "invoice_date (YYYY-MM-DD), "
    "currency (ISO 4217 code such as INR, USD, EUR), "
    "line_items (list of objects with description, quantity, unit_price, amount), "
    "subtotal, tax, total. "
    "All money values must be plain numbers: no currency symbols, no thousands separators."
)

# New runs are a separate experiment. Historical results keep their original prompt.
PROMPT += (" Resolve numeric dates using an explicit vendor country if it is legible: "
           "US means month/day/year; other generated vendor countries mean day/month/year. "
           "If the image does not resolve a field unambiguously, return null. Never guess.")
SCHEMA = {"type": "object", "properties": {
    **{name: {"type": ["string", "null"]} for name in ("invoice_number", "vendor", "invoice_date", "currency")},
    **{name: {"type": ["number", "null"]} for name in ("subtotal", "tax", "total")},
    "line_items": {"type": ["array", "null"], "items": {"type": "object", "properties": {
        "description": {"type": "string"}, **{name: {"type": "number"} for name in ("quantity", "unit_price", "amount")}},
        "required": ["description", "quantity", "unit_price", "amount"]}},
}, "required": ["invoice_number", "vendor", "invoice_date", "currency", "subtotal", "tax", "total", "line_items"]}
PROMPT_SHA256 = hashlib.sha256(PROMPT.encode()).hexdigest()


def fingerprint(model, image):
    return hashlib.sha256(json.dumps({"model": model, "image": hashlib.sha256(image.read_bytes()).hexdigest(),
        "prompt": PROMPT_SHA256, "schema": SCHEMA, "temperature": 0}, sort_keys=True).encode()).hexdigest()


def safe_error(exc):
    # Never persist arbitrary exception strings: a provider may echo credentials.
    code = getattr(exc, "code", None)
    match = re.search(r"\b(400|401|403|404|408|429|500|502|503|504)\b", str(code or exc))
    return f"HTTP_{match.group(1)}" if match else "REQUEST_FAILED"


MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def extract(model, image_path, no_retry=False, client=None):
    data = image_path.read_bytes()
    config = types.GenerateContentConfig(response_mime_type="application/json", response_json_schema=SCHEMA, temperature=0)
    attempts = []
    max_attempts = 1 if no_retry else 2
    started = time.monotonic()
    for attempt in range(max_attempts):
        try:
            start = time.monotonic()
            resp = (client or get_client()).models.generate_content(
                model=model, contents=[types.Part.from_bytes(data=data, mime_type=MIME[image_path.suffix.lower()]), PROMPT], config=config)
            duration = round(time.monotonic() - start, 3)
            attempts.append({"seconds": duration, "outcome": "answered"})
            usage = resp.usage_metadata
            return {"response_text": resp.text, "seconds": duration,
                "input_tokens": getattr(usage, "prompt_token_count", 0) or 0,
                "output_tokens": getattr(usage, "candidates_token_count", 0) or 0,
                "thinking_tokens": getattr(usage, "thoughts_token_count", 0) or 0,
                "error": None, "attempts": attempts, "elapsed_seconds": round(time.monotonic()-started, 3),
                "recorded_at": datetime.now(timezone.utc).isoformat(), "prompt_sha256": PROMPT_SHA256,
                "request_sha256": fingerprint(model, image_path),
                "returned_model": getattr(resp, "model_version", None)}
        except Exception as exc:
            err = safe_error(exc)
            attempts.append({"seconds": round(time.monotonic()-start, 3), "outcome": err})
            # Daily quota, authentication and schema errors must never be retried.
            if err not in ("HTTP_500", "HTTP_502", "HTTP_503", "HTTP_504") or attempt+1 >= max_attempts:
                break
            time.sleep(2)
    return {"response_text": None, "seconds": None, "input_tokens": 0, "output_tokens": 0,
            "thinking_tokens": 0, "error": err, "attempts": attempts,
            "elapsed_seconds": round(time.monotonic()-started, 3),
            "recorded_at": datetime.now(timezone.utc).isoformat(), "prompt_sha256": PROMPT_SHA256,
            "request_sha256": fingerprint(model, image_path)}


def level_names(data_dir):
    return sorted(p.name for p in Path(data_dir).iterdir() if p.is_dir())


def select_invoices(data_dir, levels, per_level):
    """Answer-key paths to run: the given levels in the given order (None = all, sorted)."""
    valid = level_names(data_dir)
    levels = valid if levels is None else levels
    unknown = [lv for lv in levels if lv not in valid]
    if unknown:
        raise ValueError(f"unknown level(s) {', '.join(unknown)}; valid levels: {', '.join(valid)}")
    truths = []
    for level in dict.fromkeys(levels):  # drop repeats, keep order
        truths += sorted((Path(data_dir) / level).glob("*.json"))[:per_level]
    return truths


def status(out_path, request_hash=None):
    """'run' (no result yet), 'retry' (saved API error) or 'skip' (finished)."""
    if not out_path.exists():
        return "run"
    existing = json.loads(out_path.read_text())
    if request_hash and existing.get("request_sha256") != request_hash:
        return "stale"
    return "skip" if existing.get("error") is None else "retry"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--per-level", type=int, default=30)
    ap.add_argument("--levels", help="comma-separated level folders, run in this order (default: all)")
    ap.add_argument("--data", default="data/synthetic")
    ap.add_argument("--out", default="results/local/raw")
    ap.add_argument("--max-consecutive-errors", type=int, default=3)
    ap.add_argument("--no-retry", action="store_true",
                    help="save a failed API call as an error record at once: one request, no retries, no backoff")
    ap.add_argument("--retry-transient", action="store_true", help="Opt in to one extra attempt for transient server errors only")
    ap.add_argument("--min-interval", type=float, default=0,
                    help="minimum seconds between the starts of two requests (0 = no pacing)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print which invoices would run, retry or be skipped; no API calls, no files written")
    args = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", args.model):
        ap.error("Use a valid model identifier.")
    if not 1 <= args.per_level <= 120:
        ap.error("--per-level must be between 1 and 120.")

    levels = [x.strip() for x in args.levels.split(",") if x.strip()] if args.levels else None
    try:
        truths = select_invoices(args.data, levels, args.per_level)
    except ValueError as e:
        ap.error(str(e))

    out_dir = Path(args.out) / args.model.replace("/", "_")

    if args.dry_run:
        counts = {"run": 0, "retry": 0, "skip": 0, "stale": 0}
        for i, truth_path in enumerate(truths, 1):
            image = next((p for p in truth_path.parent.glob(truth_path.stem + ".*") if p.suffix in MIME), None)
            st = status(out_dir / f"{truth_path.stem}.json", fingerprint(args.model,image) if image else None)
            counts[st] += 1
            label = {"run": "WOULD RUN", "retry": "WOULD RETRY (saved error)", "skip": "SKIP (already ok)", "stale": "STALE (use a new output directory)"}[st]
            print(f"[{i}/{len(truths)}] {truth_path.stem}  {label}")
        print(f"dry run: {counts['run']} to run, {counts['retry']} to retry, {counts['skip']} skipped, {counts['stale']} stale; no API calls made")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    consecutive_errors = 0
    last_start = None
    for i, truth_path in enumerate(truths, 1):
        inv_id = truth_path.stem
        out_path = out_dir / f"{inv_id}.json"
        image = next(p for p in truth_path.parent.glob(inv_id + ".*") if p.suffix in MIME)
        current = status(out_path, fingerprint(args.model, image))
        if current == "stale":
            raise SystemExit("Saved input or prompt differs. Choose a new --out directory; original evidence is preserved.")
        if current == "skip":  # already done: lets you resume after an interruption
            continue                    # (a saved API failure falls through and is retried)
        image = next(p for p in truth_path.parent.glob(inv_id + ".*") if p.suffix in MIME)
        if last_start is not None and args.min_interval > 0:
            wait = args.min_interval - (time.monotonic() - last_start)
            if wait > 0:
                time.sleep(wait)
        last_start = time.monotonic()
        result = extract(args.model, image, no_retry=args.no_retry or not args.retry_transient)
        result.update({"id": inv_id, "level": truth_path.parent.name, "model": args.model, "request_sha256": fingerprint(args.model, image)})
        temporary = out_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, indent=2, allow_nan=False))
        temporary.replace(out_path)
        tokens = result["input_tokens"] + result["output_tokens"] + result["thinking_tokens"]
        print(f"[{i}/{len(truths)}] {inv_id}  {result['seconds']}s  {tokens} tokens  "
              f"{result['error'] or 'ok'}", flush=True)
        consecutive_errors = consecutive_errors + 1 if result["error"] else 0
        if consecutive_errors >= args.max_consecutive_errors:
            raise SystemExit(f"Stopping: {consecutive_errors} API failures in a row. "
                             f"Last error: {result['error']}")
        time.sleep(1)  # gentle pause so we stay under rate limits


if __name__ == "__main__":
    main()
