"""Helpers shared by the scorer wrappers (alive2, llvm-mca)."""

import subprocess


class ToolError(Exception):
    pass


# Run an external tool and return the finished process, or raise ToolError if
# it couldn't start, timed out, or (with check=True) exited non-zero.
def run_tool(
    command: list[str], timeout_s: int, *, check: bool = False
) -> subprocess.CompletedProcess:
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout_s
        )
    except OSError as error:  # e.g. the tool isn't installed
        raise ToolError(f"could not run {command[0]}: {error}") from error
    except subprocess.TimeoutExpired as error:
        raise ToolError(f"{command[0]} timed out after {timeout_s}s") from error

    if check and completed.returncode != 0:
        raise ToolError(f"{command[0]} failed: {completed.stderr.strip()}")

    return completed
