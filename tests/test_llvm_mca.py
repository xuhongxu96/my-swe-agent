import json
import shutil
from pathlib import Path

import pytest

from msaorch.scorers.llvm_mca import (
    McaStats,
    Verdict,
    _parse_stats,
    analyze,
    compare,
)

FIXTURES = Path(__file__).parent / "fixtures" / "llvm_mca"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


# ----------- Stats ----------- #


def test_stats_distributed():
    stats = _parse_stats(read_fixture("distributed.json"))
    assert stats == McaStats(
        iterations=100,
        instructions=400,
        total_cycles=305,
        total_uops=600,
        ipc=1.3114754098360655,
        block_rthroughput=2.0,
    )


def test_stats_empty_output_is_none():
    assert _parse_stats("") is None


def test_stats_no_regions_is_none():
    assert _parse_stats('{"CodeRegions": []}') is None


# ----------- compare ----------- #


def test_compare_fewer_cycles_is_improved():
    result = compare(read_fixture("distributed.json"), read_fixture("factored.json"))
    assert result.verdict == Verdict.IMPROVED
    assert result.src.total_cycles == 305
    assert result.tgt.total_cycles == 109


def test_compare_more_cycles_is_regressed():
    result = compare(read_fixture("factored.json"), read_fixture("distributed.json"))
    assert result.verdict == Verdict.REGRESSED


def test_compare_same_cycles_is_unchanged():
    output = read_fixture("factored.json")
    assert compare(output, output).verdict == Verdict.UNCHANGED


def test_compare_missing_tgt_stats_is_error():
    result = compare(read_fixture("factored.json"), "")
    assert result.verdict == Verdict.ERROR
    assert result.src is not None
    assert "tgt" in result.error_message


def test_to_dict_is_json_friendly():
    output = read_fixture("factored.json")
    data = compare(output, output).to_dict()
    assert data["verdict"] == "unchanged"
    json.dumps(data)  # raises if anything isn't JSON-serializable


# ----------- analyze ----------- #


def make_fake_tool(tmp_path, name, script_body):
    script = tmp_path / name
    script.write_text("#!/bin/sh\n" + script_body + "\n")
    script.chmod(0o755)
    return script


def test_analyze_with_fake_tools(tmp_path):
    fake_llc = make_fake_tool(tmp_path, "fake-llc", "exit 0")
    fake_mca = make_fake_tool(
        tmp_path, "fake-llvm-mca", f"cat {FIXTURES / 'factored.json'}"
    )
    result = analyze("src", "tgt", llc=fake_llc, llvm_mca=fake_mca)
    assert result.verdict == Verdict.UNCHANGED


def test_analyze_llc_failure_is_error(tmp_path):
    fake_llc = make_fake_tool(tmp_path, "fake-llc", "echo 'bad IR' >&2; exit 1")
    result = analyze("src", "tgt", llc=fake_llc)
    assert result.verdict == Verdict.ERROR
    assert result.error_message.startswith("src:")
    assert "bad IR" in result.error_message


def test_analyze_missing_binary_is_error():
    result = analyze("", "", llc="definitely-not-llc")
    assert result.verdict == Verdict.ERROR


def test_analyze_timeout_is_error(tmp_path):
    fake_llc = make_fake_tool(tmp_path, "fake-llc", "sleep 5")
    result = analyze("", "", llc=fake_llc, timeout_s=1)
    assert result.verdict == Verdict.ERROR
    assert "timed out" in result.error_message


@pytest.mark.skipif(
    shutil.which("llc") is None or shutil.which("llvm-mca") is None,
    reason="llc or llvm-mca not installed",
)
def test_analyze_end_to_end():
    src = read_fixture("distributed.ll")
    tgt = read_fixture("factored.ll")
    result = analyze(src, tgt)
    assert result.verdict == Verdict.IMPROVED
