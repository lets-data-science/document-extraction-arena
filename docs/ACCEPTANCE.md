# Local acceptance checklist

- [ ] Python 3.13 environment installs `requirements.txt` and `python -m pip check` passes.
- [ ] `python -m pytest -q` passes in the reference. Starter fails only until exercises are completed or checkpoints restored.
- [ ] Evidence hashes verify; rescoring reproduces 11/16 and 15/16 on identical hard-set IDs.
- [ ] Saved replay works with no provider key; date mismatch and model switch agree with raw data.
- [ ] Repeated descriptions cannot reuse one predicted row; invalid amounts and invalid answer keys are rejected.
- [ ] No-key live action makes no request. Quota/auth failures never retry. Error messages and reports contain no key.
- [ ] Unknown prices are blank; unknown/all-error comparison models are not silently presented as a paired comparison.
- [ ] Starter, reference, LICENSE, NOTICE, checkpoints and platform setup instructions are included.
- [ ] Mobile/tablet/desktop layouts, captions and walkthrough assets are reviewed on the LDS preview.
- [ ] No `.env`, venv, caches, private uploads, generated narration credentials or local experiment results enter the ZIPs.
- [ ] Human approval precedes any commit, publication or deployment.

Recorded historical responses are not a test of current Gemini availability. A real API smoke test is optional and incurs quota; test results alone do not claim it was run.
