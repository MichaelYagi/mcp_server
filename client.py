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
import socket

from datetime import datetime
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
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

# Import system monitor
try:
    from tools.system_monitor import system_monitor_loop, SystemMonitor

    SYSTEM_MONITOR_AVAILABLE = True
except ImportError:
    SYSTEM_MONITOR_AVAILABLE = False
    print("⚠️  System monitor not available. Install with: pip install psutil gputil nvidia-ml-py3")

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


# ============================================================================
# Subprocess Log Streaming via File Tailing
# ============================================================================

async def tail_log_file(filepath: Path, check_interval: float = 0.5):
    """
    Tail a log file and stream new lines to WebSocket clients.
    This allows us to capture server.py logs that are written to the shared log file.
    """
    if not filepath.exists():
        print(f"⏳ Waiting for log file to be created: {filepath}")
        # Wait for file to be created (max 30 seconds)
        for _ in range(30):
            await asyncio.sleep(1)
            if filepath.exists():
                break
        else:
            print(f"❌ Log file never created: {filepath}")
            return

    print(f"📋 Starting to tail log file: {filepath}")

    # Track last file position and size
    last_size = 0
    last_position = 0

    # Seek to end initially to only read new content
    try:
        last_size = filepath.stat().st_size
        last_position = last_size
        print(f"📋 Initial file size: {last_size} bytes, starting from end")
    except Exception as e:
        print(f"❌ Error getting initial file size: {e}")
        last_size = 0
        last_position = 0

    lines_read = 0

    while True:
        try:
            # Check if file size changed
            current_size = filepath.stat().st_size

            if current_size < last_size:
                # File was truncated/rotated, start from beginning
                print(f"📋 Log file was truncated, restarting from beginning")
                last_position = 0
                last_size = current_size

            if current_size > last_size:
                # New content available
                with open(filepath, 'r', encoding='utf-8', errors='replace') as file:
                    # Seek to last known position
                    file.seek(last_position)

                    # Read all new lines
                    new_lines = file.readlines()

                    for line in new_lines:
                        line = line.strip()
                        if not line:
                            continue

                        lines_read += 1

                        # Debug: print every 10th line to console
                        if lines_read % 10 == 0:
                            print(f"📋 Tailed {lines_read} lines from server log")

                        # Parse the log line
                        # Format: "2024-01-09 18:17:35,070 [INFO] logger_name: message"
                        log_entry = {
                            "timestamp": datetime.now().isoformat(),
                            "level": "INFO",
                            "name": "SERVER",
                            "message": line
                        }

                        # Try to extract log level
                        if "[DEBUG]" in line:
                            log_entry["level"] = "DEBUG"
                        elif "[INFO]" in line:
                            log_entry["level"] = "INFO"
                        elif "[WARNING]" in line or "[WARN]" in line:
                            log_entry["level"] = "WARNING"
                        elif "[ERROR]" in line:
                            log_entry["level"] = "ERROR"

                        # Extract logger name if possible
                        if "] " in line:
                            try:
                                # Format: "timestamp [LEVEL] name: message"
                                parts = line.split("] ", 1)
                                if len(parts) > 1:
                                    remaining = parts[1]
                                    if ": " in remaining:
                                        logger_name = remaining.split(": ", 1)[0]
                                        log_entry["name"] = logger_name
                            except:
                                pass

                        # Broadcast to WebSocket clients
                        if LOG_WEBSOCKET_CLIENTS and MAIN_EVENT_LOOP:
                            message = json.dumps({"type": "log", **log_entry})
                            await asyncio.gather(
                                *[ws.send(message) for ws in LOG_WEBSOCKET_CLIENTS],
                                return_exceptions=True
                            )

                    # Update position
                    last_position = file.tell()
                    last_size = current_size

            # Wait before next check
            await asyncio.sleep(check_interval)

        except FileNotFoundError:
            print(f"❌ Log file disappeared: {filepath}")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ Error tailing log file: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(1)


# ============================================================================
# WebSocket Log Handler
# ============================================================================

LOG_WEBSOCKET_CLIENTS = set()
SYSTEM_MONITOR_CLIENTS = set()  # For system stats monitoring
MAIN_EVENT_LOOP = None  # Will be set in main()


