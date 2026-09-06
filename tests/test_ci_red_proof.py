"""SCRATCH ONLY -- deliberately broken, to prove the CI can go RED.

This file exists on a throwaway branch and is never merged. It is broken in
two independent ways at once so a single scratch PR proves BOTH jobs fail:

  * ruff format --check src tests  -> the spacing below is not ruff-formatted
  * pytest tests/                  -> the assertion below is false

A CI that has never been observed red is decoration.
"""

from __future__ import annotations


def test_ci_is_wired_and_can_fail():
    expected   =   1
    actual = 2
    assert actual == expected, "deliberate failure: proving this CI reports RED"
