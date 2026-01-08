import asyncio
import os
import logging
import requests
import operator
import json
import sys
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
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# Load environment variables from .env file
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

# How many messages to keep (user + assistant only)
MAX_MESSAGE_HISTORY = int(os.getenv("MAX_MESSAGE_HISTORY", "20"))

SYSTEM_PROMPT = """You are a helpful assistant with access to tools.
    When you call a tool and receive a result, use that result to answer the user's question.
    Do not call the same tool repeatedly with the same parameters.
    Provide clear, concise answers based on the tool results."""

agent = None

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
    messages = state["messages"]
    last = messages[-1]

    # Only continue if the last message contains at least one valid tool call
    if isinstance(last, AIMessage):
        tool_calls = getattr(last, "tool_calls", None)

        if tool_calls and isinstance(tool_calls, list):
            valid_calls = [
                call for call in tool_calls
                if isinstance(call, dict)
                and "name" in call
                and call.get("args") is not None
            ]

            if valid_calls:
                return "continue"

    # Otherwise, stop
    return "end"

# ============================================================================
# RAG router
# ============================================================================

# Decide when to use RAG
def router(state):
    last = state["messages"][-1].content.lower()

    if state.get("tool_calls"):
        return "tools"

    if "ingest" in last or "update knowledge" in last:
        return "ingest"

    if any(x in last for x in ["what is", "who is", "explain", "tell me about"]):
        return "rag"

    return "agent"

# Call rag_search tool and inject context
async def rag_node(state):
    query = state["messages"][-1].content

    # Call the RAG search tool
    rag_result = await state["tools"]["rag_search_tool"].ainvoke({"query": query})

    chunks = rag_result.get("chunks", [])
    context = "\n\n".join(chunks)

    augmented = [
        SystemMessage(content="Use the provided context to answer."),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}")
    ]

    response = await state["llm"].ainvoke(augmented)
    state["messages"].append(response)

    return state

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

async def ingest_node(state: AgentState):
    ingest_tool = state["tools"]["plex_ingest_batch"]
    result = await ingest_tool.ainvoke({"limit": 5})

    msg = AIMessage(
        content=f"Ingested: {result['ingested']}\nRemaining: {result['remaining']}"
    )

    return {
        "messages": state["messages"] + [msg],
        "tool_calls": [],
        "tools": state["tools"],
    }

async def switch_model(model_name, tools, logger):
    global agent

    available = get_available_models()

    if model_name not in available:
        print(f"❌ Model '{model_name}' is not installed.")
        print("📦 Available models:")
        for m in available:
            print(f" - {m}")
        print()
        return None

    logger.info(f"🔄 Switching model to: {model_name}")

    # Build new LLM
    new_llm = ChatOllama(model=model_name, temperature=0)
    llm_with_tools = new_llm.bind_tools(tools)

    # Rebuild LangGraph agent
    agent = create_langgraph_agent(llm_with_tools, tools)

    save_last_model(model_name)

    logger.info(f"✅ Model switched to {model_name}")
    return agent


def list_commands():
    print(":commands - List all available commands")
    print(":tools - List all available tools")
    print(":tool <tool> - Get the tool description")
    print(":model - View the current active model")
    print(":model <model> - Use the model passed")
    print(":models - List available models")
    print(":clear history - Clear the chat history")

