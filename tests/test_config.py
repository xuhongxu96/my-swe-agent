from pathlib import Path

import pytest

import mini.mini as mini_cli
from mini.task_config import TaskConfig, ToolSpec, load_task_config

CONFIG_DIR = Path(__file__).parent.parent / "tasks/schemas/missed_opt/configs"

VALID = """\
name: demo
task: missed_opt
tools:
  - name: alive-tv
    doc: checks refinement
"""


def write(tmp_path, text):
    p = tmp_path / "tc.yaml"
    p.write_text(text)
    return p


# ----------- Valid configs ----------- #


@pytest.mark.parametrize("name", ["baseline", "alive2", "alive2_mca"])
def test_repo_configs_load(name):
    tc = load_task_config(CONFIG_DIR / f"{name}.yaml")
    assert tc.name == name
    assert tc.task == "missed_opt"


def test_tool_access_differs_by_condition():
    names = {
        n: load_task_config(CONFIG_DIR / f"{n}.yaml").tool_names
        for n in ("baseline", "alive2", "alive2_mca")
    }
    assert names["baseline"] == frozenset()
    assert names["alive2"] == {"alive-tv"}
    assert names["alive2_mca"] == {"alive-tv", "llvm-mca"}


def test_defaults(tmp_path):
    tc = load_task_config(write(tmp_path, VALID))
    assert tc == TaskConfig(
        name="demo",
        task="missed_opt",
        num_runs=1,
        tools=(ToolSpec(name="alive-tv", doc="checks refinement"),),
    )


def test_render_addendum(tmp_path):
    tc = load_task_config(write(tmp_path, VALID + "prompt_addendum: Be careful.\n"))
    assert tc.render_addendum() == (
        "Be careful.\nAvailable domain tools:\n- alive-tv: checks refinement"
    )


def test_render_addendum_without_tools(tmp_path):
    text = "name: b\ntask: t\ntools: []\nprompt_addendum: Shell only.\n"
    assert load_task_config(write(tmp_path, text)).render_addendum() == "Shell only."


# ----------- Invalid configs ----------- #


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("- a\n- b\n", "top level"),
        (VALID + "extra: 1\n", "unknown keys"),
        ("name: x\ntask: t\n", "missing keys"),
        (VALID + "num_runs: 0\n", "num_runs"),
        (VALID + "num_runs: '3'\n", "num_runs"),
        (VALID + "num_runs: true\n", "num_runs"),
        ("name: x\ntask: t\ntools:\n  - name: a\n", "'name' and 'doc'"),
        ("name: x\ntask: t\ntools:\n  - {name: a, doc: d, flag: 1}\n", "tool keys"),
        (
            "name: x\ntask: t\ntools:\n  - {name: a, doc: d}\n  - {name: a, doc: e}\n",
            "duplicate",
        ),
        (VALID + "limits:\n  wall_time_min: 5\n", "unknown limits"),
    ],
)
def test_invalid_configs(tmp_path, text, match):
    with pytest.raises(ValueError, match=match):
        load_task_config(write(tmp_path, text))


# ----------- CLI wiring ----------- #


class FakeAgent:
    def __init__(self, model, env, **kwargs):
        self.kwargs = kwargs
        self.task = None

    def run(self, task):
        self.task = task


def run_main(monkeypatch, tmp_path, task_config_path):
    monkeypatch.setattr(mini_cli, "DefaultAgent", FakeAgent)
    monkeypatch.setattr(mini_cli, "LitellmModel", lambda **kw: object())
    base = tmp_path / "mini.yaml"
    base.write_text(
        "model: {model_name: x}\nagent: {step_limit: 100, cost_limit: 5.0}\n"
    )
    return mini_cli.main(
        task="fix it", config_path=str(base), task_config_path=task_config_path
    )


def test_main_applies_task_config(monkeypatch, tmp_path):
    agent = run_main(monkeypatch, tmp_path, str(CONFIG_DIR / "alive2_mca.yaml"))
    assert agent.kwargs == {"step_limit": 50, "cost_limit": 2.0}
    assert agent.task.startswith("fix it\n\n")
    assert "- alive-tv:" in agent.task
    assert "- llvm-mca:" in agent.task


def test_main_without_task_config_is_unchanged(monkeypatch, tmp_path):
    agent = run_main(monkeypatch, tmp_path, None)
    assert agent.kwargs == {"step_limit": 100, "cost_limit": 5.0}
    assert agent.task == "fix it"
