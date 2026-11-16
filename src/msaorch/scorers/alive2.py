"""Wrapper around Alive2's `alive-tv`: given a (src, tgt) pair of LLVM IR,
check that tgt refines src and return a structured result.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


# ----------- Result Types ----------- #

class Verdict(Enum):
    CORRECT = "correct"             # every transformation verified
    INCORRECT = "incorrect"         # at least one transformation has a counterexample
    INCONCLUSIVE = "inconclusive"   # failed-to-prove, or nothing was checked
    ERROR = "error"                 # alive-tv missing, crashed, timed out, or bad IR


@dataclass
class Alive2Summary:
    correct: int = 0
    incorrect: int = 0
    failed_to_prove: int = 0
    errors: int = 0


@dataclass
class Alive2Result:
    verdict: Verdict
    summary: Alive2Summary
    counterexample: str | None = None  # the "Example:" block of the first failure
    error_message: str | None = None
    raw_output: str = ""