class WebSocketLogHandler(logging.Handler):
    """Custom log handler that broadcasts logs to WebSocket clients"""

    def emit(self, record):
        try:
            log_entry = {
                "timestamp": self.format_time(record),
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage()
            }

            # Broadcast to all connected log clients
            # Use run_coroutine_threadsafe to schedule the coroutine on the main event loop
            if MAIN_EVENT_LOOP is not None:
                asyncio.run_coroutine_threadsafe(
                    self.broadcast_log(log_entry),
                    MAIN_EVENT_LOOP
                )
        except Exception:
            self.handleError(record)

    def format_time(self, record):
        from datetime import datetime
        return datetime.fromtimestamp(record.created).isoformat()

    async def broadcast_log(self, log_entry):
        """Send log entry to all connected WebSocket clients"""
        if LOG_WEBSOCKET_CLIENTS:
            message = json.dumps({"type": "log", **log_entry})
            # Gather with return_exceptions to prevent one failed send from breaking others
            await asyncio.gather(
                *[ws.send(message) for ws in LOG_WEBSOCKET_CLIENTS],
                return_exceptions=True
            )


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
    tools: dict


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

def router(state):
    """Route based on what the agent decided to do"""
    last_message = state["messages"][-1]

    logger = logging.getLogger("mcp_client")
    logger.info(f"🎯 Router: Last message type = {type(last_message).__name__}")

    # If the AI made tool calls, go to tools node
    if isinstance(last_message, AIMessage):
        tool_calls = getattr(last_message, "tool_calls", [])
        logger.info(f"🎯 Router: Found {len(tool_calls)} tool calls")
        if tool_calls and len(tool_calls) > 0:
            logger.info(f"🎯 Router: Routing to TOOLS")
            return "tools"

    # If it's a user message, check for special routing
    if isinstance(last_message, HumanMessage):
        content = last_message.content.lower()
        logger.info(f"🎯 Router: User message content: {content[:100]}")

        # Check for ingestion
        if "ingest" in content:
            logger.info(f"🎯 Router: Routing to INGEST")
            return "ingest"

        # Check for RAG queries
        if not any(keyword in content for keyword in ["movie", "plex", "search", "find", "show"]):
            if any(keyword in content for keyword in ["what is", "who is", "explain", "tell me about"]):
                logger.info(f"🎯 Router: Routing to RAG")
                return "rag"

    # Default: end conversation
    logger.info(f"🎯 Router: Routing to END (agent)")
    return "agent"


async def rag_node(state):
    """Search RAG and provide context to answer the question"""
    query = state["messages"][-1].content

    # Find the rag_search_tool
    tools_dict = state.get("tools", {})
    rag_search_tool = None

    for tool in tools_dict.values() if isinstance(tools_dict, dict) else tools_dict:
        if hasattr(tool, 'name') and tool.name == "rag_search_tool":
            rag_search_tool = tool
            break

    if not rag_search_tool:
        msg = AIMessage(content="RAG search is not available.")
        return {"messages": state["messages"] + [msg]}

    try:
        result = await rag_search_tool.ainvoke({"query": query})

        if isinstance(result, str):
            result = json.loads(result)

        chunks = []
        if isinstance(result, dict):
            results_list = result.get("results", [])
            chunks = [item.get("text", "") for item in results_list if isinstance(item, dict)]

        if not chunks:
            msg = AIMessage(content="I couldn't find any relevant information in the knowledge base.")
            return {"messages": state["messages"] + [msg]}

        context = "\n\n".join(chunks[:3])

        augmented_messages = state["messages"][:-1] + [
            SystemMessage(content=f"Use this context to answer the question:\n\n{context}"),
            state["messages"][-1]
        ]

        llm = state.get("llm")
        if not llm:
            from langchain_ollama import ChatOllama
            llm = ChatOllama(model="llama3.1:8b", temperature=0)

        response = await llm.ainvoke(augmented_messages)

        return {"messages": state["messages"] + [response]}

    except Exception as e:
        logger = logging.getLogger("mcp_client")
        logger.error(f"❌ Error in RAG node: {e}")
        msg = AIMessage(content=f"Error searching knowledge base: {str(e)}")
        return {"messages": state["messages"] + [msg]}


# ============================================================================
# Agent Graph Builder
# ============================================================================

MODEL_STATE_FILE = "last_model.txt"

import subprocess


