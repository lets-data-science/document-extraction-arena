# Evidence and limits

## Historical run (preserved)

- 120 synthetic invoices, 30 at each of four levels, using one generator layout.
- Flash-Lite answered all 120. Gemini 3.6 Flash answered hard invoices 001–016. A later model has a separate saved subset; it is not part of the two-model headline.
- On the same 16 hard invoices, exact matches are 11/16 and 15/16. Mean eight-field scores are 96.0% and 99.9% after display rounding.
- Mean successful-call times are 6.534375 and 10.81375 seconds. They exclude retry and quota-wait time. Do not call these end-to-end production latency.
- Estimated paid-tier equivalents are $0.00145 and $0.00873 per invoice using the repository's October 8, 2026 price snapshot and recorded tokens. The original runs used free quota; these are not bills. Check current provider pricing before estimating a new run. Unknown-model prices remain blank rather than becoming $0.
- These figures describe this sample. They are not evidence of general accuracy, a statistically established winner, or a real-world cost forecast.

## Scoring

Seven scalar fields plus the line-item collection form eight field scores. Money and numeric row values match only when the absolute difference is **strictly less than 0.005**. Text collapses whitespace and ignores case. Dates must already be ISO YYYY-MM-DD. Currency uses a three-letter uppercase code. Extra top-level metadata is ignored.

Line items match on description, quantity, unit price and amount. Each expected and predicted row can appear in at most one pair. Maximum bipartite matching prevents double credit for repeated descriptions and avoids greedy errors when numeric tolerances overlap. Line-item credit is matched-pair count / max(expected count, predicted count). Two empty lists score 1; only one empty list scores 0. An exact invoice requires every field score to equal 1. Missing or null predicted fields earn zero. Malformed JSON earns no valid extraction; provider failures are recorded separately.

## Ambiguity matters

`level4_hard_014` prints 03/08/2026 and a US vendor address. Its answer key is March 8; Flash-Lite returned August 3. The original prompt omitted an explicit date policy. Some degraded digits are also uncertain. The generator's key records intended text, not a human-legibility guarantee. Existing upstream fairness notes cover only a small subset; they are not a complete independent human audit.

Do not relabel all these disagreements as unambiguous model failures. The UI calls them **mismatches**. Extending the benchmark requires a blind human-legibility review and varied layouts before a broader claim is defensible.

## Revised local edition

The original images, keys and raw responses are byte-preserved; `evidence-manifest.json` and `scripts/verify_evidence.py` verify their SHA-256 hashes. New scoring fixes duplicate matching and invalid-input crashes without altering historical responses. The same paired result is reproducible because the original invoices have unique row descriptions.

New API requests use a structured JSON schema, explicit generated-country date policy, bounded inputs and a request fingerprint. They store actual returned model version when provided, prompt hash, timestamp, per-attempt status and total elapsed time. They belong in a separate output directory. Retried-attempt token usage is not available after all provider errors, so reported tokens are not a guaranteed total bill across failures. The default is one attempt; transient retries require an explicit flag. No automatic quota/auth retries.

The local app uses saved records by default. Live uploads are held in session memory; temporary files are deleted after the request. API keys are not written by the app or included in exports. This is a localhost teaching app, not a hardened public upload service.
