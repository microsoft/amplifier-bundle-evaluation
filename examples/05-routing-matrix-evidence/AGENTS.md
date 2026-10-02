# Routing evidence example — continuation rules

Read `README.md`, `DESIGN.md`, `REVIEW.md` and `RESULT-REUSE.md` before changing this example. Repo conventions and more-specific rules still apply. The v3 offline implementation review and the expanded reuse/catalog method review are distinct: both requested expanded reviewers support scoped planning, not live readiness, fixture clearance or implementation authorization. Keep those boundaries explicit.

## Current executable boundary

`evidence.py` and thin Click `cli.py` implement **offline** plan/readiness/analyze. There is no live executor, production event normalizer, budget enforcer or qualified benchmark result archive. Readiness must remain unsupported until a separately instrumented adapter passes actual acceptance. Synthetic receipts test logic; they are not model-performance results or authenticated traces.

Keep generic execution/evidence ownership here; do not change production routing IDs/preferences in this example. Future consumer adapters reuse the evaluation library's TaskSpec/AgentSpec/DTU/installer/AIUser/Extractor/Grader bricks. A stock run_trial completion can contain failed extraction/grading; it is not valid grade evidence. Do not fake injectable lifecycle/telemetry hooks that do not exist.

## Offline verification

From this example, using an existing environment with pytest, Click and PyYAML:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  python -m pytest -q -p no:cacheprovider test_evidence.py
ruff check --no-cache .
ruff format --check --no-cache .
```

Check the actual pinned evaluation `load_task` and `GraderConfig.from_yaml` contracts for new task adapters. Counts, complete criterion IDs/bounds/weights and hashes must agree. Do not launch runtime setup or download protected fixtures just to validate planning. Do not install into a running shared CLI. A scratch AMPLIFIER_HOME does not isolate its shared editable installation.

Preserve all scheduled cells, immutable attempts and costs. Missing grade is not zero; invalid grade cannot establish critical status; a failed necessary success threshold remains failure despite other unknown critical checks. Unknown cost is not zero. Multiple attempts remain blocked without a reviewed retry policy. Reject inheritance-erased experiments rather than silently measuring equal arms.

## Privacy and execution

No raw event capture reads into agent context. Use the capture-navigation owner for private discovery and bounded versioned adapters for normalized evidence. Do not commit private source maps, account/host identities, secret/config-derived hashes, raw artifacts or heldout answers. Newly authored synthetic public fixtures still need independent keys, lineage/difficulty calibration and license review.

Preserve only generic causal failure mechanisms from private inspiration. Author new domains, structures, inputs and references in a fresh context that has never seen private records. Obtain authorized abstract-handoff clearance and independent finished-fixture privacy/rights review; assess challenge/grader fitness separately. The task's novelty or difficulty does not make it safe to publish.

Live output requires an explicit private ignored directory outside source repos, approved budget and isolated acquisition/subject/assessment environments. No personal HOME/browser/key-store mounts or unmetered application egress. Register resources immediately and reconcile cleanup. Output exports require allowlists, local identity scans and fresh-context review; dashboards and CI artifacts count as publication.

Do not auto-run paid recurrence or mutate shipping matrix policy. If sources/tasks/grader/runtime change, use the reuse disposition in `RESULT-REUSE.md`; never relabel old scores as fresh execution. Capture tested commands, remaining gaps and agreed decisions here or in the document that owns them, without importing private project context.
