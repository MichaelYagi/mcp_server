import asyncio
import os
import logging
import requests
import operator
import json
import websockets
import platform
import httpx
import threading
from queue import Queue

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

# How many messages to keep (user + assistant only)
MAX_MESSAGE_HISTORY = int(os.getenv("MAX_MESSAGE_HISTORY", "20"))

async def ensure_ollama_running(host: str = "http://127.0.0.1:11434"):
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            r = await client.get(f"{host}/api/tags")
            r.raise_for_status()
    except Exception as e:
        raise RuntimeError(
            f"Ollama server is not running or unreachable at {host}. "
            f"Start it with 'ollama serve'. Original error: {e}"
        )

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
            tool_calls = last_message.tool_calls
            logging.getLogger("mcp_use").info(f"🔄 Continuing - found {len(tool_calls)} tool call(s)")
            for call in tool_calls:
                logging.getLogger("mcp_use").info(f" ↳ Tool: {call['name']} Args: {call.get('args')}")
            return "continue"

    # Otherwise, we're done
    logging.getLogger("mcp_use").info("✅ Stopping - no more tool calls, returning final answer")
    return "end"


# ============================================================================
# Agent Graph Builder
# ============================================================================

MODEL_STATE_FILE = "last_model.txt"

import subprocess


def get_available_models():
    try:
        out = subprocess.check_output(["ollama", "list"], text=True)
        lines = out.strip().split("\n")

        # Skip header line
        models = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                models.append(parts[0])  # first column = model name

        return models

    except Exception as e:
        print(f"❌ Could not list models: {e}")
        return []


def load_last_model():
    if os.path.exists(MODEL_STATE_FILE):
        return open(MODEL_STATE_FILE).read().strip()
    return None


def save_last_model(model_name):
    with open(MODEL_STATE_FILE, "w") as f:
        f.write(model_name)


async def switch_model(model_name, tools, logger):
    available = get_available_models()

    if model_name not in available:
        print(f"❌ Model '{model_name}' is not installed.")
        print("📦 Available models:")
        for m in available:
            print(f" - {m}")
        print()
        return None  # signal failure

    logger.info(f"🔄 Switching model to: {model_name}")

    new_llm = ChatOllama(model=model_name, temperature=0)
    llm_with_tools = new_llm.bind_tools(tools)
    new_agent = create_langgraph_agent(llm_with_tools, tools)

    save_last_model(model_name)

    logger.info(f"✅ Model switched to {model_name}")
    return new_agent


def list_commands():
    print(":commands - List all available commands")
    print(":model - View the current active model")
    print(":model <model> - Use the model passed")
    print(":models - List available models")

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
    """Return the correct Python executable path for the project's virtual environment."""

    venv = project_root / ".venv"

    # Windows first — avoids WinError 1920 on nonexistent .venv/bin
    if platform.system() == "Windows":
        candidates = [
            venv / "Scripts" / "python.exe",
            venv / "Scripts" / "python",
        ]
    else:
        candidates = [
            venv / "bin" / "python",
            project_root / ".venv-wsl" / "bin" / "python",
        ]

    for path in candidates:
        if path.exists():
            return str(path)

    raise FileNotFoundError(
        f"No valid Python executable found. Checked: {', '.join(str(p) for p in candidates)}"
    )


# ============================================================================
# Main Function
# ============================================================================

GLOBAL_CONVERSATION_STATE = {"messages": []}
CONNECTED_WEBSOCKETS = set()  # Track all connected clients


async def broadcast_message(message_type, data):
    """Broadcast a message to all connected WebSocket clients"""
    if CONNECTED_WEBSOCKETS:
        message = json.dumps({"type": message_type, **data})
        await asyncio.gather(
            *[ws.send(message) for ws in CONNECTED_WEBSOCKETS],
            return_exceptions=True
        )


async def websocket_handler(websocket, agent_ref, tools, logger):
    # Add this client to the set of connected clients
    CONNECTED_WEBSOCKETS.add(websocket)

    try:
        conversation_state = GLOBAL_CONVERSATION_STATE

        async for raw in websocket:

            # 1. Ignore empty or whitespace-only messages
            if not raw or not raw.strip():
                continue

            # 2. Try to parse JSON; if not JSON, treat as plain user text
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"type": "user", "text": raw}

            if data.get("type") == "list_models":
                models = get_available_models()
                last = load_last_model()
                await websocket.send(json.dumps({
                    "type": "models_list",
                    "models": models,
                    "last_used": last
                }))
                continue

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

            # 4. Browser requests model switch
            if data.get("type") == "switch_model":
                model_name = data.get("model")

                # Attempt to switch
                new_agent = await switch_model(model_name, tools, logger)

                # If switching failed (model not installed)
                if new_agent is None:
                    await websocket.send(json.dumps({
                        "type": "model_error",
                        "message": f"Model '{model_name}' is not installed."
                    }))
                    continue

                # Success — update the agent
                agent_ref[0] = new_agent

                await websocket.send(json.dumps({
                    "type": "model_switched",
                    "model": model_name
                }))
                continue

            # 5. Normal user message
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
                ][-MAX_MESSAGE_HISTORY:]

                # Run agent (using current model)
                agent = agent_ref[0]
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
    finally:
        # Remove this client when they disconnect
        CONNECTED_WEBSOCKETS.discard(websocket)


