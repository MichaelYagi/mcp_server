"""
MCP Client - Main Entry Point (WITH MULTI-AGENT INTEGRATION - FIXED STATE)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from mcp_use.client.client import MCPClient
from mcp_use.agents.mcpagent import MCPAgent

# Import client modules
from client import logging_handler
from client import langgraph
from client import models
from client import websocket
from client import cli
from client import utils

# Import multi-agent system
try:
    from client.multi_agent import MultiAgentOrchestrator, should_use_multi_agent
    MULTI_AGENT_AVAILABLE = True
except ImportError:
    print("⚠️ Multi-agent system not available. Add multi_agent.py to client/ directory.")
    MULTI_AGENT_AVAILABLE = False

# Import system monitor conditionally
try:
    from tools.system_monitor import system_monitor_loop
    SYSTEM_MONITOR_AVAILABLE = True
except ImportError:
    SYSTEM_MONITOR_AVAILABLE = False
    print("⚠️  System monitor not available. Install with: pip install psutil gputil nvidia-ml-py3")

# Load environment variables
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

# Configuration
MAX_MESSAGE_HISTORY = int(os.getenv("MAX_MESSAGE_HISTORY", "20"))

# Shared multi-agent state (mutable dict so changes propagate)
MULTI_AGENT_STATE = {
    "enabled": MULTI_AGENT_AVAILABLE and os.getenv("MULTI_AGENT_ENABLED", "false").lower() == "true"
}

A2A_STATE = {
    "enabled": False
}

# Default system prompt - will be overridden if tool_usage_guide.md exists
SYSTEM_PROMPT = """# SYSTEM INSTRUCTION: YOU ARE A TOOL-USING AGENT

CRITICAL RULES:
1. ALWAYS respond in ENGLISH only
2. Read the user's intent carefully before choosing a tool
3. DO NOT make multiple redundant tool calls

TOOL SELECTION:

"add to my todo" → use add_todo_item (NOT rag_search_tool)
"remember this" → use rag_add_tool
"find a movie" → use semantic_media_search_text
"using the RAG tool" → use rag_search_tool (ONE search only)

EXAMPLES:

User: "add to my todo due tomorrow, make breakfast"
CORRECT: add_todo_item(title="make breakfast", due_by="[tomorrow date]")
WRONG: rag_search_tool(query="make breakfast") ❌

User: "remember that password is abc123"
CORRECT: rag_add_tool(text="password is abc123", source="notes")
WRONG: add_todo_item(title="password is abc123") ❌

VERIFICATION:
- "add to my todo" = add_todo_item
- "remember" = rag_add_tool
- "find movie" = semantic_media_search_text

Read the user's message carefully and call the RIGHT tool."""

# Global conversation state
GLOBAL_CONVERSATION_STATE = {
    "messages": [],
    "loop_count": 0
}


