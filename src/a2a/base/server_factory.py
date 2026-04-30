"""Factory that wires up a complete A2A Starlette ASGI application.

Usage:
    app = build_a2a_app(agent_card, MyAgentExecutor())
    uvicorn.run(app, host="localhost", port=10001)

Compatible with a2a-sdk >= 1.0.0 (protobuf-based types).
"""

import httpx
from starlette.applications import Starlette

from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandlerV2
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from a2a.types import AgentCard


def build_a2a_app(agent_card: AgentCard, executor: AgentExecutor) -> Starlette:
    """Build and return an ASGI Starlette app for the given agent card and executor.

    Wires together:
    - InMemoryTaskStore                     – tracks task lifecycle
    - InMemoryPushNotificationConfigStore   – push notification config
    - BasePushNotificationSender            – sends push notifications
    - DefaultRequestHandlerV2              – routes A2A REST calls to the executor
    - Starlette                             – exposes /.well-known/agent-card.json + REST routes
    """
    httpx_client = httpx.AsyncClient()
    push_config_store = InMemoryPushNotificationConfigStore()
    push_sender = BasePushNotificationSender(
        httpx_client=httpx_client,
        config_store=push_config_store,
    )
    handler = DefaultRequestHandlerV2(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
        push_config_store=push_config_store,
        push_sender=push_sender,
    )
    routes = (
        create_agent_card_routes(agent_card=agent_card)
        + create_jsonrpc_routes(request_handler=handler, rpc_url="/")
    )
    return Starlette(routes=routes)
