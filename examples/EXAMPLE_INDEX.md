# Evaluation examples

Worked examples of the evaluation bundle in use. Each example is a self-contained directory: spec, DTU profile(s), automation, metrics extraction, and historical results.

These are not the only way to set up an evaluation. They are example shapes we find useful. Copy and adapt.

## Index

| # | Directory | What it measures | Type |
|---|-----------|------------------|-------|
| 01 | [`01-explorer-removal/`](./01-explorer-removal/README.md) | The contribution of the `foundation:explorer` agent: the same exploration task run against foundation WITH vs WITHOUT the explorer, comparing root-context tokens, delegations, citations, and answer quality. | A/B comparison, two-variant, built on the `amplifier_evaluation` library with a custom harness + metric comparison |
| 02 | [`02-hle-foundation/`](./02-hle-foundation/README.md) | Amplifier foundation's correctness on a single, pinned Humanity's Last Exam (HLE) question, judged by HLE's published judge prompt in a separate amplifier session. | Off-the-shelf benchmark, single-variant, capability measurement |
| 03 | [`03-swebench-multimodal-foundation/`](./03-swebench-multimodal-foundation/README.md) | Amplifier foundation's ability to resolve a single, pinned SWE-bench Multimodal GitHub issue. Patch graded programmatically by the official `swebench` harness (Docker-based test runner) on the host. | Off-the-shelf benchmark, single-variant, code-patch task, programmatic grading |
| 04 | [`04-foundation-vs-dev-demo/`](./04-foundation-vs-dev-demo/README.md) | End-to-end demo: 3 HLE tasks and 3 SWE-bench tasks, each run against two bundle variants (`foundation` and `amplifier-dev`) for 12 parallel runs, aggregated into one self-contained HTML report. | Multi-task, two-variant demo, mixed judge + programmatic grading |
