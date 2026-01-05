import asyncio
import os
import logging
import requests
import operator
import json
import websockets
import webbrowser

from typing import TypedDict, Annotated, Sequence
from mcp_use.client.client import MCPClient
from mcp_use.agents.mcpagent import MCPAgent
from pathlib import Path
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# Load environment variables from .env file
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

SYSTEM_PROMPT = """You are a helpful assistant with access to tools.
    When you call a tool and receive a result, use that result to answer the user's question.
    Do not call the same tool repeatedly with the same parameters.
    Provide clear, concise answers based on the tool results."""

# ============================================================================
# LangGraph State Definition
# ============================================================================

class AgentState(TypedDict):
    """State that gets passed between nodes in the graph"""
    messages: Annotated[Sequence[BaseMessage], operator.add]


# ============================================================================
# Stop Condition Function - THIS PREVENTS INFINITE LOOPS
# ============================================================================

def should_continue(state: AgentState) -> str:
    """
    Determines whether to continue with tool execution or end.

    Returns:
        "continue" if there are tool calls to execute
        "end" if the agent has finished and should return the final answer
    """
    messages = state["messages"]
    last_message = messages[-1]

    # If it's an AI message with tool calls, continue to execute them
    if isinstance(last_message, AIMessage):
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            logging.getLogger("mcp_use").info(
                f"🔄 Continuing - found {len(last_message.tool_calls)} tool call(s)"
            )
            return "continue"

    # Otherwise, we're done
    logging.getLogger("mcp_use").info("✅ Stopping - no more tool calls, returning final answer")
    return "end"


# ============================================================================
# Agent Graph Builder
# ============================================================================

def create_langgraph_agent(llm_with_tools, tools):
    """
    Creates a LangGraph agent with proper stop conditions.

    Args:
        llm_with_tools: LLM with tools bound to it
        tools: List of LangChain tools

    Returns:
        Compiled graph ready to execute
    """
    logger = logging.getLogger("mcp_use")

    # Define the agent node
    async def call_model(state: AgentState):
        """Node that calls the LLM"""
        messages = state["messages"]
        logger.info(f"🧠 Calling LLM with {len(messages)} messages")
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    # Build the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges - THIS IS THE CRITICAL PART THAT PREVENTS INFINITE LOOPS
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "tools",  # If there are tool calls, execute them
            "end": END  # If no tool calls, stop and return answer
        }
    )

    # After tools execute, always go back to agent to process results
    workflow.add_edge("tools", "agent")

    # Compile
    app = workflow.compile()
    logger.info("✅ LangGraph agent compiled successfully")

    return app


# ============================================================================
# Helper Functions
# ============================================================================

def get_public_ip():
    try:
        return requests.get("https://api.ipify.org").text
    except:
        return None


def get_venv_python(project_root: Path) -> str:
    """Return the correct Python executable path by checking known locations."""
    candidates = [
        project_root / ".venv" / "bin" / "python",  # WSL/Linux/macOS
        project_root / ".venv-wsl" / "bin" / "python",  # Legacy WSL
        project_root / ".venv" / "Scripts" / "python.exe",  # Windows
        project_root / ".venv" / "Scripts" / "python",  # Windows alt
    ]

    for path in candidates:
        if path.exists():
            return str(path)

    raise FileNotFoundError("No valid Python executable found in expected venv locations.")


# ============================================================================
# Main Function
# ============================================================================

GLOBAL_CONVERSATION_STATE = {"messages": []}

async def websocket_handler(websocket, agent, system_prompt):
    conversation_state = GLOBAL_CONVERSATION_STATE
    MAX_HISTORY = 20

    async for raw in websocket:

        # 1. Ignore empty or whitespace-only messages
        if not raw or not raw.strip():
            continue

        # 2. Try to parse JSON; if not JSON, treat as plain user text
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"type": "user", "text": raw}

        # 3. Browser requests history sync
        if data.get("type") == "history_request":
            history_payload = [
                {"role": "user", "text": m.content} if isinstance(m, HumanMessage)
                else {"role": "assistant", "text": m.content}
                for m in conversation_state["messages"]
            ]

            await websocket.send(json.dumps({
                "type": "history_sync",
                "history": history_payload
            }))
            continue

        # 4. Normal user message
        if data.get("type") == "user" or "text" in data:
            prompt = data.get("text")

            # Add user message
            conversation_state["messages"].append(
                HumanMessage(content=prompt)
            )

            # Trim history
            conversation_state["messages"] = [
                m for m in conversation_state["messages"]
                if isinstance(m, (HumanMessage, AIMessage))
            ][-MAX_HISTORY:]

            # Run agent
            result = await agent.ainvoke(
                conversation_state,
                config={"recursion_limit": 50}
            )

            final_message = result["messages"][-1]

            # Add assistant message
            conversation_state["messages"].append(final_message)

            # PRINT TO BACKEND CLI (same as CLI mode)
            print("\n" + final_message.content + "\n")

            # Send response
            await websocket.send(json.dumps({
                "type": "assistant_message",
                "text": final_message.content
            }))

