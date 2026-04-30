"""Agent Card definition for the Data Analysis A2A agent.

The card is the agent's "business card" — it tells any A2A client what the
agent can do, where to reach it, and which skills it exposes.

The URL is assembled at runtime from the CLI --host / --port options so the
same code works in dev (localhost) and prod (remote host) without changes.

Compatible with a2a-sdk >= 1.0.0 (protobuf-based AgentCard).
"""

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from src.a2a.agents.da_agent.adapter import DataAnalysisA2AAgent

AGENT_SKILL = AgentSkill(
    id="data_analysis",
    name="Data Analysis Tool",
    description=(
        "Performs numerical analysis and statistical computations on datasets. "
        "Handles arithmetic operations, aggregations, and dataset summaries "
        "using a suite of specialised MCP tools."
    ),
    tags=[
        "math",
        "statistics",
        "dataset",
        "analysis",
        "arithmetic",
        "calculate",
        "sum",
        "average",
        "multiply",
        "divide",
    ],
    examples=[
        "What is 42 multiplied by 7?",
        "Add 123.45 and 678.9 together.",
        "Can you summarise this dataset: [1, 2, 3, 4, 5]?",
    ],
)


def make_agent_card(host: str, port: int) -> AgentCard:
    """Build an AgentCard for the given host and port.

    In a2a-sdk v1.0.0+ the agent URL lives inside supported_interfaces,
    not as a top-level field on AgentCard.
    """
    return AgentCard(
        name="Data Analysis Agent",
        description=(
            "Performs numerical analyses and statistical computations "
            "using specialised MCP tools. Powered by a local Ollama LLM."
        ),
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url=f"http://{host}:{port}/",
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        default_input_modes=DataAnalysisA2AAgent.SUPPORTED_CONTENT_TYPES,
        default_output_modes=DataAnalysisA2AAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=AgentCapabilities(streaming=True, push_notifications=True),
        skills=[AGENT_SKILL],
    )
