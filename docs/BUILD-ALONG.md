# Document Extraction Arena: the seven-step build

Published by Let’s Data Science. Contributed by Dev Suthar.

Use Python 3.13. Allow about 2–3 hours. All required exercises work without a provider key. Read the README for installation and keep starter and reference folders separate.

## 1. A high score can hide the wrong date.

An invoice contains numbers, names and dates. A model returns those fields as JSON. Your job is to decide whether that answer actually matches the document—and whether the benchmark is fair.

**Your goal:** Follow one saved response from image to field checks before writing code.

You will build three Python functions: safe amount conversion, one-to-one line-item matching, and an honest score summary. Streamlit provides the interface; Gemini is an optional source of new predictions. All mandatory exercises run locally with saved evidence and mocked API calls.

### What is measured?

The original run contains 120 synthetic invoices across four levels. Its headline compares the same 16 hard invoices: 11 fully correct for Flash-Lite and 15 for Flash 3.6. One layout and a small shared sample cannot establish accuracy on real invoices. Some degraded digits and numeric dates are ambiguous.

The answer key records what the generator intended. That is different from proving every character is readable. You will learn to report disagreements without hiding provider failures or overstating what the sample proves.

**Think first:** Seven fields match exactly. The invoice date does not. Is this invoice fully correct?

<details>
<summary>Check your reasoning</summary>

- **No. The exact-invoice check fails.** All eight field scores must equal one. An average can be high while a critical field is wrong.
- **Yes, because most fields match.** That would confuse mean field score with exact-invoice accuracy. A downstream payment workflow may depend on that one date.

</details>

### Your project files · version 1.0

