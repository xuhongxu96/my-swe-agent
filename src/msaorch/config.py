from dataclasses import dataclass
from pathlib import Path

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
    prs: list[int] | None = None  # None is for the case where we want all prs
    attempts: int = 1
    verbose: bool = False
