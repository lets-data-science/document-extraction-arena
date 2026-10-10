# Document Extraction Arena · LDS edition 1.0

Build an invoice evaluator whose scores you can explain. Start with **saved, measured model responses**: no key, cloud account or new API request is needed. Then implement three small pieces of the evaluator and, optionally, try one new extraction.

Published by **[Let's Data Science](https://github.com/lets-data-science)**. Contributed by **[Dev Suthar](https://github.com/devsutharsystems)** and extended for the LDS build-along. The original benchmark evidence is preserved from upstream commit `65cf9ca5a1fbd68d097ff9536c3e2a99f110ac96`. See `NOTICE`, `UPSTREAM.json` and `docs/METHODOLOGY.md`.

## Get the project

- [Version 1.0.1 downloads](https://github.com/lets-data-science/document-extraction-arena/releases/tag/v1.0.1): choose the **starter** to implement the exercises or the **reference** to inspect the finished app. The release includes SHA-256 checksums.
- This repository contains the **completed reference**. Clone it with the commands below, then follow the setup instructions. Keep your starter in a separate folder.
- [Seven-step build-along](docs/BUILD-ALONG.md): implementation tasks, reference answers, checks and troubleshooting in one guide.

```sh
git clone https://github.com/lets-data-science/document-extraction-arena.git
cd document-extraction-arena
```

## 1. Run the completed app first

Install **Python 3.13** from [python.org](https://www.python.org/downloads/). These pinned dependencies were checked with Python 3.13. Older Python versions may not install them.

Clone this repository, or download and extract the **reference** archive into its own directory. Open a terminal inside its `document-extraction-arena` folder (the folder containing `app.py`).

macOS / Linux:

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port 3086
```

Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 3086
```

Open **http://localhost:3086**. If that port is busy, change `3086` in the command. The same folder serves the same app on any port. Stop with Ctrl+C. On Windows, use `.\.venv\Scripts\python.exe` wherever this guide says `python`; activation is not required.

The first view shows invoice `level4_hard_014` and Flash-Lite's saved answer. Seven of eight fields match. Select **Differences only**: the date is August 3 in the prediction but March 8 in the key. This is also a lesson in benchmark ambiguity: the original prompt did not explain the generated locale's date policy. A mismatch does not, by itself, prove an unreasonable model answer.

Choose Gemini 3.6 Flash to inspect its saved response. **Compare models** uses the same 16 hard invoices for both models. **How it works** explains the scoring rules.

## 2. Build the three learner functions

Extract the **starter** in a separate directory, keeping the completed reference available for comparison. Repeat the environment setup inside the starter. Its three learner functions deliberately raise `NotImplementedError`. Test failures are expected until you implement them. The UI explains this rather than claiming a passing score.

1. `learner/normalize.py`: turn a plain finite decimal into `Decimal`; reject booleans, invalid text, non-finite values and unsupported input types. Preserve scientific notation. Do not strip random punctuation from money.
2. `learner/matching.py`: match expected and predicted rows one to one. A repeated product name is not a unique ID. Use the provided `row_matches` helper. If two rows compete for the same candidate, try reassigning its current owner to another candidate (an augmenting path).
3. `learner/report.py`: validate eight finite scores in [0, 1], then return `correct`, `fields`, `exact` and `mean`. Seven perfect fields and one half-credit field means 7/8 fully correct fields, mean 0.9375, **not** an exact invoice.

Run the focused checks in order:

```sh
python -m pytest tests/test_learning.py -k normalize -q
python -m pytest tests/test_learning.py -k matching -q
python -m pytest tests/test_learning.py -k report -q
python -m pytest -q
```

If stuck, restore just one completed function. The script preserves your old file in `.backups/`:

```sh
python scripts/restore.py normalize
python scripts/restore.py matching
python scripts/restore.py report
```

Read the restored implementation and explain why it passes the edge cases. Restart Streamlit after editing learner code if its running session still shows the previous result.

## 3. Reproduce the saved scores without an API

From the project folder:

```sh
python scripts/verify_evidence.py
python runner/score.py --raw results/raw --out results/local/recomputed
python runner/compare.py --results results/local/recomputed --models gemini-3.1-flash-lite,gemini-3.6-flash --per-level 30
```

The paired hard set should still show **11/16** exact invoices for Flash-Lite and **15/16** for Flash 3.6. The scorer fixes do not change these original records because the original dataset has no repeated line-item descriptions. New output is written separately; do not delete the historical raw responses to force a rerun.

## 4. Optional: make one new extraction

Use **Review an invoice → New extraction**. Pick a synthetic sample or upload a PNG/JPEG of at most 10 MB and 20 million pixels. PDFs are not supported. An optional JSON answer key must contain all eight fields; without one, the output is explicitly **unscored**.

Paste your own Gemini key into the password field or copy `.env.example` to `.env` and set `GEMINI_API_KEY`. Never commit a real `.env`. Click **Extract once** only when ready. One click makes at most one provider request, with SDK retries disabled. Quota errors are not retried. Charges depend on your Google account and model; free quota is not guaranteed. Your image is sent to Google. Do not use confidential invoices; read Google's current [data terms](https://ai.google.dev/gemini-api/terms) first. The app does not write uploaded images or typed keys to persistent storage.

For a bounded command-line experiment, preview the work first:

```sh
python runner/run_models.py --model gemini-3.1-flash-lite --levels level1_clean --per-level 1 --out results/local/experiment-01/raw --dry-run
```

This prints `WOULD RUN` without contacting Google. To make that one real request, set your key and run the same command **without `--dry-run`**. New runs use a structured output schema and explicit date policy, so they are a separate experiment, not a replication of the historical prompt. Request fingerprints prevent silently reusing results from a different image, prompt or schema. Use a new output directory when the experiment changes.

## 5. Extend responsibly

Before testing real documents, add independently designed layouts, languages and repeated descriptions. Have a human label image legibility without seeing model outputs. Agree on date and rounding rules before running models. Keep API failures separate from extraction errors and compare only shared invoice IDs. Record prompt, model version, image hash, retries, elapsed time and usage. This app does not establish production OCR accuracy or endorse a model based on 16 invoices.

`docs/METHODOLOGY.md` contains the full boundaries; `docs/ACCEPTANCE.md` is the release checklist. The tests use mocks and saved evidence; **they make no paid provider requests**.

## License

Apache License 2.0. Preserve `LICENSE` and `NOTICE` when redistributing. The project is a teaching workbench, not accounting or payment-approval software.
