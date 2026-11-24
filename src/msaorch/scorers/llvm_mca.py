"""
Wrapper around `llc` and `llvm-mca`: given a (src, tgt) pair of LLVM IR,
compile both to assembly, estimate their performance, and return a structured
comparison.
"""

from dataclasses import asdict, dataclass
from enum import Enum

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