async def start_websocket_server(agent, system_prompt):
    async with websockets.serve(
        lambda ws: websocket_handler(ws, agent, system_prompt),
        "localhost",
        8765
    ):
        print("🌐 Browser UI available at ws://localhost:8765")
        await asyncio.Future()  # run forever

async def cli_loop(agent, system_prompt, logger):
    print("\n✅ MCP Agent ready with LangGraph. Type a prompt (Ctrl+C to exit).\n")

    # Persistent conversation state
    conversation_state = {"messages": []}

    # How many messages to keep (user + assistant only)
    MAX_HISTORY = 20

    while True:
        try:
            query = input("> ").strip()
            if not query:
                continue

            logger.info(f"💬 Received query: '{query}'")

            # Add user message to history
            conversation_state["messages"].append(
                HumanMessage(content=query)
            )

            # Trim history (keep only last N user/assistant messages)
            conversation_state["messages"] = [
                m for m in conversation_state["messages"]
                if isinstance(m, (HumanMessage, AIMessage))
            ][-MAX_HISTORY:]

            # Run the agent with full (trimmed) history
            logger.info("🏁 Starting agent execution")
            result = await agent.ainvoke(
                conversation_state,
                config={"recursion_limit": 50}
            )

            # Extract final answer
            final_message = result["messages"][-1]

            # Add assistant message to history
            conversation_state["messages"].append(final_message)

            # Print answer
            if isinstance(final_message, AIMessage):
                answer = final_message.content
            else:
                answer = str(final_message)

            print("\n" + answer + "\n")
            logger.info("✅ Query completed successfully")

        except KeyboardInterrupt:
            print("\n👋 Exiting.")
            break

        except Exception as e:
            logger.error(f"❌ Error during agent execution: {e}", exc_info=True)
            print(f"\n❌ Error: {e}\n")

def open_browser_file(path: Path):
    import platform
    import subprocess
    import webbrowser

    # Detect WSL
    if "microsoft" in platform.uname().release.lower():
        # Use Windows default browser via cmd.exe
        windows_path = str(path).replace("/mnt/c", "C:").replace("/", "\\")
        subprocess.run(["cmd.exe", "/c", "start", windows_path], shell=False)
    else:
        # Normal behavior on macOS/Linux/Windows native
        webbrowser.open(f"file://{path}")

async def main():
    load_dotenv()

    PROJECT_ROOT = Path(__file__).resolve().parent
    LOG_DIR = Path(str(PROJECT_ROOT / "logs"))
    LOG_DIR.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / "mcp-client.log", encoding="utf-8"),
            logging.StreamHandler()
        ],
    )

    # Show the actual JSON payloads being sent to/from Ollama
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("langchain").setLevel(logging.DEBUG)

    # If you want to see exactly what the MCP Server is saying to the Client
    logging.getLogger("mcp").setLevel(logging.DEBUG)

    logger = logging.getLogger("mcp_use")

    # 2️⃣ MCP Server config
    client = MCPClient.from_dict({
        "mcpServers": {
            "local": {
                "command": get_venv_python(PROJECT_ROOT),
                "args": [str(PROJECT_ROOT / "server.py")],
                "cwd": str(PROJECT_ROOT),
                "env": {
                    "CLIENT_IP": get_public_ip()
                }
            }
        }
    })

    # 3️⃣ Load system prompt
    SYSTEM_PROMPT_PATH = PROJECT_ROOT / "prompts/tool_usage_guide.md"
    logger.warning(f"⚠️  System prompt file not found, using default")

    if SYSTEM_PROMPT_PATH.exists():
        SYSTEM_PROMPT = SYSTEM_PROMPT_PATH.read_text()

    model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    logger.info(f"🤖 Using model: {model_name}")

    # 4️⃣ Initialize LLM
    llm = ChatOllama(
        model=model_name,
        temperature=0
    )

    # 5️⃣ Create MCPAgent to initialize and get tools
    mcp_agent = MCPAgent(
        llm=llm,
        client=client,
        max_steps=10,  # This won't be used, but needed for initialization
        system_prompt=SYSTEM_PROMPT
    )

    mcp_agent.debug = True
    await mcp_agent.initialize()

    # Get the tools from MCPAgent
    tools = mcp_agent._tools

    logger.info(f"🛠 Found {len(tools)} MCP tools:")
    for t in tools:
        logger.info(f"  - {t.name}: {t.description}")

    # 6️⃣ Bind tools to LLM
    llm_with_tools = llm.bind_tools(tools)

    # 7️⃣ Create LangGraph agent with stop conditions
    agent = create_langgraph_agent(llm_with_tools, tools)

    print("\nChoose interface:")
    print("1) Browser")
    print("2) CLI")
    choice = input("> ").strip()

    if choice == "1":
        print("🌐 Starting browser UI mode...")

        index_path = PROJECT_ROOT / "index.html"
        open_browser_file(index_path)

        await start_websocket_server(agent, SYSTEM_PROMPT)

    else:
        print("🖥️ Starting CLI mode...")
        await cli_loop(agent, SYSTEM_PROMPT, logger)

if __name__ == "__main__":
    asyncio.run(main())