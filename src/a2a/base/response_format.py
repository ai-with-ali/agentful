"""Shared response types for all A2A agents in this project."""

from typing import Literal, TypedDict

from pydantic import BaseModel


class ResponseFormat(BaseModel):
    """Structured output format for agents that support it."""

    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str


class AgentStreamChunk(TypedDict):
    """A single event yielded by any BaseA2AAgent.stream() implementation.

    is_task_complete    – True only on the last chunk.
    require_user_input  – True when the agent needs clarification.
    content             – Human-readable text for this chunk.
    is_streaming_token  – True for partial LLM tokens (stream as artifact chunks).
    """

    is_task_complete: bool
    require_user_input: bool
    content: str
    is_streaming_token: bool
