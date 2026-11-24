import json
import shutil
from pathlib import Path

import pytest

from msaorch.scorers.alive2 import (
    Alive2Summary,
    Verdict,
    _extract_failures,
    _parse_summary,
    parse_output,
    verify,
)

FIXTURES = Path(__file__).parent / "fixtures" / "alive2"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


# ----------- Summary ----------- #


def test_summary_two_transformations():
    summary = _parse_summary(read_fixture("two_transformations.txt"))
    assert summary == Alive2Summary(correct=1, incorrect=1)


def test_summary_missing_is_none():
    assert _parse_summary("Target file is broken\n") is None


# ----------- Failures ----------- #


def test_failures_only_from_failing_transformation():
    [failure] = _extract_failures(read_fixture("two_transformations.txt"))
    assert failure.reason == "Value mismatch"
    assert failure.counterexample.startswith("Example:")
    assert failure.counterexample.endswith("Target value: #x04 (4)")


def test_failures_poison_reason():
    [failure] = _extract_failures(read_fixture("incorrect_poison.txt"))
    assert failure.reason == "Target is more poisonous than source"


# ----------- parse_output ----------- #


def test_parse_correct():
    result = parse_output(read_fixture("correct.txt"))
    assert result.verdict == Verdict.CORRECT
    assert result.failures == []


def test_parse_one_incorrect_makes_it_incorrect():
    result = parse_output(read_fixture("two_transformations.txt"))
    assert result.verdict == Verdict.INCORRECT


def test_parse_no_summary_is_error():
    result = parse_output("Target file is broken\n")
    assert result.verdict == Verdict.ERROR
    assert result.error_message == "Target file is broken"


def test_parse_nothing_checked_is_inconclusive():
    output = (
        "Summary:\n"
        "  0 correct transformations\n"
        "  0 incorrect transformations\n"
        "  0 failed-to-prove transformations\n"
        "  0 Alive2 errors\n"
    )
    assert parse_output(output).verdict == Verdict.INCONCLUSIVE


def test_to_dict_is_json_friendly():
    data = parse_output(read_fixture("two_transformations.txt")).to_dict()
    assert data["verdict"] == "incorrect"
    json.dumps(data)  # raises if anything isn't JSON-serializable


# ----------- verify ----------- #


def make_fake_alive_tv(tmp_path, script_body):
    script = tmp_path / "fake-alive-tv"
    script.write_text("#!/bin/sh\n" + script_body + "\n")
    script.chmod(0o755)
    return script


def test_verify_with_fake_alive_tv(tmp_path):
    fake = make_fake_alive_tv(tmp_path, f"cat {FIXTURES / 'two_transformations.txt'}")
    result = verify("src", "tgt", alive_tv=fake)
    assert result.verdict == Verdict.INCORRECT


def test_verify_missing_binary_is_error():
    result = verify("", "", alive_tv="definitely-not-alive-tv")
    assert result.verdict == Verdict.ERROR


def test_verify_timeout_is_error(tmp_path):
    fake = make_fake_alive_tv(tmp_path, "sleep 5")
    result = verify("", "", alive_tv=fake, timeout_s=1)
    assert result.verdict == Verdict.ERROR
    assert "timed out" in result.error_message


@pytest.mark.skipif(shutil.which("alive-tv") is None, reason="alive-tv not installed")
def test_verify_end_to_end():
    src = read_fixture("two_transformations_src.ll")
    tgt = read_fixture("two_transformations_tgt.ll")
    result = verify(src, tgt)
    assert result.summary == Alive2Summary(correct=1, incorrect=1)
