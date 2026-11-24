"""
Wrapper around `llc` and `llvm-mca`: given a (src, tgt) pair of LLVM IR,
compile both to assembly, estimate their performance, and return a structured
comparison.
"""

import json
from dataclasses import asdict, dataclass
from enum import Enum

# ----------- llvm-mca JSON Keys ----------- #
# exact keys llvm-mca prints with --json (tools/llvm-mca/Views/SummaryView.cpp in LLVM)

CODE_REGIONS = "CodeRegions"
SUMMARY_VIEW = "SummaryView"

# ----------- Result Types ----------- #


class Verdict(Enum):
    IMPROVED = "improved"    # tgt takes fewer simulated cycles than src
    REGRESSED = "regressed"  # tgt takes more simulated cycles than src
    UNCHANGED = "unchanged"  # same number of simulated cycles
    ERROR = "error"          # llc/llvm-mca missing, crashed, timed out, or bad IR


@dataclass
class McaStats:
    iterations: int    # how many times llvm-mca simulated the code (default 100)
    instructions: int  # instructions executed across all iterations
    total_cycles: int  # simulated cycles across all iterations
    total_uops: int
    ipc: float         # instructions per cycle
    # estimated cycles per iteration, from port usage only (ignores latency)
    block_rthroughput: float


@dataclass
class McaResult:
    verdict: Verdict
    src: McaStats | None  # None if that side failed before llvm-mca finished
    tgt: McaStats | None
    error_message: str | None = None
    raw_output: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)                   # converts nested src/tgt stats too
        data["verdict"] = self.verdict.value  # Enum isn't JSON-friendly, use its text
        return data


# ----------- Parser ----------- #


"""
- Read the stats from the "SummaryView" of llvm-mca's --json output.
- Returns None if the output isn't valid JSON or has no code region, which
  means llvm-mca failed (it prints nothing to stdout on errors)

- The summary looks like this (one per code region):

    "SummaryView": {
      "BlockRThroughput": 1,
      "DispatchWidth": 6,
      "IPC": 1.834862385321101,
      "Instructions": 200,
      "Iterations": 100,
      "TotalCycles": 109,
      "TotaluOps": 400,
      "uOpsPerCycle": 3.669724770642202
    }
"""


def _parse_stats(output: str) -> McaStats | None:
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return None

    regions = data.get(CODE_REGIONS, [])
    if not regions:
        return None

    summary = regions[0][SUMMARY_VIEW]

    return McaStats(
        iterations=summary["Iterations"],
        instructions=summary["Instructions"],
        total_cycles=summary["TotalCycles"],
        total_uops=summary["TotaluOps"],
        ipc=summary["IPC"],
        # JSON writes whole numbers like 1.0 as 1, so make it a float again
        block_rthroughput=float(summary["BlockRThroughput"]),
    )