- [Download the build-along starter](https://github.com/lets-data-science/document-extraction-arena/releases/download/v1.0.1/document-extraction-arena-starter-1.0.1.zip): Three functions to implement, focused tests, preserved evidence and recovery checkpoints. Extract into its own folder.
- [Download the completed reference](https://github.com/lets-data-science/document-extraction-arena/releases/download/v1.0.1/document-extraction-arena-reference-1.0.1.zip): The finished local workbench. Inspect this first, then build in a separate starter folder.
- [View Document Extraction Arena on GitHub](https://github.com/lets-data-science/document-extraction-arena): The public LDS repository, contributed by Dev Suthar. Browse the completed app or download versioned starter and reference packages from Releases.

**Checkpoint:** You can name the source image, predicted fields and answer key, and explain why a mismatch is not automatically an unfair or fair model failure.

### If you get stuck

- **Do I need a paid account?** No. The saved replay and all build tasks work without a key. A new model request is optional and uses your own account and quota.

Run the completed reference first; then prepare your starter.

## 2. Start with something you can inspect.

Run the reference, verify the original evidence, then create a separate starter workspace. Use Python 3.13 so the pinned dependencies install consistently.

**Your goal:** Open the local app and locate the three files you will change.

### Your project files · version 1.0

- [Download the build-along starter](https://github.com/lets-data-science/document-extraction-arena/releases/download/v1.0.1/document-extraction-arena-starter-1.0.1.zip): Three functions to implement, focused tests, preserved evidence and recovery checkpoints. Extract into its own folder.
- [Download the completed reference](https://github.com/lets-data-science/document-extraction-arena/releases/download/v1.0.1/document-extraction-arena-reference-1.0.1.zip): The finished local workbench. Inspect this first, then build in a separate starter folder.
- [View Document Extraction Arena on GitHub](https://github.com/lets-data-science/document-extraction-arena): The public LDS repository, contributed by Dev Suthar. Browse the completed app or download versioned starter and reference packages from Releases.

Extract the reference ZIP. Open a terminal in its document-extraction-arena folder, where app.py and requirements.txt live. These are local Python files; the LDS website is the guide, not an upload service.

### macOS / Linux: create the environment

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port 3086
```

Leave this terminal running and open http://localhost:3086. Stop with Ctrl+C. Choose another port if needed; always run from the same project folder.

### Windows PowerShell: create the environment

```bash
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 3086
```

No activation or execution-policy change is required. In later commands, replace python with .\.venv\Scripts\python.exe.

### Try it in the app: Inspect your first saved response

1. Open Review an invoice and leave Saved run selected.
2. Choose level4_hard_014 and Gemini 3.1 Flash-Lite.
3. Select Differences only and compare the two dates.
4. Switch the model and inspect the result.

### Check the reference in a second terminal

```bash
python scripts/verify_evidence.py
python -m pytest -q
```

Use the same environment. The hash check confirms the bundled source evidence is unchanged; tests use saved records and mocked requests.

Now extract the starter into a different folder and create its environment using the same commands. Open learner/normalize.py, learner/matching.py and learner/report.py in your editor. Their NotImplementedError markers are your tasks. Early test failures and the starter notice are expected; work through the next three steps in order.

**Checkpoint:** The reference shows a real saved response. You have a separate starter folder and know how to run its tests.

### If you get stuck

- **Installation fails on Python 3.11 or 3.12.** Install Python 3.13 and create a new .venv. Do not edit the dependency pins to work around the wrong interpreter.
- **Port 3086 is busy.** Stop your earlier Streamlit process or choose another port. A different port does not require a different code checkout.
- **The starter cannot score yet.** That is intentional. Implement the three learner functions, or restore one named checkpoint to continue.

Make amount normalization reject bad inputs without changing valid ones.

## 3. Do not turn “1e3” into thirteen.

The scorer compares values, not how they happen to be formatted. Removing every non-digit character can silently change the value you are checking.

**Your goal:** Implement to_decimal(value) in learner/normalize.py.

Use Decimal for comparisons. The contract accepts integers, floats, Decimal values and plain numeric strings, including scientific notation. It returns None for booleans, unsupported objects, currency symbols, separators, non-finite numbers, text longer than 80 characters, and magnitudes above 10^15. These bounds keep untrusted inputs manageable.

### Examples your function must preserve

```python
to_decimal('1e3') == Decimal('1000')
to_decimal(' 12.34 ') == Decimal('12.34')
to_decimal('NaN') is None
to_decimal(True) is None
to_decimal('$12.34') is None
```

These examples describe the function contract. Decimal and re are already imported in the starter.

Check type first: bool is a subclass of int in Python, but it is not an invoice amount. Strip surrounding whitespace, validate the whole numeric string, construct Decimal inside a try/except, then enforce the finite-value and magnitude checks. Do not replace commas or currency symbols and hope the result is correct.

### Run the amount checks

```bash
python -m pytest tests/test_learning.py -k normalize -q
```

The test also checks the strict tolerance boundary: 12.341 matches 12.34; 12.345 does not. A difference equal to 0.005 is rejected.

**Think first:** A model returns "1e3" for an amount of 1000. What should normalization produce?

<details>
<summary>Check your reasoning</summary>

- **Decimal(1000)** The exponent is part of the value, not decoration. Decimal preserves its meaning.
- **Decimal(13)** Removing non-digit characters corrupts scientific notation.
- **A match for any value starting with 1** Partial numeric matching would conceal extraction mistakes.

</details>

<details>
<summary>Reference: learner/normalize.py</summary>

```python
"""Step 3: compare amounts without silently changing their meaning."""
import re
from decimal import Decimal, InvalidOperation


def to_decimal(value):
    """Accept a finite number or an unformatted decimal string; otherwise None."""
    if isinstance(value, bool) or value is None:
        return None
    if not isinstance(value, (int, float, str, Decimal)):
        return None
    text = str(value).strip()
    if len(text) > 80 or not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?", text):
        return None
    try:
        number = Decimal(text)
        return number if number.is_finite() and abs(number) <= Decimal('1e15') else None
    except (InvalidOperation, ValueError):
        return None
```

Try your implementation before opening this reference. Explain each guard and each edge case.

</details>

### Continue from a checkpoint

```bash
python scripts/restore.py normalize
python -m pytest tests/test_learning.py -k normalize -q
```

Your previous file is backed up in .backups/. This restores only the named exercise. Other unfinished exercises can still fail.

**Checkpoint:** The normalize tests pass, and you can explain the bool and non-finite checks.

### If you get stuck

- **The function accepts NaN.** Decimal can represent NaN. Construction alone is not validation; check is_finite().
- **Why reject formatted money?** The model prompt asks for plain numeric values. Rejecting unexpected formatting is safer than guessing a locale-dependent separator.

Use these safe comparisons to match repeated line items exactly once.

## 4. A product name is not a unique row ID.

An invoice can contain two entries called “Consulting”. A dictionary keyed by description loses one of them. Your matcher must preserve both.

**Your goal:** Implement match_rows(expected, predicted) in learner/matching.py.

The provided row_matches helper checks normalized description, quantity, unit price and amount. Return index pairs: (expected index, predicted index). A row on either side can appear in at most one pair. Reordering is allowed. Both lists are bounded to 100 rows.

### A repeated-description example

```python
expected = [
    {'description':'Consulting','quantity':1,'unit_price':100,'amount':100},
    {'description':'Consulting','quantity':2,'unit_price':100,'amount':200},
]
predicted = list(reversed(expected))
# Expected result: [(0, 1), (1, 0)]
```

There are two different rows. Keep their indices instead of collapsing them into a dictionary.

Build the list of valid predicted candidates for each expected row. Track which expected row currently owns each prediction. When a candidate is occupied, try moving its owner to another candidate first. A visited set prevents cycling during that search. This is maximum bipartite matching: two sets of rows connected only where every field matches.

### Why not take the first free match?

Numeric tolerance can overlap. Expected amounts 100 and 100.008 can both match 100.004, but only the first can match 99.999. Taking 100.004 for the first row and stopping would miss a valid two-row pairing. Reassignment resolves it.

### Run the row checks

```bash
python -m pytest tests/test_learning.py -k matching -q
```

Checks cover repeats, order, double credit, empty lists, invented rows and overlapping tolerances. Complete normalize first.

<details>
<summary>Reference: learner/matching.py</summary>

```python
"""Step 4: a predicted row may satisfy only one expected row."""
import re
from decimal import Decimal
from learner.normalize import to_decimal


def equal_amount(a, b):
    left, right = to_decimal(a), to_decimal(b)
    return left is not None and right is not None and abs(left - right) < Decimal('0.005')


def row_matches(expected, predicted):
    if not isinstance(expected, dict) or not isinstance(predicted, dict):
        return False
    def text(value):
        return re.sub(r'\s+', ' ', value.strip()).casefold() if isinstance(value, str) else None
    label = text(expected.get('description'))
    return bool(label) and label == text(predicted.get('description')) and all(
        equal_amount(expected.get(key), predicted.get(key))
        for key in ('quantity', 'unit_price', 'amount')
    )


def match_rows(expected, predicted):
    """Return (expected index, predicted index) pairs using maximum matching.

    Augmenting paths avoid a greedy error when rounding tolerances overlap.
    Inputs are bounded to 100 rows by the invoice schema.
    """
    if not isinstance(expected, list) or not isinstance(predicted, list):
        raise ValueError('Line items must be lists.')
    if len(expected) > 100 or len(predicted) > 100:
        raise ValueError('Use at most 100 line items.')
    candidates = [[j for j, item in enumerate(predicted) if row_matches(row, item)] for row in expected]
    owners = {}
    def assign(i, seen):
        for j in candidates[i]:
            if j in seen:
                continue
            seen.add(j)
            if j not in owners or assign(owners[j], seen):
                owners[j] = i
                return True
        return False
    for i in range(len(expected)):
        assign(i, set())
    return sorted((i, j) for j, i in owners.items())
```

Try your implementation before opening this reference. Explain each guard and each edge case.

</details>

### Continue from a checkpoint

```bash
python scripts/restore.py matching
python -m pytest tests/test_learning.py -k matching -q
```

Your previous file is backed up in .backups/. This restores only the named exercise. Other unfinished exercises can still fail.

**Checkpoint:** Matching tests pass. One returned row cannot earn credit for two expected rows.

### If you get stuck

- **The score changes when rows are reordered.** Remove order-dependent assumptions and match on all four row fields.
- **An empty invoice crashes.** Two empty lists score one; only one empty list scores zero. The scorer already defines these cases—your matcher returns an empty list of pairs.

Turn the field results into an honest, validated report.

## 5. Make the score explain itself.

The evaluator produces seven scalar scores and one score for the complete line-item collection. A partial line-item match is a fraction, not a fully correct field.

**Your goal:** Implement summarize(scores) in learner/report.py.

Require a dictionary of eight finite numeric scores between zero and one. Reject bool values and empty or incomplete input. Return the number of scores equal to one as correct, eight as fields, all(v == 1) as exact, and the arithmetic mean as mean.

### Check a report by hand

```python
scores = dict(zip('abcdefgh', [1, 1, 1, 1, 1, 1, 1, 0.5]))
# correct: 7, fields: 8
# exact: False
# mean: 0.9375
```

The average is 93.75%. It does not mean the whole invoice is correct. The real scorer supplies the eight named invoice fields.

### Finish the build and run the full suite

```bash
python -m pytest tests/test_learning.py -k report -q
python -m pytest -q
python -m streamlit run app.py --server.port 3086
```

With all three tasks complete, the app can score the saved evidence. Restart an old Streamlit process if it still holds an earlier imported module.

### Try it in the app: Inspect the score and its raw evidence

1. Select Differences only.
2. Inspect the mismatched date.
3. Switch models and compare field checks.
4. Open Raw evidence & report to see the underlying response.

<details>
<summary>Reference: learner/report.py</summary>

```python
"""Step 5: keep exact invoices distinct from mean field scores."""
import math


def summarize(scores):
    """Summarize eight bounded field scores; an empty report is not a pass."""
    if not isinstance(scores, dict) or len(scores) != 8:
        raise ValueError('A report needs all eight field scores.')
    values = list(scores.values())
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in values):
        raise ValueError('Each field score must be a finite number between zero and one.')
    return {'correct': sum(v == 1 for v in values), 'fields': len(values),
            'exact': all(v == 1 for v in values), 'mean': sum(values) / len(values)}
```

Try your implementation before opening this reference. Explain each guard and each edge case.

</details>

### Continue from a checkpoint

```bash
python scripts/restore.py report
python -m pytest tests/test_learning.py -k report -q
```

Your previous file is backed up in .backups/. This restores only the named exercise. Other unfinished exercises can still fail.

**Checkpoint:** All tests pass. The saved Flash-Lite response for hard invoice 014 shows 7 of 8 fields; the saved Flash 3.6 response shows 8 of 8.

### If you get stuck

- **My report says an empty dictionary passed.** all([]) is True in Python. Validate the required field count before calling all.
- **The average looks right, but exact is wrong.** Only scores exactly equal to one count as fully correct. Do not round before the exact check.

Recompute the historical run and compare identical documents.

## 6. Compare the same work, and state the limits.

A small model tested on 120 invoices and a larger model tested on 16 do not form a fair aggregate comparison. Restrict the comparison to shared invoice IDs.

**Your goal:** Reproduce the saved paired result without contacting Google.

### Verify and rescore the original evidence

```bash
python scripts/verify_evidence.py
python runner/score.py --raw results/raw --out results/local/recomputed
python runner/compare.py --results results/local/recomputed --models gemini-3.1-flash-lite,gemini-3.6-flash --per-level 30
```

No API call. Output goes to a new directory. The explicit model list prevents a model with no successful answers from being silently dropped.

### Try it in the app: Read the paired comparison

1. Open Compare models.
2. Read the 11/16 and 15/16 exact counts.
3. Inspect the field mismatch chart.
4. Expand Dataset coverage and limits before drawing a conclusion.

On hard invoices 001–016, Flash-Lite has 11 exact matches and Flash 3.6 has 15. Mean field scores round to 96.0% and 99.9%. An API failure is kept in a separate error log; it is not called an extraction mistake. Invalid model JSON still counts as a failed extraction.

### Timing and cost are narrower than they look.

Original timings cover successful calls and exclude retry waits. Dollar figures are estimated paid-tier equivalents from recorded tokens and an October 8, 2026 price snapshot; the original run used free quota. Neither is a production latency or billing guarantee.

Inspect the date on hard invoice 014: the key is March 8, the prediction is August 3, and the original prompt did not specify the date convention. Some images also contain degraded digits. Report these as mismatches and review ambiguity before attributing blame. The updated local prompt specifies a generated-country policy, so future requests form a separate experiment.

**Think first:** Does 15/16 on one synthetic layout prove the larger model is best for real invoices?

<details>
<summary>Check your reasoning</summary>

- **No. It describes this sample and needs broader evaluation.** A small, synthetic, single-layout sample cannot establish general performance.
- **Yes. The higher exact count settles it.** It ignores sample size, layout diversity, ambiguity, latency and cost.

</details>

**Checkpoint:** You can reproduce both exact counts, identify the shared IDs and explain at least three limitations.

### If you get stuck

- **The comparison says no shared invoices.** Check the selected model names and results directory. An all-error model cannot support a paired extraction comparison.
- **The new runner wants to rerun historical records.** Do not point a revised prompt at the old output directory. Use a new experiment directory; preserve the original evidence.

Optionally make one bounded extraction, then design your next experiment.

## 7. Spend quota only after the checks are ready.

Your build is already complete without a new model call. This optional step connects it to a current provider response using your own key.

**Your goal:** Understand the request boundary and plan a more informative benchmark.

### Try it in the app: Prepare a single extraction

1. Open New extraction.
2. Choose a synthetic sample and preview it.
3. Inspect the model and password field.
4. Read the data-use and billing notice before Extract once.

Use Review an invoice → New extraction. Choose a synthetic sample or a PNG/JPEG up to 10 MB and 20 million pixels. The optional answer key must contain all eight invoice fields; invalid keys are rejected before any request. Without a key, extracted values are marked unscored. PDF input is not supported.

### Your document and your provider account

A new extraction sends the image to Google. Use synthetic documents and read the current data terms before sending anything confidential. A password field or local .env supplies the key; it is never written by this app or included in exports. Free quota is not guaranteed. One click makes at most one provider request, with retries disabled.

### Preview a one-document experiment

```bash
python runner/run_models.py --model gemini-3.1-flash-lite --levels level1_clean --per-level 1 --out results/local/experiment-01/raw --dry-run
```

This makes zero calls. Only remove --dry-run after setting your own key and deciding to spend quota. A stale request hash requires a new output directory.

If you choose to run the experiment, copy .env.example to .env and set GEMINI_API_KEY. Never commit the real file. Run the same command without --dry-run for one request. Model availability and charges depend on your Google project. The tests mock this boundary; they do not prove a live account has access.

For your extension, add a second independently designed layout with repeated descriptions. Ask someone to label legibility without seeing model answers, define the date policy first, and rerun both models on identical IDs. Save image and prompt hashes, returned model version, usage, attempt history and total elapsed time. Present coverage and failure counts alongside scores.

### Continue from authoritative references

- [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output): How a response schema constrains the shape of model output.
- [Gemini pricing and data terms](https://ai.google.dev/gemini-api/docs/pricing): Check your current model, tier and pricing before a request.
- [LDS project source and releases](https://github.com/lets-data-science/document-extraction-arena): The LDS edition, contributed by Dev Suthar. Apache 2.0, source attribution and the original measured evidence are included.

**Checkpoint:** You have a working evaluator, passing tests, reproducible saved results and a bounded plan for new data. A live call is optional, not a completion requirement.

### If you get stuck

- **Google reports quota or high demand.** Stop and check account limits. No quota retry is automatic; wait before deliberately trying again.
- **The model returns invalid JSON.** Do not award a score. Inspect the input and schema, and preserve the failed response as evidence.
- **Can I host this publicly now?** This is a local teaching app. A public upload service needs its own authentication, rate limits, retention controls and cost protections.

Make the project your own: evaluate another document type with explicit fields and an independently reviewed answer key.
