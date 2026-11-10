from pathlib import Path

import pytest

from msaorch.config import (
    AgentSpec,
    HarnessConfig,
    Limits,
    RunSettings,
    ScoreSettings,
    load_config,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ----------- Valid configs ----------- #


def test_full_config():
    config = load_config(FIXTURES / "full.yaml")

    assert config == HarnessConfig(
        dataset=FIXTURES / "data/tasks.jsonl",
        limits=Limits(step_limit=100, cost_limit_usd=5, wall_time_min=180),
        configs=[
            AgentSpec(name="baseline", agent_config=FIXTURES / "agents/baseline.yaml"),
            AgentSpec(name="llvm-tools", agent_config=FIXTURES / "agents/llvm-tools.yaml"),
        ],
        run=RunSettings(output=FIXTURES / "runs/experiment1", workers=4),
        score=ScoreSettings(use=["build", "pr-tests", "alive2", "llvm-mca"]),
        prs=None,
        attempts=3,
        verbose=True,
    )


def test_minimal_config_uses_defaults():
    config = load_config(FIXTURES / "minimal.yaml")

    assert config.prs is None
    assert config.attempts == 1
    assert config.verbose is False
    assert config.run.workers == 1


def test_prs_list():
    config = load_config(FIXTURES / "prs_list.yaml")

    assert config.prs == [123, 456]


def test_prs_empty_value_means_all():
    config = load_config(FIXTURES / "prs_empty_value.yaml")

    assert config.prs is None


def test_paths_are_relative_to_config_file():
    config = load_config(FIXTURES / "full.yaml")

    assert config.dataset == FIXTURES / "data/tasks.jsonl"
    assert config.configs[0].agent_config == FIXTURES / "agents/baseline.yaml"
    assert config.run.output == FIXTURES / "runs/experiment1"


def test_load_config_accepts_str_path():
    config = load_config(str(FIXTURES / "minimal.yaml"))

    assert config.dataset == FIXTURES / "data/tasks.jsonl"


# ----------- Invalid configs ----------- #


def test_empty_file_is_rejected():
    with pytest.raises(ValueError, match="expected a mapping at the top level"):
        load_config(FIXTURES / "empty.yaml")


def test_top_level_list_is_rejected():
    with pytest.raises(ValueError, match="expected a mapping at the top level"):
        load_config(FIXTURES / "top_level_list.yaml")


def test_unknown_key_is_rejected():
    with pytest.raises(ValueError, match="unknown config key: attempt"):
        load_config(FIXTURES / "unknown_key.yaml")


def test_prs_typo_is_rejected():
    with pytest.raises(ValueError, match="prs must be 'all' or a list of PR numbers"):
        load_config(FIXTURES / "prs_typo.yaml")


def test_prs_single_int_is_rejected():
    with pytest.raises(ValueError, match="prs must be 'all' or a list of PR numbers"):
        load_config(FIXTURES / "prs_single_int.yaml")


def test_prs_as_strings_is_rejected():
    with pytest.raises(ValueError, match="PR numbers must be integers"):
        load_config(FIXTURES / "prs_strings.yaml")


def test_missing_limits_is_rejected():
    with pytest.raises(KeyError, match="limits"):
        load_config(FIXTURES / "missing_limits.yaml")


def test_missing_agent_config_is_rejected():
    with pytest.raises(KeyError, match="agent_config"):
        load_config(FIXTURES / "missing_agent_config.yaml")


def test_missing_file_is_rejected():
    with pytest.raises(FileNotFoundError):
        load_config(FIXTURES / "does_not_exist.yaml")