def create_langgraph_agent(llm_with_tools, tools):
    logger = logging.getLogger("mcp_client")

    #
    # 1. Agent (LLM) node
    #
    async def call_model(state: AgentState):
        messages = state["messages"]
        logger.info(f"🧠 Calling LLM with {len(messages)} messages")

        response = await llm_with_tools.ainvoke(messages)

        return {
            "messages": messages + [response],
            "tool_calls": getattr(response, "tool_calls", []),
            "tools": state.get("tools", tools),
        }

    #
    # 2. Ingestion node
    #
    async def ingest_node(state: AgentState):
        ingest_tool = state["tools"].get("plex_ingest_batch")
        if not ingest_tool:
            msg = AIMessage(content="Ingestion tool not available.")
            return {
                "messages": state["messages"] + [msg],
                "tool_calls": [],
                "tools": state["tools"],
            }

        result = await ingest_tool.ainvoke({"limit": 5})
        msg = AIMessage(
            content=f"Ingested: {result.get('ingested')}\nRemaining: {result.get('remaining')}"
        )

        return {
            "messages": state["messages"] + [msg],
            "tool_calls": [],
            "tools": state["tools"],
        }

    #
    # 3. Build graph
    #
    workflow = StateGraph(AgentState)

    # Nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("rag", rag_node)
    workflow.add_node("ingest", ingest_node)   # ← REQUIRED

    # Entry point
    workflow.set_entry_point("agent")

    #
    # 4. Router transitions
    #
    workflow.add_conditional_edges(
        "agent",
        router,
        {
            "tools": "tools",
            "rag": "rag",
            "ingest": "ingest",   # ← REQUIRED
            "agent": END
        }
    )

    #
    # 5. Node-to-node edges
    #
    workflow.add_edge("tools", "agent")     # tools → agent
    workflow.add_edge("ingest", "agent")    # ingest → agent
    workflow.add_edge("rag", END)           # rag → end

    #
    # 6. Compile
    #
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

