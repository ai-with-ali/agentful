import traceback
import uuid

import chainlit as cl
from langchain_core.runnables.config import RunnableConfig
from langchain_core.messages import HumanMessage, ToolMessage

from src.agents.da_agent.graph import create_data_analysis_agent

# ──────────────────────────────────────────────────────────────────────────────
# Session lifecycle
# ──────────────────────────────────────────────────────────────────────────────

_WELCOME_MESSAGE = """\
### Running the Agent Locally in your machine for free!

I can help you perform numerical analyses using a set of specialised tools.

**Try asking:**
- *"What is 42 multiplied by 7?"*
- *"Add 123.45 and 678.9 together."*
- *"Can you summarise this dataset: [1, 2, 3, 4, 5]?"*

Type your question below to get started.
"""


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialise a fresh agent and thread_id for every new browser session."""
    # The MemorySaver checkpointer is embedded inside the agent,
    # so conversation history is automatically scoped to thread_id.
    agent = await create_data_analysis_agent()
    thread_id = str(uuid.uuid4())

    cl.user_session.set("agent", agent)
    cl.user_session.set("thread_id", thread_id)

    await cl.Message(
        content=_WELCOME_MESSAGE,
        author="Data Analysis Agent",
    ).send()


# ──────────────────────────────────────────────────────────────────────────────
# Message handling
# ──────────────────────────────────────────────────────────────────────────────


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Stream agent response with tool-call steps via LangchainCallbackHandler."""
    agent = cl.user_session.get("agent")
    thread_id = cl.user_session.get("thread_id")

    # cl.LangchainCallbackHandler automatically renders tool steps in the UI.
    cb = cl.LangchainCallbackHandler()
    run_config = RunnableConfig(
        callbacks=[cb],
        configurable={"thread_id": thread_id},
    )

    final_answer = cl.Message(content="", author="Data Analysis Agent")

    try:
        async for chunk, _metadata in agent.astream(
            {"messages": [HumanMessage(content=message.content)]},
            config=run_config,
            stream_mode="messages",
        ):
            # Skip human echoes and raw tool-result messages;
            # stream only LLM-generated text tokens.
            if isinstance(chunk, (HumanMessage, ToolMessage)):
                continue

            token = chunk.content
            if not token:
                continue

            # content can be a plain string or a list of content-part dicts
            if isinstance(token, list):
                token = "".join(
                    part.get("text", "")
                    for part in token
                    if isinstance(part, dict)
                )

            if token:
                await final_answer.stream_token(token)

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
