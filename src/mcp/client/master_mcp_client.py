import os

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

mcp_client = MultiServerMCPClient(
    {
        "DataAnalysis": {
            "transport": "http",
            "url": f"http://{os.getenv('MCP_DataAnalysis_Host')}:{os.getenv('MCP_DataAnalysis_Port')}/mcp",
        },
    }
)

