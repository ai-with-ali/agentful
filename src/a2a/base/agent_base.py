"""Abstract base class that every A2A-wrapped LangGraph agent must implement."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from src.a2a.base.response_format import AgentStreamChunk


class BaseA2AAgent(ABC):
    """Template for all A2A-compatible agents.

    To add a new agent:
    1. Subclass BaseA2AAgent.
    2. Override SUPPORTED_CONTENT_TYPES if needed.
    3. Implement stream() as an async generator that yields AgentStreamChunk dicts.
       The final chunk must have is_task_complete=True or require_user_input=True.
    """

    SUPPORTED_CONTENT_TYPES: list[str] = ["text/plain"]

    @abstractmethod
    async def stream(
        self, query: str, context_id: str
    ) -> AsyncIterator[AgentStreamChunk]:
        """Yield AgentStreamChunk events for the given query.

        Implement this method as an async generator (use ``yield``).
        Intermediate tool-call updates should be yielded with
        ``is_task_complete=False, require_user_input=False``.
        The final answer must be yielded with ``is_task_complete=True``.
        """