GLOBAL_CONVERSATION_STATE = {
    "messages": [],
    "loop_count": 0
}
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

                # Show user prompt in CLI
                print(f"\n> {prompt}")

                # Send user prompt to Web UI
                await websocket.send(json.dumps({
                    "type": "user_message",
                    "text": prompt
                }))

                # Run agent
                agent = agent_ref[0]
                result = await run_agent(agent, conversation_state, prompt, logger)

                # Extract assistant message
                final_message = result["messages"][-1]
                assistant_text = final_message.content

                # Print assistant response to CLI
                print("\n" + assistant_text + "\n")

                # Send assistant response to Web UI
                await websocket.send(json.dumps({
                    "type": "assistant_message",
                    "text": assistant_text
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

async def run_agent(agent, conversation_state, user_message, logger):
    try:
        # Increment loop counter
        conversation_state["loop_count"] += 1

        # Loop guard
        if conversation_state["loop_count"] >= 5:
            logger.error("⚠️ Loop detected — stopping early after 5 iterations.")

            error_msg = AIMessage(
                content=(
                    "I detected that this request was causing repeated reasoning loops. "
                    "I'm stopping early to avoid getting stuck. "
                    "Try rephrasing your request or simplifying what you're asking for."
                )
            )

            conversation_state["messages"].append(error_msg)
            conversation_state["loop_count"] = 0
            return {"messages": conversation_state["messages"]}

        # Ensure system prompt exists
        if not conversation_state["messages"]:
            conversation_state["messages"].append(
                SystemMessage(content=SYSTEM_PROMPT)
            )

        # Add user message
        conversation_state["messages"].append(
            HumanMessage(content=user_message)
        )

        # Trim history (keep tool messages)
        conversation_state["messages"] = conversation_state["messages"][-MAX_MESSAGE_HISTORY:]

        # Ensure system prompt stays at index 0
        if not isinstance(conversation_state["messages"][0], SystemMessage):
            conversation_state["messages"].insert(0, SystemMessage(content=SYSTEM_PROMPT))

        logger.info(f"🧠 Calling LLM with {len(conversation_state['messages'])} messages")

        # Run the agent
        result = await agent.ainvoke({"messages": conversation_state["messages"]})

        # Replace conversation state with returned messages
        conversation_state["messages"] = result["messages"]
        conversation_state["loop_count"] = 0

        return {"messages": conversation_state["messages"]}

    except Exception as e:
        # Recursion limit handling
        if "GraphRecursionError" in str(e):
            logger.error("❌ Recursion limit reached — stopping agent loop safely.")

            error_msg = AIMessage(
                content=(
                    "I ran into a recursion limit while processing your request. "
                    "This usually means the model kept looping instead of producing a final answer. "
                    "Try rephrasing your request or simplifying what you're asking for."
                )
            )

            conversation_state["messages"].append(error_msg)
            return {"messages": conversation_state["messages"]}

        # Any other error — return the REAL exception message
        logger.exception("❌ Unexpected error in agent execution")

        # Extract the meaningful part of the error
        error_text = getattr(e, "args", [str(e)])[0]

        error_msg = AIMessage(
            content=f"An error occurred while running the agent:\n\n{error_text}"
        )

        conversation_state["messages"].append(error_msg)
        return {"messages": conversation_state["messages"]}

async def cli_input_loop(agent, logger, tools, model_name):
    """Handle CLI input using a separate thread"""
    conversation_state = GLOBAL_CONVERSATION_STATE

    # Create queue and event for thread communication
    input_queue = Queue()
    stop_event = threading.Event()

    # Start input thread
    thread = threading.Thread(target=input_thread, args=(input_queue, stop_event), daemon=True)
    thread.start()

    def tool_description(tools_obj, tool_name):
        found=False
        for t in tools_obj:
            if t.name == tool_name:
                logger.info(f"  - {t.description}")
                found=True
                break
        if not found:
            logger.info(f"❌ MCP tool {tool_name} not found")

    def list_tools(tools_obj):
        logger.info(f"🛠 Found {len(tools_obj)} MCP tools:")
        for t in tools_obj:
            logger.info(f"  - {t.name}")

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

                if query == ":tools":
                    list_tools(tools)
                    continue

                if query.startswith(":tool "):
                    parts = query.split(maxsplit=1)
                    if len(parts) == 1:
                        print("Usage: :tool <tool_name>")
                        continue

                    tool_name = parts[1]
                    tool_description(tools, tool_name)
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

                if query.startswith(":clear "):
                    parts = query.split()
                    if len(parts) == 1:
                        print(f"Specify what to clear")
                        continue

                    target = parts[1]

                    if target == "history":
                        conversation_state["messages"] = []
                        conversation_state["messages"].append(SystemMessage(content=SYSTEM_PROMPT))
                        print(f"Chat history cleared.")
                        continue

                    else:
                        print(f"Unknown clear target: {target}")
                        continue

                # Normal chat
                logger.info(f"💬 Received query: '{query}'")

                # 1. Print user prompt to CLI
                print(f"\n> {query}")

                # 2. Broadcast user prompt to Web UI
                await broadcast_message("cli_user_message", {"text": query})

                # 3. Run unified agent pipeline (returns FULL LangGraph result)
                result = await run_agent(agent, conversation_state, query, logger)

                # 4. Extract assistant message
                final_message = result["messages"][-1]
                assistant_text = final_message.content

                # 5. Print assistant response to CLI
                print("\n" + assistant_text + "\n")
                logger.info("✅ Query completed successfully")

                # 6. Broadcast assistant response to Web UI
                await broadcast_message("cli_assistant_message", {"text": assistant_text})

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

    logger = logging.getLogger("mcp_client")

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

    if system_prompt_path.exists():
        logger.info(f"⚙️ System prompt found!")
        SYSTEM_PROMPT = system_prompt_path.read_text(encoding="utf-8")
    else:
        logger.warning(f"⚠️  System prompt file not found, using default")

    model_name = "llama3.1:8b"
    last = load_last_model()
    available = get_available_models()
    available_count = len(available)

    if available_count == 0:
        print("❌ No models available. Download models using `ollama pull <model>` and run `ollama serve`. Exiting.")
        sys.exit(1)

    if last is not None and last != model_name and last in available:
        model_name = last

    save_last_model(model_name)
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