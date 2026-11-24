"""
Wrapper around `llc` and `llvm-mca`: given a (src, tgt) pair of LLVM IR,
compile both to assembly, estimate their performance, and return a structured
comparison.
"""

import json
import tempfile
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from msaorch.scorers.utils import ToolError, run_tool

# ----------- llvm-mca JSON Keys ----------- #
# exact keys llvm-mca prints with --json (tools/llvm-mca/Views/SummaryView.cpp in LLVM)

CODE_REGIONS = "CodeRegions"
SUMMARY_VIEW = "SummaryView"

# ----------- Result Types ----------- #


class Verdict(Enum):
    IMPROVED = "improved"  # tgt takes fewer simulated cycles than src
    REGRESSED = "regressed"  # tgt takes more simulated cycles than src
    UNCHANGED = "unchanged"  # same number of simulated cycles
    ERROR = "error"  # llc/llvm-mca missing, crashed, timed out, or bad IR


@dataclass
class McaStats:
    iterations: int  # how many times llvm-mca simulated the code (default 100)
    instructions: int  # instructions executed across all iterations
    total_cycles: int  # simulated cycles across all iterations
    total_uops: int
    ipc: float  # instructions per cycle
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
        data = asdict(self)  # converts nested src/tgt stats too
        data["verdict"] = self.verdict.value  # Enum isn't JSON-friendly, use its text
        return data


# ----------- Runner ----------- #


# Compile src and tgt to assembly with llc, run llvm-mca on both, and compare.
def analyze(
    src_ir: str,
    tgt_ir: str,
    *,
    llc: str | Path = "llc",
    llvm_mca: str | Path = "llvm-mca",
    # pinned so results don't depend on the machine running the scorer
    triple: str = "x86_64-unknown-linux-gnu",
    mcpu: str = "skylake",
    timeout_s: int = 60,  # per tool call, so up to 4x this in total
) -> McaResult:
    target_flags = [f"-mtriple={triple}", f"-mcpu={mcpu}"]
    outputs = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        for name, ir in [("src", src_ir), ("tgt", tgt_ir)]:
            ir_path = Path(tmp_dir) / f"{name}.ll"
            asm_path = Path(tmp_dir) / f"{name}.s"
            ir_path.write_text(ir)

            llc_command = [str(llc), *target_flags, str(ir_path), "-o", str(asm_path)]
            mca_command = [str(llvm_mca), *target_flags, "--json", str(asm_path)]
            # a failed llc/llvm-mca prints nothing useful to stdout, so the
            # exit code is the only reliable signal (check=True)
            try:
                run_tool(llc_command, timeout_s, check=True)
                completed = run_tool(mca_command, timeout_s, check=True)
            except ToolError as error:
                return _error_result(f"{name}: {error}")
            outputs.append(completed.stdout)

    src_output, tgt_output = outputs
    return compare(src_output, tgt_output)


def _error_result(message: str) -> McaResult:
    return McaResult(verdict=Verdict.ERROR, src=None, tgt=None, error_message=message)


# ----------- Parser ----------- #


"""
- Turn the llvm-mca outputs for src and tgt into an McaResult.
- The verdict compares TotalCycles, checked in this order:

    either side has no stats   -> ERROR      (llvm-mca failed on that side)
    tgt cycles < src cycles    -> IMPROVED
    tgt cycles > src cycles    -> REGRESSED
    otherwise                  -> UNCHANGED

- TotalCycles is used over BlockRThroughput because it is simulated, so it
  also counts time spent waiting on dependencies (BlockRThroughput doesn't)
"""


def compare(src_output: str, tgt_output: str) -> McaResult:
    src = _parse_stats(src_output)
    tgt = _parse_stats(tgt_output)
    raw_output = f"--- src ---\n{src_output}\n--- tgt ---\n{tgt_output}"

    if src is None or tgt is None:
        failed_side = "src" if src is None else "tgt"
        return McaResult(
            verdict=Verdict.ERROR,
            src=src,
            tgt=tgt,
            error_message=f"llvm-mca gave no stats for {failed_side}",
            raw_output=raw_output,
        )

    if tgt.total_cycles < src.total_cycles:
        verdict = Verdict.IMPROVED
    elif tgt.total_cycles > src.total_cycles:
        verdict = Verdict.REGRESSED
    else:
        verdict = Verdict.UNCHANGED

    return McaResult(verdict=verdict, src=src, tgt=tgt, raw_output=raw_output)


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
