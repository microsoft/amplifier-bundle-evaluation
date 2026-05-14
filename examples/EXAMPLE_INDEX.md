# Evaluation examples

Worked examples of the evaluation bundle in use. Each example is a self-contained directory: spec, DTU profile(s), automation, metrics extraction, and historical results.

These are not the only way to set up an evaluation. They are example shapes we find useful. Copy and adapt.

## Index

| # | Directory | What it measures | Type |
|---|-----------|------------------|-------|
| 01 | [`01-explorer-removal/`](./01-explorer-removal/README.md) | The contribution of the `foundation:explorer` agent on a real exploration task. | Testing before and after changes, quality, metrics |
| 02 | [`02-hle-foundation/`](./02-hle-foundation/README.md) | Amplifier foundation's correctness on a single, pinned Humanity's Last Exam (HLE) question, judged by HLE's published judge prompt in a separate amplifier session. | Off-the-shelf benchmark, single-variant, capability measurement |
| 03 | [`03-swebench-multimodal-foundation/`](./03-swebench-multimodal-foundation/README.md) | Amplifier foundation's ability to resolve a single, pinned SWE-bench Multimodal GitHub issue. Patch graded programmatically by the official `swebench` harness (Docker-based test runner) on the host. | Off-the-shelf benchmark, single-variant, code-patch task, programmatic grading |
