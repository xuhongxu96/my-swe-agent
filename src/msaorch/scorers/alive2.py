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


""" 
- Read the counts from the "Summary:" block alive-tv prints at the end.
- Returns None if there is no summary, which means alive-tv stopped before reading anything

- The summary looks like this (format from tools/alive-tv.cpp in Alive2):

    Summary:
         1 correct transformations
         0 incorrect transformations
         0 failed-to-prove transformations
         0 Alive2 errors
"""
def _parse_summary(output: str) -> Alive2Summary | None:

    if "Summary:" not in output:
        return None

    summary_text = output.split("Summary:")[1]
    lines = summary_text.strip().splitlines()[:4]  # only the 4 count lines

    summary = Alive2Summary()
    for line in lines:
        # "1 correct transformations" -> number="1", label="correct transformations"
        number, label = line.strip().split(" ", 1)

        if label == "correct transformations":
            summary.correct = int(number)
        elif label == "incorrect transformations":
            summary.incorrect = int(number)
        elif label == "failed-to-prove transformations":
            summary.failed_to_prove = int(number)
        elif label == "Alive2 errors":
            summary.errors = int(number)

    return summary