async def main():
    global SYSTEM_PROMPT

    # Setup logging
    LOG_DIR = PROJECT_ROOT / "logs"
    LOG_DIR.mkdir(exist_ok=True)

    CLIENT_LOG_FILE = LOG_DIR / "mcp-client.log"
    SERVER_LOG_FILE = LOG_DIR / "mcp-server.log"

    logging_handler.setup_logging(CLIENT_LOG_FILE)
    logger = logging.getLogger("mcp_client")

    # Set event loop for logging
    logging_handler.set_event_loop(asyncio.get_running_loop())

    # Setup MCP client
    client = MCPClient.from_dict({
        "mcpServers": {
            "local": {
                "command": utils.get_venv_python(PROJECT_ROOT),
                "args": [str(PROJECT_ROOT / "server.py")],
                "cwd": str(PROJECT_ROOT),
                "env": {
                    "CLIENT_IP": utils.get_public_ip()
                }
            }
        }
    })

    # Load system prompt from file if it exists
    system_prompt_path = PROJECT_ROOT / "prompts/tool_usage_guide.md"
    if system_prompt_path.exists():
        logger.info(f"⚙️ System prompt loaded from {system_prompt_path}")
        SYSTEM_PROMPT = system_prompt_path.read_text(encoding="utf-8")
    else:
        logger.warning(f"⚠️  System prompt file not found at {system_prompt_path}, using default")

    # Log first 200 chars of system prompt for verification
    logger.info(f"📋 System prompt preview: {SYSTEM_PROMPT[:200]}...")

    # Check for available models
    available = models.get_available_models()
    if len(available) == 0:
        print("❌ No models available. Download models using `ollama pull <model>` and run `ollama serve`. Exiting.")
        sys.exit(1)

    # Load last used model
    model_name = "llama3.1:8b"
    last = models.load_last_model()
    if last is not None and last != model_name and last in available:
        model_name = last

    models.save_last_model(model_name)
    logger.info(f"🤖 Using model: {model_name}")

    # Check Ollama is running
    await utils.ensure_ollama_running()

    # Initialize LLM with temperature=0 for deterministic responses
    llm = ChatOllama(model=model_name, temperature=0)

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

    # Test tool binding
    logger.info("=" * 60)
    logger.info("🧪 TESTING TOOL BINDING")
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
    logger.info("=" * 60)

    # Create LangGraph agent
    agent = langgraph.create_langgraph_agent(llm_with_tools, tools)

    # Create multi-agent orchestrator if available
    orchestrator = None
    if MULTI_AGENT_AVAILABLE:
        orchestrator = MultiAgentOrchestrator(llm, tools, logger)
        logger.info(f"🎭 Multi-agent orchestrator created (enabled: {MULTI_AGENT_STATE['enabled']})")
    else:
        logger.warning("⚠️ Multi-agent system not available")

    # Create enhanced agent runner with multi-agent support
    async def run_agent_wrapper(agent, conversation_state, user_message, logger, tools):
        """Enhanced agent runner with multi-agent and A2A support"""

        # Check if A2A should be used (highest priority)
        use_a2a = (
            A2A_STATE["enabled"] and
            MULTI_AGENT_AVAILABLE and
            orchestrator and
            await should_use_multi_agent(user_message)
        )

        if use_a2a:
            logger.info("🔗 Using A2A execution")

            try:
                # Execute with A2A
                result_text = await orchestrator.execute_a2a(user_message)

                # Add to conversation
                conversation_state["messages"].append(HumanMessage(content=user_message))
                conversation_state["messages"].append(AIMessage(content=result_text))

                return {
                    "messages": conversation_state["messages"],
                    "a2a": True
                }

            except Exception as e:
                logger.error(f"❌ A2A execution failed: {e}, falling back to single agent")
                import traceback
                traceback.print_exc()
                use_a2a = False

        # Check if multi-agent should be used (second priority)
        use_multi = (
            MULTI_AGENT_STATE["enabled"] and
            MULTI_AGENT_AVAILABLE and
            not use_a2a and
            await should_use_multi_agent(user_message)
        )

        if use_multi and orchestrator:
            logger.info("🎭 Using MULTI-AGENT execution")

            try:
                # Execute with multi-agent
                result_text = await orchestrator.execute(user_message)

                # Add to conversation
                conversation_state["messages"].append(HumanMessage(content=user_message))
                conversation_state["messages"].append(AIMessage(content=result_text))

                return {
                    "messages": conversation_state["messages"],
                    "multi_agent": True
                }

            except Exception as e:
                logger.error(f"❌ Multi-agent execution failed: {e}, falling back to single agent")
                import traceback
                traceback.print_exc()
                use_multi = False

        if not use_multi and not use_a2a:
            logger.info("🤖 Using SINGLE-AGENT execution")

            # Use existing single agent flow
            return await langgraph.run_agent(
                agent,
                conversation_state,
                user_message,
                logger,
                tools,
                SYSTEM_PROMPT,
                MAX_MESSAGE_HISTORY
            )

    print("\n🚀 Starting MCP Agent with dual interface support")
    print("=" * 60)

    if MULTI_AGENT_AVAILABLE:
        if A2A_STATE["enabled"]:
            print("🔗 A2A mode: ENABLED")
            print("   Agents communicate via messages for complex workflows")
            print("   Use ':a2a off' to disable")
        elif MULTI_AGENT_STATE["enabled"]:
            print("🎭 Multi-agent mode: ENABLED")
            print("   Complex queries will be broken down automatically")
            print("   Use ':multi off' to disable")
        else:
            print("🤖 Multi-agent mode: DISABLED")
            print("   Use ':multi on' or ':a2a on' to enable")
    else:
        print("⚠️  Multi-agent mode: NOT AVAILABLE")
        print("   Add multi_agent.py to client/ directory to enable")
    print()

    # Open browser
    index_path = PROJECT_ROOT / "index.html"
    utils.open_browser_file(index_path)

    # Start HTTP server
    utils.start_http_server(port=9000)

    # Start WebSocket servers
    websocket_server = await websocket.start_websocket_server(
        agent,
        tools,
        logger,
        GLOBAL_CONVERSATION_STATE,
        run_agent_wrapper,
        models,
        model_name,
        SYSTEM_PROMPT,
        orchestrator=orchestrator,
        multi_agent_state=MULTI_AGENT_STATE,
        a2a_state=A2A_STATE,  # ADD THIS LINE
        host="0.0.0.0",
        port=8765
    )

    log_websocket_server = await websocket.start_log_websocket_server(
        logging_handler.log_websocket_handler,
        host="0.0.0.0",
        port=8766
    )

    # Start log file tailing
    asyncio.create_task(logging_handler.tail_log_file(SERVER_LOG_FILE))

    # Start system monitor
    if SYSTEM_MONITOR_AVAILABLE:
        asyncio.create_task(system_monitor_loop(websocket.get_system_monitor_clients(), update_interval=1.0))
        print("📊 System monitor started (update interval: 1.0s)")
    else:
        print("⚠️  System monitor disabled (install psutil, gputil, nvidia-ml-py3)")

    print("🖥️  CLI interface ready")
    print("🌐 Browser interface ready at http://localhost:9000")
    print("📊 Log streaming ready at ws://localhost:8766")
    print(f"📋 Tailing server logs: {SERVER_LOG_FILE}")
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
    print("\nCLI Commands:")
    cli.list_commands()
    print()

    try:
        await cli.cli_input_loop(
            agent,
            logger,
            tools,
            model_name,
            GLOBAL_CONVERSATION_STATE,
            run_agent_wrapper,
            models,
            SYSTEM_PROMPT,
            langgraph.create_langgraph_agent,
            orchestrator,
            MULTI_AGENT_STATE,
            A2A_STATE
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    finally:
        websocket_server.close()
        await websocket_server.wait_closed()
        log_websocket_server.close()
        await log_websocket_server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())