def get_available_models():
    try:
        out = subprocess.check_output(["ollama", "list"], text=True)
        lines = out.strip().split("\n")

        models = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                models.append(parts[0])

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

    new_llm = ChatOllama(model=model_name, temperature=0)
    llm_with_tools = new_llm.bind_tools(tools)

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

    async def call_model(state: AgentState):
        messages = state["messages"]
        logger.info(f"🧠 Calling LLM with {len(messages)} messages")

        response = await llm_with_tools.ainvoke(messages)

        tool_calls = getattr(response, "tool_calls", [])
        logger.info(f"🔧 LLM returned {len(tool_calls)} tool calls")

        if len(tool_calls) == 0 and response.content:
            import re
            import json as json_module

            content = response.content.strip()

            try:
                parsed = json_module.loads(content)
                if isinstance(parsed, dict) and parsed.get("name"):
                    tool_name = parsed["name"]
                    args = parsed.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json_module.loads(args)
                        except:
                            args = {}

                    logger.info(f"🔧 Parsed JSON tool call: {tool_name}({args})")
                    response.tool_calls = [{
                        "name": tool_name,
                        "args": args,
                        "id": "manual_call_1",
                        "type": "tool_call"
                    }]
            except (json_module.JSONDecodeError, ValueError):
                match = re.search(r'(\w+)\((.*?)\)', content.replace('\n', '').replace('`', ''))
                if match:
                    tool_name = match.group(1)
                    args_str = match.group(2).strip()

                    args = {}
                    if args_str:
                        for arg_match in re.finditer(r'(\w+)\s*=\s*(["\']?)([^,\)]+)\2', args_str):
                            key = arg_match.group(1)
                            value = arg_match.group(3).strip().strip('"\'')
                            try:
                                value = int(value)
                            except:
                                pass
                            args[key] = value

                    logger.info(f"🔧 Parsed function call: {tool_name}({args})")
                    response.tool_calls = [{
                        "name": tool_name,
                        "args": args,
                        "id": "manual_call_1",
                        "type": "tool_call"
                    }]

        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tc in response.tool_calls:
                logger.info(f"🔧   Tool: {tc.get('name', 'unknown')}, Args: {tc.get('args', {})}")
        else:
            logger.info(f"🔧 No tool calls. Response: {response.content[:200]}")

        return {
            "messages": messages + [response],
            "tools": state.get("tools", {}),
        }

    async def ingest_node(state: AgentState):
        tools_dict = state.get("tools", {})
        ingest_tool = None

        for tool in tools_dict.values() if isinstance(tools_dict, dict) else tools_dict:
            if hasattr(tool, 'name') and tool.name == "plex_ingest_batch":
                ingest_tool = tool
                break

        if not ingest_tool:
            msg = AIMessage(content="Ingestion tool not available.")
            return {
                "messages": state["messages"] + [msg],
                "tools": state.get("tools", {}),
            }

        try:
            result = await ingest_tool.ainvoke({"limit": 5})

            if isinstance(result, str) and result.startswith('[TextContent('):
                import re
                match = re.search(r"text='([^']*(?:\\'[^']*)*)'", result)
                if match:
                    result = match.group(1).replace("\\'", "'").replace("\\n", "\n")

            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    msg = AIMessage(content=f"Error: Could not parse ingestion result")
                    return {
                        "messages": state["messages"] + [msg],
                        "tools": state.get("tools", {}),
                    }

            if isinstance(result, dict) and "error" in result:
                msg = AIMessage(content=f"Ingestion error: {result['error']}")
            else:
                ingested = result.get('ingested', []) if isinstance(result, dict) else []
                remaining = result.get('remaining', 0) if isinstance(result, dict) else 0
                total_ingested = result.get('total_ingested', 0) if isinstance(result, dict) else 0

                if ingested:
                    items_list = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(ingested))

                    msg = AIMessage(
                        content=f"✅ **Successfully ingested {len(ingested)} items:**\n\n{items_list}\n\n"
                                f"📊 **Total items in RAG:** {total_ingested}\n"
                                f"📊 **Remaining to ingest:** {remaining}"
                    )
                else:
                    msg = AIMessage(
                        content=f"✅ All items already ingested.\n\n📊 **Total items in RAG:** {total_ingested}"
                    )

        except Exception as e:
            logger.error(f"❌ Error in ingest_node: {e}")
            import traceback
            traceback.print_exc()
            msg = AIMessage(content=f"Ingestion failed: {str(e)}")

        return {
            "messages": state["messages"] + [msg],
            "tools": state.get("tools", {}),
        }

    workflow = StateGraph(AgentState)

    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("rag", rag_node)
    workflow.add_node("ingest", ingest_node)

    workflow.set_entry_point("agent")

    workflow.add_conditional_edges(
        "agent",
        router,
        {
            "tools": "tools",
            "rag": "rag",
            "ingest": "ingest",
            "agent": END
        }
    )

    workflow.add_edge("tools", "agent")
    workflow.add_edge("ingest", "agent")
    workflow.add_edge("rag", END)

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
CONNECTED_WEBSOCKETS = set()


