"""Entry point for the Data Analysis A2A agent server.

Run with:
    python -m src.a2a.agents.da_agent
    python -m src.a2a.agents.da_agent --host 0.0.0.0 --port 10001
"""

import logging
import sys

import click
import uvicorn

from src.a2a.agents.da_agent.card import make_agent_card
from src.a2a.agents.da_agent.executor import DataAnalysisAgentExecutor
from src.a2a.base.server_factory import build_a2a_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", default="localhost", show_default=True, help="Bind host.")
@click.option("--port", default=10001, show_default=True, help="Bind port.")
def main(host: str, port: int) -> None:
    """Start the Data Analysis A2A agent server."""
    try:
        agent_card = make_agent_card(host, port)
        app = build_a2a_app(agent_card, DataAnalysisAgentExecutor())
        logger.info("Starting Data Analysis Agent at http://%s:%d/", host, port)
        logger.info("Agent Card available at http://%s:%d/.well-known/agent-card.json", host, port)
        uvicorn.run(app, host=host, port=port)
    except Exception as exc:
        logger.error("Failed to start server: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
