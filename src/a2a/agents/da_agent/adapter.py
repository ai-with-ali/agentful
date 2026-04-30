"""DataAnalysisA2AAgent — wraps the existing LangGraph DA agent as a BaseA2AAgent.

The underlying graph (graph.py) is untouched; this adapter translates LangGraph's
stream events into the AgentStreamChunk protocol expected by BaseAgentExecutor.
"""

import logging
from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.a2a.base.agent_base import BaseA2AAgent
from src.a2a.base.response_format import AgentStreamChunk

logger = logging.getLogger(__name__)


def _coerce_content(content) -> str:
    """Normalise an AIMessage content value to a plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return str(content)


class DataAnalysisA2AAgent(BaseA2AAgent):
    """A2A-compatible wrapper around the compiled DataAnalysis LangGraph agent."""

    SUPPORTED_CONTENT_TYPES = ["text/plain"]

    def __init__(self, graph) -> None:
        # graph is the compiled LangGraph agent returned by create_data_analysis_agent()
        self._graph = graph

    async def stream(
        self, query: str, context_id: str
    ) -> AsyncIterator[AgentStreamChunk]:
        """Stream AgentStreamChunks using dual stream modes for token-level output.

        stream_mode=["updates", "messages"] yields:
          - ("messages", (AIMessageChunk, metadata)) — individual LLM tokens
          - ("updates",  {node: state_delta})        — completed node outputs

        Token streaming strategy:
          - "messages" from the model node, without tool_call_chunks → stream as tokens
          - "updates" AIMessage with tool_calls → emit "Calling tool: ..." working event
          - "updates" ToolMessage               → emit "Tool result: ..." working event
          - Final AIMessage in "updates"         → skipped (already streamed token-by-token)
        """
        inputs = {"messages": [HumanMessage(content=query)]}
        config = {"configurable": {"thread_id": context_id}}

        last_tool_result: str = ""
        streamed_tokens: bool = False

        async for mode, data in self._graph.astream(
            inputs, config, stream_mode=["updates", "messages"]
        ):
            if mode == "messages":
                msg_chunk, metadata = data
                # Only forward tokens from the LLM model node.
                if metadata.get("langgraph_node") != "model":
                    continue
                # Skip raw tool-call argument chunks (JSON fragments).
                if getattr(msg_chunk, "tool_call_chunks", None):
                    continue
                token = _coerce_content(getattr(msg_chunk, "content", ""))
                if token:
                    streamed_tokens = True
                    yield AgentStreamChunk(
                        is_task_complete=False,
                        require_user_input=False,
                        content=token,
                        is_streaming_token=True,
                    )

            elif mode == "updates":
                for _node, node_state in data.items():
                    messages = node_state.get("messages", [])
                    if not messages:
                        continue
                    for msg in messages:
                        if isinstance(msg, AIMessage) and msg.tool_calls:
                            call_descriptions = []
                            for tc in msg.tool_calls:
                                args_str = ", ".join(
                                    f"{k}={v!r}" for k, v in tc.get("args", {}).items()
                                )
                                call_descriptions.append(f"**{tc['name']}**({args_str})")
                            yield AgentStreamChunk(
                                is_task_complete=False,
                                require_user_input=False,
                                content="Calling tool: " + " · ".join(call_descriptions),
                                is_streaming_token=False,
                            )
                        elif isinstance(msg, ToolMessage):
                            last_tool_result = _coerce_content(msg.content)
                            logger.debug("Tool result: %s", last_tool_result)
                            yield AgentStreamChunk(
                                is_task_complete=False,
                                require_user_input=False,
                                content=f"Tool result: {last_tool_result}",
                                is_streaming_token=False,
                            )
                        # Final AIMessage skipped here — already streamed token-by-token
                        # via the "messages" mode above.

        # Small-model fallback: if the model emitted no text tokens after tool use,
        # surface the raw tool result as the answer.
        fallback = "" if streamed_tokens else last_tool_result
        yield AgentStreamChunk(
            is_task_complete=True,
            require_user_input=False,
            content=fallback,
            is_streaming_token=False,
        )