async def broadcast_message(message_type, data):
    """Broadcast a message to all connected WebSocket clients"""
    if CONNECTED_WEBSOCKETS:
        message = json.dumps({"type": message_type, **data})
        await asyncio.gather(
            *[ws.send(message) for ws in CONNECTED_WEBSOCKETS],
            return_exceptions=True
        )


async def websocket_handler(websocket, agent_ref, tools, logger):
    CONNECTED_WEBSOCKETS.add(websocket)

    # Track if this client wants system stats
    subscribe_to_stats = False

    try:
        conversation_state = GLOBAL_CONVERSATION_STATE

        async for raw in websocket:

            if not raw or not raw.strip():
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"type": "user", "text": raw}

            # Handle system stats subscription
            if data.get("type") == "subscribe_system_stats":
                subscribe_to_stats = True
                SYSTEM_MONITOR_CLIENTS.add(websocket)
                await websocket.send(json.dumps({
                    "type": "subscribed",
                    "subscription": "system_stats"
                }))
                continue

            if data.get("type") == "unsubscribe_system_stats":
                subscribe_to_stats = False
                SYSTEM_MONITOR_CLIENTS.discard(websocket)
                await websocket.send(json.dumps({
                    "type": "unsubscribed",
                    "subscription": "system_stats"
                }))
                continue

            if data.get("type") == "list_models":
                models = get_available_models()
                last = load_last_model()
                await websocket.send(json.dumps({
                    "type": "models_list",
                    "models": models,
                    "last_used": last
                }))
                continue

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

            if data.get("type") == "switch_model":
                model_name = data.get("model")

                new_agent = await switch_model(model_name, tools, logger)

                if new_agent is None:
                    await websocket.send(json.dumps({
                        "type": "model_error",
                        "message": f"Model '{model_name}' is not installed."
                    }))
                    continue

                agent_ref[0] = new_agent

                await websocket.send(json.dumps({
                    "type": "model_switched",
                    "model": model_name
                }))
                continue

            if data.get("type") == "user" or "text" in data:
                prompt = data.get("text")

                print(f"\n> {prompt}")

                await broadcast_message("user_message", {"text": prompt})

                agent = agent_ref[0]
                result = await run_agent(agent, conversation_state, prompt, logger, tools)

                final_message = result["messages"][-1]
                assistant_text = final_message.content

                print("\n" + assistant_text + "\n")

                await broadcast_message("assistant_message", {"text": assistant_text})
    finally:
        CONNECTED_WEBSOCKETS.discard(websocket)
        SYSTEM_MONITOR_CLIENTS.discard(websocket)  # Clean up stats subscription


async def log_websocket_handler(websocket):
    """Handle WebSocket connections for log streaming"""
    LOG_WEBSOCKET_CLIENTS.add(websocket)

    try:
        async for message in websocket:
            pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        LOG_WEBSOCKET_CLIENTS.discard(websocket)


async def start_websocket_server(agent, tools, logger, host="0.0.0.0", port=8765):
    """Start the WebSocket server without blocking"""

    async def handler(websocket):
        try:
            await websocket_handler(websocket, [agent], tools, logger)
        except websockets.exceptions.ConnectionClosed:
            pass

    server = await websockets.serve(handler, host, port)

    import socket
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        logger.info(f"🌐 WebSocket listening on {host}:{port}")
        logger.info(f"   Local: ws://localhost:{port}")
        logger.info(f"   Network: ws://{local_ip}:{port}")
    except:
        logger.info(f"🌐 WebSocket server at ws://{host}:{port}")

    return server


async def start_log_websocket_server(host="0.0.0.0", port=8766):
    """Start a separate WebSocket server for log streaming"""

    server = await websockets.serve(log_websocket_handler, host, port)

    logger = logging.getLogger("mcp_client")
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        logger.info(f"📊 Log WebSocket listening on {host}:{port}")
        logger.info(f"   Local: ws://localhost:{port}")
        logger.info(f"   Network: ws://{local_ip}:{port}")
    except:
        logger.info(f"📊 Log WebSocket server at ws://{host}:{port}")

    return server


