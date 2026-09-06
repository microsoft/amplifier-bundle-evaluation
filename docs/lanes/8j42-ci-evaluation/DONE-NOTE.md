# Lane 8j42 — CI for `amplifier-bundle-evaluation`

**Item:** `model_performance-8j42` (project `model_performance`)
**Repo:** `microsoft/amplifier-bundle-evaluation`
**Base:** `main` @ `3531ccdc34dbdaeb45e726c621046014a8f2e14f`
**Branch:** `lane/8j42-ci-evaluation`
**Outcome:** **A — RESOLVED.** All deliverables DONE. Nothing recorded NOT-POSSIBLE.
**Date:** 2026-09-06

---

## 1. Result in one paragraph

`microsoft/amplifier-bundle-evaluation` had **no `.github/` directory at all** — no workflows, no
Dependabot config. Every merge to this repo (`#24`–`#28`, and every eval commit before them) was
verified by lane- or manager-run suites, never by GitHub CI. This lane adds one workflow,
`.github/workflows/ci.yml`, modelled on the sibling `amplifier-bundle-context-intelligence` CI, and
then **proved it can go red across every fallible step it contains** — four steps, three deliberately
broken scratch commits, four red job results — before opening the real PR green.

---

## 2. Deliverables

| # | Deliverable | State |
|---|---|---|
| 1 | `.github/workflows/ci.yml` on push+PR: ruff scoped to the library, pytest, import smoke | **DONE** |
| 2 | Explicit evidence that large fixture data is neither linted nor installed | **DONE** (§4) |
| 3 | No example harness reachable from the workflow | **DONE** (§5) |
| 4 | RED run URL and GREEN run URL both quoted in the real PR body | **DONE** (§3) |
| 5 | Workflow only (+ minimal fixes); STOP and report if clean main is red in CI | **DONE** — clean main is green; zero source or config files changed (§6) |

---

## 3. The red proof — four steps, each independently observed RED

