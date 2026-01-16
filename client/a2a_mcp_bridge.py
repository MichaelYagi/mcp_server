from typing import Any, Dict
from langchain_core.tools import Tool
from client.a2a_client import A2AClient


def make_a2a_tool(a2a_client: A2AClient, tool_def: Dict[str, Any]):
    """
    Create a LangChain Tool that forwards calls to a remote A2A agent.
    Matches the structure of MCPAgent-generated tools.
    """

    name = f"a2a_{tool_def['name']}"
    description = tool_def.get("description", f"A2A remote tool: {tool_def['name']}")

    async def _run(**kwargs):
        return await a2a_client.call(tool_def["name"], kwargs)

    # LangChain Tool wrapper
    tool = Tool(
        name=name,
        description=description,
        func=_run,        # async function is allowed
    )

    return tool
