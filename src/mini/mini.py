"""CLI: run bare mini-swe-agent on one issue under one task config."""

import logging

import typer

from mini.runner import (
    load_issue,
    load_mini_config,
    run_agent,
    write_result,
)
from mini.task_config import load_task_config

app = typer.Typer()


@app.command()
def main(
    input_path: str = typer.Option(..., "-i", "--input", help="Issue JSON file"),
    config_path: str = typer.Option(
        ..., "-c", "--config", help="mini-swe-agent config file"
    ),
    output_path: str = typer.Option(..., "-o", "--output", help="Result JSON path"),
    task_config_path: str | None = typer.Option(
        None, "--task-config", help="Task config (experimental condition)"
    ),
) -> None:
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("LiteLLM").setLevel(
        logging.WARNING
    )  # its DEBUG logs print api_key in plain text

    task_config = load_task_config(task_config_path) if task_config_path else None
    issue = load_issue(input_path, task_config.task if task_config else "missed_opt")
    result = run_agent(issue, load_mini_config(config_path), task_config)
    write_result(result, output_path)


if __name__ == "__main__":
    app()
