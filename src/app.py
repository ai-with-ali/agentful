import traceback
import uuid
from pathlib import Path

import chainlit as cl

from src.a2a.orchestrator.client import A2AAgentClient
from src.a2a.orchestrator.registry import AgentRegistry

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "agents.yaml"

_WELCOME_MESSAGE = """\
### Running the Agent Locally in your machine for free!

I can help you perform numerical analyses using a set of specialised tools.

**Try asking:**
- *"What is 42 multiplied by 7?"*
- *"Add 123.45 and 678.9 together."*
- *"Can you summarise this dataset: [1, 2, 3, 4, 5]?"*

Type your question below to get started.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Session lifecycle
# ──────────────────────────────────────────────────────────────────────────────


@cl.on_chat_start
async def on_chat_start() -> None:
    """Discover available A2A agents and initialise a conversation context."""
    registry = AgentRegistry(config_path=_CONFIG_PATH)
    await registry.discover()

    cl.user_session.set("registry", registry)
    cl.user_session.set("thread_id", str(uuid.uuid4()))

    await cl.Message(
        content=_WELCOME_MESSAGE,
        author="Agent Orchestrator",
    ).send()


# ──────────────────────────────────────────────────────────────────────────────
# Message handling
# ──────────────────────────────────────────────────────────────────────────────


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Route the user message to the best-matching A2A agent and stream the reply.

    Flow:
    1. AgentRegistry.find_agent() selects an agent by skill-tag matching.
    2. A2AAgentClient.send_streaming() sends the message via A2A JSON-RPC/SSE.
    3. Intermediate "working" events are surfaced as collapsible Chainlit Steps.
    4. The final answer is streamed token-by-token into the reply message.
    """
    registry: AgentRegistry = cl.user_session.get("registry")
    thread_id: str = cl.user_session.get("thread_id")

    agent_card = registry.find_agent(message.content)
    if not agent_card:
        await cl.Message(
            content=(
                "No agent is currently available. "
                "Please start an agent server and reload."
            ),
            author="System",
        ).send()
        return

    a2a_client = A2AAgentClient()
    final_answer = cl.Message(content="", author=agent_card.name)

    try:
        async with cl.Step(
            name=f"{agent_card.name} — processing", type="tool"
        ) as work_step:
            async for event in a2a_client.send_streaming(
                agent_card, message.content, thread_id
            ):
                event_type = event["type"]
                content = event["content"]

                if event_type == "working" and content:
                    # Append each working event so all steps remain visible.
                    if work_step.output:
                        work_step.output += "\n\n" + content
                    else:
                        work_step.output = content
                    await work_step.update()
                elif event_type in ("final", "input_required") and content:
                    await final_answer.stream_token(content)

    except Exception:  # noqa: BLE001
        error_detail = traceback.format_exc()
        await cl.Message(
            content=(
                "An error occurred while processing your request.\n\n"
                f"```\n{error_detail}\n```"
            ),
            author="System",
        ).send()
        return

    await final_answer.send()
