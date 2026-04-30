"""Generic AgentExecutor that bridges the A2A protocol with any BaseA2AAgent.

Subclasses only need to implement _create_agent() — all A2A task-lifecycle
bookkeeping (status updates, artifact upload, completion) is handled here.

Compatible with a2a-sdk >= 1.0.0 (protobuf-based types).
"""

import logging
from abc import ABC, abstractmethod
from uuid import uuid4

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, Task, TaskState, TaskStatus
from a2a.utils.errors import (
    InternalError,
    InvalidParamsError,
    UnsupportedOperationError,
)

from src.a2a.base.agent_base import BaseA2AAgent

logger = logging.getLogger(__name__)


class BaseAgentExecutor(AgentExecutor, ABC):
    """Reusable A2A executor shell.

    Subclass checklist:
    - Implement _create_agent() to return your concrete BaseA2AAgent instance.
    - Optionally override _validate_request() for input validation.
    - Optionally override cancel() if your agent supports cancellation.
    """

    def __init__(self) -> None:
        self._agent: BaseA2AAgent | None = None

    @abstractmethod
    async def _create_agent(self) -> BaseA2AAgent:
        """Instantiate and return the concrete agent. Called once (lazy init)."""

    async def _get_agent(self) -> BaseA2AAgent:
        if self._agent is None:
            self._agent = await self._create_agent()
        return self._agent

    def _validate_request(self, context: RequestContext) -> bool:
        """Return True if the request is invalid (triggers InvalidParamsError)."""
        return False

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        if self._validate_request(context):
            raise InvalidParamsError()

        query = context.get_user_input()
        # task_id and context_id are always set by the framework before execute() is called.
        task_id: str = context.task_id
        context_id: str = context.context_id

        updater = TaskUpdater(event_queue, task_id, context_id)

        try:
            agent = await self._get_agent()
            # Enqueue the initial Task object so the consumer sets _task_created
            # before any TaskStatusUpdateEvent arrives (required by a2a-sdk >= 1.0.2).
            await event_queue.enqueue_event(
                Task(
                    id=task_id,
                    context_id=context_id,
                    status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
                )
            )
            # Signal to the client that we are actively processing (TASK_STATE_WORKING).
            await updater.start_work()
            completed = False
            # Stable artifact ID so token chunks append to the same artifact.
            artifact_id = uuid4().hex
            artifact_started = False

            async for chunk in agent.stream(query, context_id):
                is_complete = chunk["is_task_complete"]
                needs_input = chunk["require_user_input"]
                content = chunk["content"]
                is_token = chunk.get("is_streaming_token", False)

                if is_token and content:
                    # Stream each LLM token as an artifact chunk so the client
                    # receives it immediately via SSE and Chainlit calls stream_token().
                    await updater.add_artifact(
                        [Part(text=content)],
                        artifact_id=artifact_id,
                        name="result",
                        append=artifact_started,
                        last_chunk=False,
                    )
                    artifact_started = True

                elif not is_complete and not needs_input:
                    # Intermediate working update (tool call / tool result).
                    msg = updater.new_agent_message([Part(text=content)])
                    await updater.update_status(TaskState.TASK_STATE_WORKING, message=msg)

                elif needs_input:
                    msg = updater.new_agent_message([Part(text=content)])
                    await updater.update_status(
                        TaskState.TASK_STATE_INPUT_REQUIRED, message=msg
                    )
                    completed = True
                    break

                else:
                    # Final sentinel chunk — content is non-empty only for small-model
                    # fallback (tool result echoed when LLM emits no text tokens).
                    if content:
                        await updater.add_artifact(
                            [Part(text=content)],
                            artifact_id=artifact_id,
                            name="result",
                            append=artifact_started,
                            last_chunk=True,
                        )
                    await updater.complete()
                    completed = True
                    break

            if not completed:
                logger.warning("Agent stream exhausted without a terminal chunk.")
                await updater.complete()

        except (InvalidParamsError, UnsupportedOperationError, InternalError):
            raise
        except Exception as exc:
            logger.error("Agent execution error: %s", exc, exc_info=True)
            raise InternalError() from exc

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        raise UnsupportedOperationError()
