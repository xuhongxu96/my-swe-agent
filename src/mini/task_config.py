"""Load and validate a task config (one experimental condition)."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

_TOP_KEYS = {
    "name",
    "task",
    "num_runs",
    "prompt_addendum",
    "tools",
    "limits",
    "signals",
}
_REQUIRED = {"name", "task", "tools"}
_TOOL_KEYS = {"name", "doc", "timeout_s"}
_LIMIT_KEYS = {
    "step_limit",
    "cost_limit",
}


@dataclass(frozen=True)
class ToolSpec:
    name: str
    doc: str
    timeout_s: int = 60


@dataclass(frozen=True)
class TaskConfig:
    name: str
    task: str
    num_runs: int = 1
    prompt_addendum: str = ""
    tools: tuple[ToolSpec, ...] = ()
    limits: dict = field(default_factory=dict)
    signals: tuple = ()

    @property
    def tool_names(self) -> frozenset[str]:
        return frozenset(t.name for t in self.tools)

    def render_addendum(self) -> str:
        """Text appended to the prompt: the addendum plus one line per tool."""
        parts = [self.prompt_addendum.strip()]
        if self.tools:
            parts.append("Available domain tools:")
            parts += [f"- {t.name}: {t.doc}" for t in self.tools]
        return "\n".join(p for p in parts if p)


def load_task_config(path: str | Path) -> TaskConfig:
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    if unknown := raw.keys() - _TOP_KEYS:
        raise ValueError(f"{path}: unknown keys {sorted(unknown)}")
    if missing := _REQUIRED - raw.keys():
        raise ValueError(f"{path}: missing keys {sorted(missing)}")

    num_runs = raw.get("num_runs", 1)
    if not isinstance(num_runs, int) or isinstance(num_runs, bool) or num_runs < 1:
        raise ValueError(f"{path}: num_runs must be an integer >= 1")

    tools = []
    for t in raw["tools"] or []:
        if not isinstance(t, dict) or not {"name", "doc"} <= t.keys():
            raise ValueError(f"{path}: each tool needs 'name' and 'doc'")
        if unknown := t.keys() - _TOOL_KEYS:
            raise ValueError(f"{path}: unknown tool keys {sorted(unknown)}")
        tools.append(ToolSpec(**t))
    if len({t.name for t in tools}) != len(tools):
        raise ValueError(f"{path}: duplicate tool names")

    limits = raw.get("limits") or {}
    if unknown := limits.keys() - _LIMIT_KEYS:
        raise ValueError(f"{path}: unknown limits {sorted(unknown)}")

    return TaskConfig(
        name=raw["name"],
        task=raw["task"],
        num_runs=num_runs,
        prompt_addendum=raw.get("prompt_addendum", ""),
        tools=tuple(tools),
        limits=dict(limits),
        signals=tuple(raw.get("signals") or ()),
    )