async def start_websocket_server(agent, tools, logger):
    """Start the WebSocket server without blocking"""

    async def handler(websocket):
        try:
            await websocket_handler(websocket, [agent], tools, logger)
        except websockets.exceptions.ConnectionClosed:
            pass

    server = await websockets.serve(handler, "127.0.0.1", 8765)
    logger.info("🌐 Browser UI available at ws://127.0.0.1:8765")
    return server


def input_thread(input_queue, stop_event):
    """Thread to handle blocking input() calls"""
    while not stop_event.is_set():
        try:
            query = input("> ")
            input_queue.put(query)
        except (EOFError, KeyboardInterrupt):
            break


async def cli_input_loop(agent, logger, tools, model_name):
    """Handle CLI input using a separate thread"""
    conversation_state = GLOBAL_CONVERSATION_STATE

    # Create queue and event for thread communication
    input_queue = Queue()
    stop_event = threading.Event()

    # Start input thread
    thread = threading.Thread(target=input_thread, args=(input_queue, stop_event), daemon=True)
    thread.start()

    def list_models():
        import subprocess, json

        try:
            out = subprocess.check_output(["ollama", "list"], text=True)
            lines = out.strip().split("\n")
            rows = lines[1:]

            parsed = []
            for line in rows:
                line_parts = line.split()
                if len(line_parts) < 4:
                    continue

                name = line_parts[0]
                model_id = line_parts[1]
                size = line_parts[2]
                modified = " ".join(line_parts[3:])

                parsed.append({
                    "name": name,
                    "id": model_id,
                    "size": size,
                    "modified": modified
                })

            json_str = json.dumps(parsed)
            models = json.loads(json_str)

            print("\n📦 Available models:")
            for m in models:
                print(f" - {m['name']}")
            print()

        except Exception as e:
            print(f"❌ Could not list models: {e}")

    try:
        while True:
            # Check for input from the queue
            await asyncio.sleep(0.1)  # Small delay to prevent busy waiting

            if not input_queue.empty():
                query = input_queue.get().strip()

                if not query:
                    continue

                if query == ":commands":
                    list_commands()
                    continue

                if query == ":models":
                    list_models()
                    continue

                if query.startswith(":model "):
                    parts = query.split(maxsplit=1)
                    if len(parts) == 1:
                        print("Usage: :model <model_name>")
                        continue

                    model_name = parts[1]
                    new_agent = await switch_model(model_name, tools, logger)
                    if new_agent is None:
                        continue

                    agent = new_agent
                    print(f"🤖 Model switched to {model_name}\n")
                    continue

                if query == ":model":
                    print(f"Using model: {model_name}\n")
                    continue

                # Normal chat
                logger.info(f"💬 Received query: '{query}'")

                conversation_state["messages"].append(
                    HumanMessage(content=query)
                )

                # Broadcast user message to web clients
                await broadcast_message("cli_user_message", {"text": query})

                # Trim history
                conversation_state["messages"] = [
                    m for m in conversation_state["messages"]
                    if isinstance(m, (HumanMessage, AIMessage))
                ][-MAX_MESSAGE_HISTORY:]

                logger.info("🏁 Starting agent execution")
                result = await agent.ainvoke(
                    conversation_state,
                    config={"recursion_limit": 50}
                )

                final_message = result["messages"][-1]
                conversation_state["messages"].append(final_message)

                answer = (
                    final_message.content
                    if isinstance(final_message, AIMessage)
                    else str(final_message)
                )

                print("\n" + answer + "\n")
                logger.info("✅ Query completed successfully")

                # Broadcast assistant message to web clients
                await broadcast_message("cli_assistant_message", {"text": answer})

    except KeyboardInterrupt:
        print("\n👋 Exiting.")
    finally:
        stop_event.set()


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
    system_prompt_path = PROJECT_ROOT / "prompts/tool_usage_guide.md"
    system_prompt = """You are a helpful assistant with access to tools.
    When you call a tool and receive a result, use that result to answer the user's question.
    Do not call the same tool repeatedly with the same parameters.
    Provide clear, concise answers based on the tool results."""

    if system_prompt_path.exists():
        logger.info(f"4️⃣  System prompt found!")
        system_prompt = system_prompt_path.read_text(encoding="utf-8")
    else:
        logger.warning(f"⚠️  System prompt file not found, using default")

    model_name = "llama3.1:8b"
    last = load_last_model()
    if last is not None and last != model_name:
        model_name = last
    logger.info(f"🤖 Using model: {model_name}")

    await ensure_ollama_running()

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
        system_prompt=system_prompt
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

    # Start both interfaces simultaneously
    print("\n🚀 Starting MCP Agent with dual interface support")
    print("=" * 60)

    # Open browser
    index_path = PROJECT_ROOT / "index.html"
    open_browser_file(index_path)

    # Start WebSocket server (non-blocking)
    websocket_server = await start_websocket_server(agent, tools, logger)

    print("🖥️  CLI interface ready")
    print("🌐 Browser interface ready at http://localhost:8765")
    print("=" * 60)
    print("\nBoth interfaces share the same conversation state!")
    print("Commands:")
    list_commands()
    print()

    # Run CLI input loop (this will block until Ctrl+C)
    try:
        await cli_input_loop(agent, logger, tools, model_name)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    finally:
        websocket_server.close()
        await websocket_server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())