import json
from pathlib import Path

import pytest

import mini.runner as runner
from mini.task_config import load_task_config

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "tasks/schemas/missed_opt/configs"
EXAMPLE = ROOT / "tasks/schemas/missed_opt/example_input.json"


class FakeAgent:
    last = None

    def __init__(self, model, env, **kwargs):
        self.kwargs = kwargs
        self.task = None
        self.cost = 0.5
        self.n_calls = 3
        self.messages = [{"role": "exit"}]
        FakeAgent.last = self

    def run(self, task):
        self.task = task
        return {"exit_status": "Submitted", "submission": "ret i32 %x"}


@pytest.fixture
def fake_agent(monkeypatch):
    monkeypatch.setattr(runner, "DefaultAgent", FakeAgent)
    monkeypatch.setattr(runner, "build_model", lambda cfg: object())


MINI = {"model": {"model_name": "x"}, "agent": {"step_limit": 100, "cost_limit": 5.0}}


def test_load_issue_example():
    assert runner.load_issue(EXAMPLE)["issue_id"] == "missed_opt-0001"


@pytest.mark.parametrize(
    "issue",
    [
        {"title": "t", "description": "d"},
        {"issue_id": "a", "title": "t", "description": "d", "extra": 1},
    ],
)
def test_load_issue_rejects_invalid(tmp_path, issue):
    p = tmp_path / "i.json"
    p.write_text(json.dumps(issue))
    with pytest.raises(ValueError, match="invalid issue"):
        runner.load_issue(p)


def test_build_task_with_and_without_config():
    issue = runner.load_issue(EXAMPLE)
    tc = load_task_config(CONFIG_DIR / "alive2_mca.yaml")
    plain = runner.build_task(issue)
    assert plain.startswith("# [example] Missed fold") and "alive-tv" not in plain
    full = runner.build_task(issue, tc)
    assert full.startswith(plain) and "- llvm-mca:" in full


def test_run_agent_applies_limits_and_shapes_result(fake_agent):
    issue = runner.load_issue(EXAMPLE)
    tc = load_task_config(CONFIG_DIR / "alive2.yaml")
    result = runner.run_agent(issue, MINI, tc)
    assert FakeAgent.last.kwargs == {"step_limit": 50, "cost_limit": 2.0}
    assert result == {
        "issue_id": "missed_opt-0001",
        "config": "alive2",
        "exit_status": "Submitted",
        "submission": "ret i32 %x",
        "cost": 0.5,
        "n_calls": 3,
        "messages": [{"role": "exit"}],
    }


def test_run_agent_without_task_config(fake_agent):
    result = runner.run_agent(runner.load_issue(EXAMPLE), MINI)
    assert FakeAgent.last.kwargs == {"step_limit": 100, "cost_limit": 5.0}
    assert result["config"] is None


def test_write_result_creates_parent(tmp_path):
    out = tmp_path / "a/b/r.json"
    runner.write_result({"x": 1}, out)
    assert json.loads(out.read_text()) == {"x": 1}
