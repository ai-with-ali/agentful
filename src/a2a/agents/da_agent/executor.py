"""DataAnalysisAgentExecutor — thin A2A executor for the DA agent.

All A2A protocol bookkeeping lives in BaseAgentExecutor. This class only
specifies *which* agent to instantiate.
"""

from src.a2a.agents.da_agent.adapter import DataAnalysisA2AAgent
from src.a2a.base.agent_base import BaseA2AAgent
from src.a2a.base.executor_base import BaseAgentExecutor
from src.agents.da_agent.graph import create_data_analysis_agent


class DataAnalysisAgentExecutor(BaseAgentExecutor):
    """Executor for the Data Analysis LangGraph agent."""

    async def _create_agent(self) -> BaseA2AAgent:
        graph = await create_data_analysis_agent()
        return DataAnalysisA2AAgent(graph)