def start_http_server(port=9000):
    """Serve index.html over HTTP on the network"""
    Handler = SimpleHTTPRequestHandler

    def serve():
        with TCPServer(("0.0.0.0", port), Handler) as httpd:
            try:
                # Get actual network IP (not 127.0.1.1)
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()

                print(f"📄 HTTP server listening on 0.0.0.0:{port}")
                print(f"   Local: http://localhost:{port}/index.html")
                print(f"   Network: http://{local_ip}:{port}/index.html")
            except:
                print(f"📄 HTTP server running on 0.0.0.0:{port}")
            httpd.serve_forever()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()


def input_thread(input_queue, stop_event):
    """Thread to handle blocking input() calls"""
    while not stop_event.is_set():
        try:
            query = input("> ")
            input_queue.put(query)
        except (EOFError, KeyboardInterrupt):
            break


async def run_agent(agent, conversation_state, user_message, logger, tools):
    try:
        conversation_state["loop_count"] += 1

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

        if not conversation_state["messages"]:
            conversation_state["messages"].append(
                SystemMessage(content=SYSTEM_PROMPT)
            )

        conversation_state["messages"].append(
            HumanMessage(content=user_message)
        )

        conversation_state["messages"] = conversation_state["messages"][-MAX_MESSAGE_HISTORY:]

        if not isinstance(conversation_state["messages"][0], SystemMessage):
            conversation_state["messages"].insert(0, SystemMessage(content=SYSTEM_PROMPT))

        logger.info(f"🧠 Calling LLM with {len(conversation_state['messages'])} messages")

        tool_registry = {tool.name: tool for tool in tools}

        result = await agent.ainvoke({
            "messages": conversation_state["messages"],
            "tools": tool_registry
        })

        conversation_state["messages"] = result["messages"]
        conversation_state["loop_count"] = 0

        return {"messages": conversation_state["messages"]}

    except Exception as e:
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

        logger.exception("❌ Unexpected error in agent execution")

        error_text = getattr(e, "args", [str(e)])[0]

        error_msg = AIMessage(
            content=f"An error occurred while running the agent:\n\n{error_text}"
        )

        conversation_state["messages"].append(error_msg)
        return {"messages": conversation_state["messages"]}


async def cli_input_loop(agent, logger, tools, model_name):
    """Handle CLI input using a separate thread"""
    conversation_state = GLOBAL_CONVERSATION_STATE

    input_queue = Queue()
    stop_event = threading.Event()

    thread = threading.Thread(target=input_thread, args=(input_queue, stop_event), daemon=True)
    thread.start()

    def tool_description(tools_obj, tool_name):
        found = False
        for t in tools_obj:
            if t.name == tool_name:
                logger.info(f"  - {t.description}")
                found = True
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
            await asyncio.sleep(0.1)

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

                logger.info(f"💬 Received query: '{query}'")

                print(f"\n> {query}")

                await broadcast_message("cli_user_message", {"text": query})

                result = await run_agent(agent, conversation_state, query, logger, tools)

                final_message = result["messages"][-1]
                assistant_text = final_message.content

                print("\n" + assistant_text + "\n")
                logger.info("✅ Query completed successfully")

                await broadcast_message("cli_assistant_message", {"text": assistant_text})

    except KeyboardInterrupt:
        print("\n👋 Exiting.")
    finally:
        stop_event.set()


def open_browser_file(path: Path):
    import platform
    import subprocess
    import webbrowser

    if "microsoft" in platform.uname().release.lower():
        windows_path = str(path).replace("/mnt/c", "C:").replace("/", "\\")
        subprocess.run(["cmd.exe", "/c", "start", windows_path], shell=False)
    else:
        webbrowser.open(f"file://{path}")


