"""SCRATCH ONLY -- deliberately broken, to prove the CI can go RED.

Second red variant: this file IS ruff-formatted, so the `Check formatting`
step passes and execution reaches the `Lint (library only)` step, which the
first variant never got to run (it was skipped after format failed).

  * ruff check src tests -> F401, `os` imported but unused
  * pytest tests/        -> the assertion below is false
"""

from __future__ import annotations

import os


def test_ci_is_wired_and_can_fail():
    expected = 1
    actual = 2
    assert actual == expected, "deliberate failure: proving this CI reports RED"
