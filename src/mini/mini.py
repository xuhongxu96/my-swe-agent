"""This is the simplest possible example of how to use mini-SWE-agent with python bindings.
For a more complete example, see mini.py
"""

import logging
import os
from pathlib import Path

import typer
import yaml

from minisweagent import package_dir
from minisweagent.agents.default import DefaultAgent
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models.litellm_model import LitellmModel

app = typer.Typer()


@app.command()
def main(
    task: str = typer.Option(..., "-t", "--task", help="Task/problem statement", show_default=False, prompt=True),
    config_path: str = typer.Option(..., "-c", "--config", help="Config file path", show_default=False, prompt=True),
) -> DefaultAgent:
    logging.basicConfig(level=logging.DEBUG)
    config = yaml.safe_load(Path(config_path).read_text())
    agent = DefaultAgent(
        LitellmModel(**config["model"]),
        LocalEnvironment(),
        **config["agent"],
    )
    agent.run(task)
    return agent


if __name__ == "__main__":
    app()
