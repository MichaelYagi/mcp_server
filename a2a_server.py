"""
A2A Server Module (Lifespan Version) - FIXED
------------------------------------
Exposes your MCP tools over the A2A protocol using FastAPI's modern lifespan API.
"""

import asyncio
import os
from urllib.parse import urljoin
from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from mcp_use.client.client import MCPClient

A2A_ENDPOINT = os.getenv("A2A_ENDPOINT", "").strip()

# -----------------------------
# A2A RPC Request Schema
# -----------------------------
class RPCRequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: dict


# -----------------------------
# FastAPI Lifespan Manager
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting MCP session…")

    client = MCPClient.from_dict({
        "mcpServers": {
            "local": {
                "command": "python",
                "args": ["server.py"],
                "cwd": "."
            }
        }
    })

    # Create MCP session before serving traffic
    session = await client.create_session("local")
    app.state.session = session

    print("✅ MCP session ready")
    yield

    # Cleanup on shutdown
    print("🛑 Shutting down MCP sessions…")
    await client.close_all_sessions()


# -----------------------------
# FastAPI App
# -----------------------------
app = FastAPI(lifespan=lifespan)


# -----------------------------
# A2A RPC Handler
# -----------------------------
@app.get("/.well-known/agent.json")
async def agent_card():
    # If A2A_ENDPOINT is the card URL, derive the RPC URL
    rpc_url = None
    if A2A_ENDPOINT:
        # Replace the card path with /a2a
        base = A2A_ENDPOINT.rsplit("/", 2)[0]  # http://localhost:8010/.well-known
        rpc_url = urljoin(base + "/", "a2a")

    card = {
        "name": "Local A2A Agent",
        "description": "Your MCP tools exposed over A2A",
        "version": "1.0.0",
        "capabilities": {"streaming": False},
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
        "skills": [],
    }

    if rpc_url:
        card["endpoints"] = {"a2a": rpc_url}

    return card

@app.post("/a2a")
async def a2a_handler(req: RPCRequest, request: Request):
    session = request.app.state.session

    if req.method == "a2a.discover":
        tools = await session.list_tools()

        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "schema": (
                            t.args_schema.schema()
                            if hasattr(t, "args_schema") and t.args_schema
                            else {"type": "object"}
                        )
                    }
                    for t in tools
                ]
            }
        }

    if req.method == "a2a.call":
        tool_name = req.params["tool"]
        args = req.params["arguments"]

        # Find the tool object (for validation)
        tools = await session.list_tools()
        tool = next((t for t in tools if t.name == tool_name), None)

        if tool is None:
            return {
                "jsonrpc": "2.0",
                "id": req.id,
                "error": f"Tool not found: {tool_name}"
            }

        # Call the tool using the session's call_tool method
        try:
            # session.call_tool returns a list of content items
            result = await session.call_tool(tool_name, args)

            # Result is typically a list of TextContent objects
            # Extract the text from the result
            if isinstance(result, list) and len(result) > 0:
                if hasattr(result[0], 'text'):
                    result_text = result[0].text
                else:
                    result_text = str(result[0])
            else:
                result_text = str(result)

            return {
                "jsonrpc": "2.0",
                "id": req.id,
                "result": result_text
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "jsonrpc": "2.0",
                "id": req.id,
                "error": f"Tool execution failed: {str(e)}"
            }

    return {
        "jsonrpc": "2.0",
        "id": req.id,
        "error": f"Unknown method: {req.method}"
    }

# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)