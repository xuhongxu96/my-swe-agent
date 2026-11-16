"""Wrapper around Alive2's `alive-tv`: given a (src, tgt) pair of LLVM IR,
check that tgt refines src and return a structured result.
"""

from dataclasses import dataclass, field
from enum import Enum

# ----------- alive-tv Output Markers ----------- #
# exact strings alive-tv prints (llvm_util/compare.cpp, tools/alive-tv.cpp in Alive2)

SEPARATOR = "-" * 40  # printed before each transformation
INCORRECT_MSG = "Transformation doesn't verify!"
ERROR_PREFIX = "ERROR:"
EXAMPLE_HEADER = "Example:"
SUMMARY_HEADER = "Summary:"

# ----------- Result Types ----------- #


class Verdict(Enum):
    CORRECT = "correct"            # every transformation verified
    INCORRECT = "incorrect"        # at least one transformation has a counterexample
    INCONCLUSIVE = "inconclusive"  # failed-to-prove, or nothing was checked
    ERROR = "error"                # alive-tv missing, crashed, timed out, or bad IR


@dataclass
class Alive2Summary:
    correct: int = 0
    incorrect: int = 0
    failed_to_prove: int = 0
    errors: int = 0


@dataclass
class Alive2Failure:
    reason: str  # the text after "ERROR:", e.g. "Value mismatch"
    counterexample: str | None  # the "Example:" section, None if alive-tv gave none


@dataclass
class Alive2Result:
    verdict: Verdict
    summary: Alive2Summary
    # one entry per failing transformation, empty if none failed
    failures: list[Alive2Failure] = field(default_factory=list)
    error_message: str | None = None
    raw_output: str = ""


# ----------- Parser ----------- #


"""
- Turn the raw alive-tv output into an Alive2Result.
- The verdict comes from the Summary counts, checked in this order:

    no Summary at all         -> ERROR         (alive-tv stopped before checking)
    any incorrect             -> INCORRECT     (one bad transformation is enough)
    any Alive2 errors         -> ERROR
    any failed-to-prove       -> INCONCLUSIVE
    nothing checked at all    -> INCONCLUSIVE  (e.g. no function names matched)
    otherwise                 -> CORRECT
"""
def parse_output(output: str) -> Alive2Result:
    summary = _parse_summary(output)

    # no Summary means alive-tv stopped early and printed only an error
    # message (e.g. "Target file is broken"), so keep that message
    if summary is None:
        return Alive2Result(
            verdict=Verdict.ERROR,
            summary=Alive2Summary(),
            error_message=output.strip(),
            raw_output=output,
        )

    # pick the verdict; the order matters, the first matching rule wins
    if summary.incorrect > 0:
        verdict = Verdict.INCORRECT
    elif summary.errors > 0:
        verdict = Verdict.ERROR
    elif summary.failed_to_prove > 0:
        verdict = Verdict.INCONCLUSIVE
    elif summary.correct == 0:
        # nothing was checked at all, so there's nothing to call correct
        verdict = Verdict.INCONCLUSIVE
    else:
        verdict = Verdict.CORRECT

    return Alive2Result(
        verdict=verdict,
        summary=summary,
        failures=_extract_failures(output),
        raw_output=output,
    )


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

    if SUMMARY_HEADER not in output:
        return None

    summary_text = output.split(SUMMARY_HEADER)[1]
    lines = summary_text.strip().splitlines()[:4]  # only the 4 count lines

    summary = Alive2Summary()
    for line in lines:
        # "1 correct transformations" -> number="1", label="correct transformations"
        # assumes every line is "<number> <label>", which alive-tv always prints
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


"""
- Collect the reason and counterexample of every failing transformation, in order.
- Returns an empty list if no transformation failed.

 reason is the text after "ERROR:", counterexample is everything from "Example:" on.
"""
def _extract_failures(output: str) -> list[Alive2Failure]:
    # each transformation starts with a line of 40 dashes
    blocks = output.split(SEPARATOR)

    failures = []
    for block in blocks:
        if INCORRECT_MSG not in block:
            continue

        # everything after the first "ERROR:"
        # assumes a failing block always has "ERROR:", which is true unless
        # alive-tv runs with --quiet (we never pass that flag)
        details = block.split(ERROR_PREFIX, 1)[1]

        # the last block also has the Summary stuck on the end, so cut it off
        details = details.split(SUMMARY_HEADER)[0]

        # " Value mismatch\n\nExample:..." -> "Value mismatch"
        reason = details.strip().splitlines()[0]

        if EXAMPLE_HEADER in details:
            text_after_example = details.split(EXAMPLE_HEADER, 1)[1]
            counterexample = (EXAMPLE_HEADER + text_after_example).strip()
        else:
            counterexample = None

        failures.append(Alive2Failure(reason=reason, counterexample=counterexample))

    return failures