async def main():
    global MAIN_EVENT_LOOP

    # Capture the main event loop for use in the log handler
    MAIN_EVENT_LOOP = asyncio.get_running_loop()

    load_dotenv()

    PROJECT_ROOT = Path(__file__).resolve().parent
    LOG_DIR = Path(str(PROJECT_ROOT / "logs"))
    LOG_DIR.mkdir(exist_ok=True)

    # Client logs go to mcp-client.log
    CLIENT_LOG_FILE = LOG_DIR / "mcp-client.log"
    # Server logs are in mcp-server.log (we'll tail this)
    SERVER_LOG_FILE = LOG_DIR / "mcp-server.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(CLIENT_LOG_FILE, encoding="utf-8"),
            logging.StreamHandler()
        ],
    )

    # Add WebSocket log handler to root logger to catch ALL logs
    ws_log_handler = WebSocketLogHandler()
    ws_log_handler.setLevel(logging.DEBUG)  # Capture DEBUG and above
    root_logger = logging.getLogger()
    root_logger.addHandler(ws_log_handler)

    # Set specific log levels for different components
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("langchain").setLevel(logging.DEBUG)
    logging.getLogger("mcp").setLevel(logging.DEBUG)

    # Set these to propagate to root (default behavior, but being explicit)
    logging.getLogger("httpx").propagate = True
    logging.getLogger("langchain").propagate = True
    logging.getLogger("mcp").propagate = True

    logger = logging.getLogger("mcp_client")

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

    llm = ChatOllama(
        model=model_name,
        temperature=0
    )

    mcp_agent = MCPAgent(
        llm=llm,
        client=client,
        max_steps=10,
        system_prompt=SYSTEM_PROMPT
    )

    mcp_agent.debug = True
    await mcp_agent.initialize()

    tools = mcp_agent._tools

    llm_with_tools = llm.bind_tools(tools)

    logger.info("=" * 60)
    logger.info("🧪 TESTING TOOL BINDING, ALMOST THERE!")
    test_messages = [
        SystemMessage(content="You have access to tools. Call the semantic_media_search_text tool to find movies."),
        HumanMessage(content="find action movies")
    ]
    test_response = await llm_with_tools.ainvoke(test_messages)
    logger.info(f"Test response type: {type(test_response)}")
    logger.info(f"Has tool_calls attr: {hasattr(test_response, 'tool_calls')}")
    if hasattr(test_response, 'tool_calls'):
        tool_calls = test_response.tool_calls
        logger.info(f"Number of tool calls: {len(tool_calls)}")
        if tool_calls:
            for tc in tool_calls:
                logger.info(f"  Tool call: {tc}")
    else:
        logger.info("No tool_calls attribute found!")
    logger.info(f"Response content: {test_response.content[:300]}")
    logger.info("=" * 60)

    agent = create_langgraph_agent(llm_with_tools, tools)

    print("\n🚀 Starting MCP Agent with dual interface support")
    print("=" * 60)

    index_path = PROJECT_ROOT / "index.html"
    open_browser_file(index_path)

    start_http_server(port=9000)

    websocket_server = await start_websocket_server(agent, tools, logger, host="0.0.0.0", port=8765)
    log_websocket_server = await start_log_websocket_server(host="0.0.0.0", port=8766)

    # Start tailing the server log file to capture server.py logs in Web UI
    asyncio.create_task(tail_log_file(SERVER_LOG_FILE))

    # Start system monitor for real-time CPU/GPU stats
    if SYSTEM_MONITOR_AVAILABLE:
        asyncio.create_task(system_monitor_loop(SYSTEM_MONITOR_CLIENTS, update_interval=1.0))
        print("📊 System monitor started (update interval: 1.0s)")
    else:
        print("⚠️  System monitor disabled (install psutil, gputil, nvidia-ml-py3)")

    # Start system monitor for real-time CPU/GPU stats
    asyncio.create_task(system_monitor_loop(SYSTEM_MONITOR_CLIENTS, update_interval=1.0))

    print("🖥️  CLI interface ready")
    print("🌐 Browser interface ready at http://localhost:9000")
    print("📊 Log streaming ready at ws://localhost:8766")
    print("📋 Tailing server logs: {}".format(SERVER_LOG_FILE))
    print()

    # Show file status
    if SERVER_LOG_FILE.exists():
        size = SERVER_LOG_FILE.stat().st_size
        print(f"📋 Server log file exists: {size} bytes")
    else:
        print(f"⚠️  Server log file does NOT exist yet: {SERVER_LOG_FILE}")
        print(f"   It will be created when server.py starts")
    print()
    print("=" * 60)
    print("\nBoth interfaces share the same conversation state!")
    print("Commands:")
    list_commands()
    print()

    try:
        await cli_input_loop(agent, logger, tools, model_name)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    finally:
        websocket_server.close()
        await websocket_server.wait_closed()
        log_websocket_server.close()
        await log_websocket_server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())