A CI that has never been observed red is decoration. This workflow has four steps that can fail.
**Every one of them was observed failing on a real GitHub-hosted run**, on scratch branch
`scratch/8j42-ci-red-proof` (PR #29, now **closed, branch deleted**).

| Variant | Scratch SHA | What was broken | Run (RED) |
|---|---|---|---|
| 1 | `f5226344c14c5b2fff3045264175427bb56f4ebb` | test file not ruff-formatted **and** assertion false | [34062107293](https://github.com/microsoft/amplifier-bundle-evaluation/actions/runs/34062107293) |
| 2 | `5108e9b1219b2895b093c58f8332745e09dbf47b` | format-clean, `F401` unused import **and** assertion false | [34062656818](https://github.com/microsoft/amplifier-bundle-evaluation/actions/runs/34062656818) |
| 3 | `9d2a3abe79faedf9dc81abbd863ed66973fe48b7` | lint-clean; `__init__.py` raises on import | [34063051252](https://github.com/microsoft/amplifier-bundle-evaluation/actions/runs/34063051252) |

Per-step attribution, read back from the GitHub API (`gh run view --json jobs`):

| Workflow step | Observed RED in | Job results |
|---|---|---|
| `Check formatting (library only)` | variant 1 | `Lint: failure` |
| `Lint (library only)` | variant 2 | `Lint: failure` (format step `success` first, so this step actually ran) |
| `Run tests` | variants 1 and 2 | `Tests — Python 3.11/3.12/3.13: failure` (all three) |
| `Import smoke` | variant 3 | `Tests — Python 3.11/3.12/3.13: failure`, `Run tests: skipped`, and `Lint: success` |

Variant 2 exists because in variant 1 the `Lint (library only)` step was **skipped** — the format step
failed first — so `ruff check` itself had not been proven to fail. Variant 3 exists because in
variants 1–2 `Import smoke` was **green**, so it had not been proven to fail either. A step that has
only ever passed is indistinguishable from a step that swallows its exit code.

**GREEN:** [34062139183](https://github.com/microsoft/amplifier-bundle-evaluation/actions/runs/34062139183)
at `bc76d576dced621d1e47337b78812a60b15ec378` — all four jobs `success`.
(A second green run follows on the commit that adds this note; the PR body quotes the latest.)

---

## 4. What is NOT linted, and what is NOT installed — with the mechanism named

The goal warned about `ai-notes/` and captured runs. **Neither exists in this repo** — `git ls-files`
returns **0** files under `ai-notes/`, and there is no capture corpus here. Those live in the evals
program repo, not in this module. The analogous hazard here is real but differently shaped, and it was
measured rather than assumed.

**What is actually large and lintable-but-shouldn't-be:**

| Path | Size / count | Why it must not be linted or treated as library code |
|---|---|---|
| `amplifier-benchmark/tasks/` | **51 MB**, 157 tracked files | Benchmark task fixtures: `graspologic.zip` (6.6 MB ×2), `hr_report.pdf` (4.3 MB ×5), generated PNGs. Includes two `grader-data/*.py` scripts mounted **verbatim** into a grading container. |
| `examples/` | 9 `.py` | Example harnesses — they spend money and need DTUs. |
| `.amplifier/evaluations/tasks/01-.../workspace/` | 1 `.py` | A deliberately-imperfect fixture bundle that a task is *scored on*. Reformatting it would change the thing under test. |

**The measurement (clean `main` @ `3531ccd`, ruff 0.15.14):**

```
$ ruff format --check .            ->  exit 1
Would reformat: amplifier-benchmark/tasks/chiptune_generator/grader-data/analyze_midi.py
Would reformat: amplifier-benchmark/tasks/pixel_art_generator/grader-data/validate_sprites.py
Would reformat: examples/04-foundation-vs-dev-demo/swebench/grade.py
3 files would be reformatted, 35 files already formatted

$ ruff format --check src tests    ->  exit 0
26 files already formatted

$ ruff check src tests             ->  exit 0
All checks passed!
```

**A verbatim copy of the sibling repo's `ruff format --check .` step would have been RED on clean
main on day one** — on three files that are fixtures, not library code. That is the whole trap, and it
is why the scoping is load-bearing rather than cosmetic.

**Mechanism relied on: explicit path arguments in the workflow** — `ruff format --check src tests`
and `ruff check src tests`. `pyproject.toml` has **no `[tool.ruff]` section**, so there is no existing
config to honour; an unscoped `ruff .` walks the entire tree. Two mechanisms were available:

1. **CLI path args in the workflow** (chosen). Zero repo-config change — satisfies "workflow only"
   exactly. Cost: a contributor running a bare `ruff .` locally sees the three fixture failures CI
   does not.
2. **Add `[tool.ruff]` to `pyproject.toml`** (not chosen). Local and CI would agree, but it changes
   repo-wide behaviour beyond the workflow, which this lane was scoped out of.

Decision recorded, per "no waiting on a human decision". The workflow comment points at option 2 as
the preferred follow-up if a `[tool.ruff]` section is ever added.

**What is NOT installed.** `pyproject.toml`'s
`[tool.hatch.build.targets.wheel.force-include]` copies the whole `amplifier-benchmark/` tree into the
installed package — **measured 52 MB in `site-packages/amplifier_evaluation/`, even for an editable
`uv sync`**. The `lint` job therefore syncs with **`--only-group dev`** and runs ruff via
`uv run --frozen --only-group dev`, which **never builds or installs the project**. Verified in a
clean throwaway environment:

```
$ UV_PROJECT_ENVIRONMENT=/tmp/... uv sync --frozen --only-group dev
Installed 10 packages    # ruff, pytest, pyright, ... — no amplifier-* at all
$ ls $VENV/lib/python3.13/site-packages/ | grep -i amplifier
NOT INSTALLED (good)
$ uv run --frozen --only-group dev ruff format --check src tests   # 0.15s
$ ls $VENV/lib/python3.13/site-packages/ | grep -i amplifier
STILL NOT INSTALLED (good)
```

The `test` job **does** `uv sync --frozen`, and therefore does pay the 52 MB local copy. That is
deliberate and unavoidable: the benchmark suite is *intended* to ship inside the wheel
(`harness/resources.py` resolves it at runtime), so installing it is exactly what a real consumer
does, and the import smoke would be testing a fiction otherwise. It is a local filesystem copy from a
checkout that already contains the bytes — not a network install, and not lint noise.

---

## 5. No example harness, no money, no keys

No step in `ci.yml` invokes `examples/*/run.sh`, `examples/01-explorer-removal/harness.py`,
`scripts/run_benchmark.py`, `.amplifier/evaluations/run.sh`, `amplifier-digital-twin`, or any
LLM-backed validation recipe. Checked mechanically:

```
$ grep -nE "examples/|run\.sh|run_benchmark|amplifier-digital-twin|API_KEY|secrets\." .github/workflows/ci.yml
12:# NOTHING HERE RUNS AN EVAL. The example harnesses under `examples/`, ...
13:# benchmark runner, and `.amplifier/evaluations/run.sh` all spend real money ...
25:  # harnesses under `examples/` and a fixture bundle checked in under ...
34:  # `examples/04-foundation-vs-dev-demo/swebench/grade.py`) while ...
```

All four hits are **comment lines**. No executable step references them. `permissions: contents: read`
only; no `secrets.*` reference anywhere; the workflow needs no API key. `tests/` holds unit tests that
stub the DTU CLI and assert argv/envelope contracts — no network, no container, no spend.

---

## 6. Clean main is GREEN in CI — nothing was papered over

The instruction was to STOP and report if clean main is red in CI. It is not.

- Run [34062139183](https://github.com/microsoft/amplifier-bundle-evaluation/actions/runs/34062139183)
  at `bc76d57` (= `main` `3531ccd` + the workflow file, nothing else): **4/4 jobs success**.
- Locally, before pushing anything: `ruff format --check src tests` 26 files clean, `ruff check src
  tests` clean, `pytest tests/ -q` **26 passed in 0.15s** on **both** Python 3.11.14 and 3.13.11,
  import smoke OK on both.
- **No `continue-on-error` anywhere. No test selection narrowed. No `--ignore`. No source file
  changed.** The only file in the real PR's diff is `.github/workflows/ci.yml` (plus this lane note).

One honest caveat: **Python 3.12 was never exercised locally** — 3.11 and 3.13 were, and 3.12 passed
in CI on the first run. It is bracketed on both sides.

---

## 7. Deviations from the goal text, and why

1. **`ai-notes/` does not exist in this repo.** The goal's premise ("this repo's `ai-notes/` and
   captured runs are large") is false for `amplifier-bundle-evaluation` — 0 tracked files under
   `ai-notes/`, no capture corpus. The real hazard is `amplifier-benchmark/tasks/` (51 MB) plus the
   example and fixture `.py` files. The lane addressed the hazard the goal was pointing at, in the
   shape it actually takes here, and measured it (§4) rather than asserting it.
2. **No `Makefile`, so no repo entry point to prefer.** The goal said to invoke `make check`/`make
   test` if they exist. They do not (`ls Makefile` → no such file). Commands are specified directly,
   matching the sibling template.
3. **Three red variants instead of one.** The goal required one observed red run. One run only proved
   two of the four fallible steps could fail; two further scratch commits closed the gap. Cost: CI
   minutes, $0.
4. **PR marked ready-for-review after green**, per the work item's own text ("DRAFT → ready. Manager
   verifies red-then-green and merges"). **Not merged** — merging is the manager's stage.

---

## 8. Spend

**SPEND AUTHORITY: $0** — arithmetic as stated in the goal: `0 runs x 0 arms x $0 / 1.00 = $0.00`,
slack `$0.00`. Workflow YAML plus CI minutes; no API calls, no DTU, no containers.

| Category | Authorized | Spent | Notes |
|---|---|---|---|
| LLM API | $0.00 | **$0.00** | No eval run, no grader, no harness, no DTU launch. |
| DTU / containers | $0.00 | **$0.00** | None created. `infra_ledger.sh` not touched — nothing to register, nothing to tear down. |
| GitHub Actions minutes | (not capped) | 5 runs × 4 jobs | 3 red (scratch, deleted), 2 green (lane). Ubuntu runners on a public repo. |

The cap did not bind. No deliverable was dropped. **Outcome branch A, not B.**

---

## 9. Open / follow-ups (not this lane's scope)

1. **`[tool.ruff]` in `pyproject.toml`** would make a bare local `ruff .` agree with CI. Today it does
   not: locally `ruff format --check .` exits 1 on three fixture files. See §4 option 2.
2. **No `dependabot.yml`.** The sibling template repo has one; this repo does not. Out of scope here
   ("workflow only"), but it is the other half of the CI parity gap.
3. **`ruff check .` currently passes** while `ruff format --check .` does not — so a future decision
   to widen the scope is cheap for `check` and costs three fixture reformats for `format`.
4. **Three sibling repos still have no workflows** per the program's CI sweep (7 green, 4 with none).
   This lane closes one of the four.
