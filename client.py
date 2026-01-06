import asyncio
import os
import logging
import requests
import operator
import json
import websockets

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

async def websocket_handler(websocket, agent_ref, tools, logger):
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

async def start_websocket_server(agent, tools, logger):
    async with websockets.serve(
        lambda ws: websocket_handler(ws, [agent], tools, logger),
        "127.0.0.1",
        8765
    ):
        print("🌐 Browser UI available at ws://127.0.0.1:8765")
        await asyncio.Future()  # run forever

async def cli_loop(agent, system_prompt, logger, tools, model_name):
    print("\n✅ MCP Agent ready with LangGraph. Type a prompt (Ctrl+C to exit).\n")

    # Persistent conversation state
    conversation_state = {"messages": []}

    def list_models():
        import subprocess, json

        try:
            # Run ollama list (no --json available)
            out = subprocess.check_output(["ollama", "list"], text=True)

            lines = out.strip().split("\n")

            # Skip header line
            rows = lines[1:]

            parsed = []
            for line in rows:
                line_parts = line.split()
                if len(line_parts) < 4:
                    continue

                # NAME may contain no spaces → safe to take line_parts[0]
                name = line_parts[0]
                model_id = line_parts[1]
                size = line_parts[2]
                modified = " ".join(line_parts[3:])  # e.g. "15 hours ago"

                parsed.append({
                    "name": name,
                    "id": model_id,
                    "size": size,
                    "modified": modified
                })

            # Convert to JSON string so json.loads() works
            json_str = json.dumps(parsed)
            models = json.loads(json_str)

            print("\n📦 Available models:")
            for m in models:
                print(f" - {m['name']}")
            print()

        except Exception as e:
            print(f"❌ Could not list models: {e}")

    while True:
        try:
            query = input("> ").strip()
            if not query:
                continue

            if query == ":commands":
                list_commands()
                continue

            # -------------------------
            # MODEL SWITCH COMMAND
            # -------------------------

            # 1. Exact match for listing models
            if query == ":models":
                list_models()
                continue

            # 2. Model switching command
            if query.startswith(":model "):  # note the space!
                parts = query.split(maxsplit=1)
                if len(parts) == 1:
                    print("Usage: :model <model_name>")
                    continue

                model_name = parts[1]
                new_agent = await switch_model(model_name, tools, logger)
                if new_agent is None:
                    continue

                agent = new_agent
                model_name = model_name  # update current model
                print(f"🤖 Model switched to {model_name}\n")

                continue

            # 3. If user typed ":model" with no argument
            if query == ":model":
                print(f"Using model: {model_name}\n")
                continue

            # -------------------------
            # NORMAL CHAT
            # -------------------------
            logger.info(f"💬 Received query: '{query}'")

            conversation_state["messages"].append(
                HumanMessage(content=query)
            )

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
    system_prompt_path = PROJECT_ROOT / "prompts/tool_usage_guide.md"
    system_prompt = """You are a helpful assistant with access to tools.
    When you call a tool and receive a result, use that result to answer the user's question.
    Do not call the same tool repeatedly with the same parameters.
    Provide clear, concise answers based on the tool results."""

    if system_prompt_path.exists():
        logger.info(f"4️⃣  System prompt found!")
        system_prompt = system_prompt_path.read_text()
    else:
        logger.warning(f"⚠️  System prompt file not found, using default")

    model_name = "llama3.1:8b"
    last = load_last_model()
    if last is not None and last != model_name:
        model_name = last
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

    print("\nChoose interface:")
    print("1) Browser")
    print("2) CLI")
    choice = input("> ").strip()

    if choice == "1":
        print("🌐 Starting browser UI mode...")

        index_path = PROJECT_ROOT / "index.html"
        open_browser_file(index_path)

        await start_websocket_server(agent, tools, logger)

    else:
        print("🖥️ Starting CLI mode...")
        print("Commands:")
        list_commands()
        await cli_loop(agent, system_prompt, logger, tools, model_name)

if __name__ == "__main__":
    asyncio.run(main())