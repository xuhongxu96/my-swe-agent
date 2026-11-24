"""Glue between an issue, a task config (condition) and a bare mini-swe-agent run."""

import json
import logging
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from minisweagent.agents.default import DefaultAgent
from minisweagent.environments.local import LocalEnvironment

from mini.models import build_model
from mini.task_config import TaskConfig

SCHEMA_DIR = Path(__file__).parent.parent.parent / "tasks/schemas"


def load_issue(path: str | Path, task: str = "missed_opt") -> dict:
    """Read an issue JSON and validate it against the task's input schema."""
    schema = json.loads((SCHEMA_DIR / task / "input.schema.json").read_text())
    issue = json.loads(Path(path).read_text())
    if errors := sorted(
        Draft202012Validator(schema).iter_errors(issue), key=lambda e: list(e.path)
    ):
        msgs = "; ".join(
            f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors
        )
        raise ValueError(f"{path}: invalid issue: {msgs}")
    return issue


def build_task(issue: dict, task_config: TaskConfig | None = None) -> str:
    """Prompt text for the agent: the issue, then the condition's addendum."""
    parts = [f"# {issue['title']}", issue["description"]]
    if task_config and (addendum := task_config.render_addendum()):
        parts.append(addendum)
    return "\n\n".join(parts)


def run_agent(
    issue: dict, mini_config: dict, task_config: TaskConfig | None = None
) -> dict:
    """Run one agent on one issue and return a JSON-serializable result."""
    agent_config = dict(mini_config["agent"])
    if task_config:
        agent_config |= task_config.limits
    agent = DefaultAgent(
        build_model(mini_config["model"]), LocalEnvironment(), **agent_config
    )
    try:
        info = agent.run(build_task(issue, task_config))
    except Exception as e:  # agent already recorded an exit message; keep the run
        logging.getLogger(__name__).exception("agent crashed")
        info = {"exit_status": type(e).__name__, "submission": ""}
    return {
        "issue_id": issue["issue_id"],
        "config": task_config.name if task_config else None,
        "exit_status": info.get("exit_status"),
        "submission": info.get("submission", ""),
        "cost": agent.cost,
        "n_calls": agent.n_calls,
        "messages": agent.messages,
    }


def write_result(result: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, default=str))


def load_mini_config(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text())
