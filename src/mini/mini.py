"""This is the simplest possible example of how to use mini-SWE-agent
with python bindings.
"""

import logging
import os
import uuid
from pathlib import Path

import typer
import yaml
from dotenv import dotenv_values
from minisweagent.agents.default import DefaultAgent
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models.litellm_model import LitellmModel

app = typer.Typer()

USER_AGENT = "my-swe-agent/0.1.0"


class OpencodeGoModel(LitellmModel):
    """LitellmModel for the OpenCode Go subscription.

    OpenCode Go requires a client-specific User-Agent and a stable
    `x-opencode-session` ID per conversation. The API key is injected per
    request (not stored in config) so it never shows up in serialized
    trajectories, and it is read from .env without being exported to
    os.environ, so the agent's shell commands can't see it.
    """

    def __init__(self, *, api_key: str, **kwargs):
        super().__init__(**kwargs)
        self._api_key = api_key
        self._headers = {
            "User-Agent": USER_AGENT,
            "x-opencode-session": str(uuid.uuid4()),
        }

    def _query(self, messages, **kwargs):
        headers = (
            self._headers
            | self.config.model_kwargs.get("extra_headers", {})
            | kwargs.pop("extra_headers", {})
        )
        return super()._query(
            messages, api_key=self._api_key, extra_headers=headers, **kwargs
        )


def get_opencode_api_key() -> str:
    key = os.environ.get("OPENCODE_API_KEY") or dotenv_values().get("OPENCODE_API_KEY")
    if not key:
        raise RuntimeError("OPENCODE_API_KEY not found in environment or .env")
    return key


@app.command()
def main(
    task: str = typer.Option(
        ...,
        "-t",
        "--task",
        help="Task/problem statement",
        show_default=False,
        prompt=True,
    ),
    config_path: str = typer.Option(
        ..., "-c", "--config", help="Config file path", show_default=False, prompt=True
    ),
) -> DefaultAgent:
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("LiteLLM").setLevel(
        logging.WARNING
    )  # its DEBUG logs print api_key in plain text

    config = yaml.safe_load(Path(config_path).read_text())
    model_config = config["model"]

    if "opencode.ai" in model_config.get("model_kwargs", {}).get("api_base", ""):
        model = OpencodeGoModel(api_key=get_opencode_api_key(), **model_config)
    else:
        model = LitellmModel(**model_config)

    agent = DefaultAgent(
        model,
        LocalEnvironment(),
        **config["agent"],
    )
    agent.run(task)
    return agent


if __name__ == "__main__":
    app()
