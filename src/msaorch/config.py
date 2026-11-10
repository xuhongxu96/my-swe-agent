from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


# ----------- Dataclass Definitions ----------- #
@dataclass
class Limits:
    step_limit: int
    cost_limit_usd: float
    wall_time_min: int


@dataclass
class AgentSpec:
    name: str
    agent_config: Path  # path to the mini-swe-agent yaml config


@dataclass
class RunSettings:
    output: Path
    workers: int = 1


@dataclass
class ScoreSettings:
    use: list[str]


@dataclass
class HarnessConfig:
    dataset: Path
    limits: Limits
    configs: list[AgentSpec]
    run: RunSettings
    score: ScoreSettings
    prs: list[int] | None = None  # None means all PRs
    attempts: int = 1
    verbose: bool = False


# ----------- Parser ----------- #

ALLOWED_KEYS = [
    "dataset",
    "prs",
    "attempts",
    "verbose",
    "limits",
    "configs",
    "run",
    "score",
]


def load_config(path: str | Path) -> HarnessConfig:
    path = Path(path)

    with open(path, encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")

    return parse_config(data, config_dir=path.parent)


def parse_config(data: dict[str, Any], config_dir: Path) -> HarnessConfig:
    # all relative paths in the config are resolved against the config file's folder
    for key in data:
        if key not in ALLOWED_KEYS:
            raise ValueError(f"unknown config key: {key}")

    limits_data = data["limits"]
    limits = Limits(
        step_limit=limits_data["step_limit"],
        cost_limit_usd=limits_data["cost_limit_usd"],
        wall_time_min=limits_data["wall_time_min"],
    )

    configs = []
    for spec_data in data["configs"]:
        configs.append(
            AgentSpec(
                name=spec_data["name"],
                agent_config=config_dir / spec_data["agent_config"],
            )
        )

    run_data = data["run"]
    run = RunSettings(
        output=config_dir / run_data["output"],
        workers=run_data.get("workers", 1),
    )

    score = ScoreSettings(use=data["score"]["use"])

    return HarnessConfig(
        dataset=config_dir / data["dataset"],
        limits=limits,
        configs=configs,
        run=run,
        score=score,
        prs=_parse_prs(data.get("prs")),
        attempts=data.get("attempts", 1),
        verbose=data.get("verbose", False),
    )


def _parse_prs(value: Any) -> list[int] | None:
    if value is None or value == "all":
        return None
    if not isinstance(value, list):
        raise ValueError(f"prs must be 'all' or a list of PR numbers, got {value!r}")
    for pr in value:
        if not isinstance(pr, int):
            raise ValueError(f"PR numbers must be integers, got {pr!r}")
    return value
