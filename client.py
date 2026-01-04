import asyncio
import os
import logging
import requests
import operator
from pathlib import Path
from typing import TypedDict, Annotated, Sequence

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import (
    SystemMessage,
    ToolMessage,
    BaseMessage,
    HumanMessage,
    AIMessage,
)
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from mcp_use.client.client import MCPClient
from mcp_use.agents.mcpagent import MCPAgent

from prompts.prompts import (
    INTENT_DETECTOR_PROMPT,
    SUMMARIZE_TOOL_RESULT_PROMPT,
    DIRECT_ANSWER_PROMPT,
    AGENT_PROMPT,
)

# ============================================================================
# Environment Setup
# ============================================================================

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

# ============================================================================
# LangGraph State Definition
# ============================================================================

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

# ============================================================================
# Helper: Summarize Tool Output
# ============================================================================

async def summarize_tool_result(llm, system_prompt, tool_text):
    prompt = SUMMARIZE_TOOL_RESULT_PROMPT.format(metrics=tool_text)
    messages = [SystemMessage(content=prompt)]
    response = await llm.ainvoke(messages)
    return response.content

# ============================================================================
# Helper: Detect Tool Intent
# ============================================================================

async def detect_tool_intent(llm, query: str) -> bool:
    messages = [
        SystemMessage(content=INTENT_DETECTOR_PROMPT),
        HumanMessage(content=query),
    ]
    resp = await llm.ainvoke(messages)
    return resp.content.strip().lower() == "tools"

# ============================================================================
# LangGraph Stop Condition
# ============================================================================

def should_continue(state: AgentState) -> str:
    logger = logging.getLogger("mcp_use")
    messages = state["messages"]
    last = messages[-1]

    # Stop if tool result arrived
    if isinstance(last, ToolMessage):
        logger.info("🛑 Last message is a ToolMessage — stopping to avoid loop")
        return "end"

    # Loop guard
    tool_call_turns = sum(
        1 for m in messages
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None)
    )
    if tool_call_turns > 5:
        logger.warning("⚠️ Max tool-calling turns reached. Stopping.")
        return "end"

    # Continue if LLM requested tool calls
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        logger.info(f"🔄 Continuing - found {len(last.tool_calls)} tool call(s)")
        return "continue"

    logger.info("✅ Stopping - no more tool calls, returning final answer")
    return "end"

# ============================================================================
# LangGraph Agent Builder
# ============================================================================

def create_langgraph_agent(llm_for_query, tools_for_query):
    logger = logging.getLogger("mcp_use")

    async def call_model(state: AgentState):
        messages = state["messages"]
        logger.info(f"🧠 Calling LLM with {len(messages)} messages")

        # Do not call LLM again after tool result
        if isinstance(messages[-1], ToolMessage):
            logger.info("🛑 ToolMessage detected — not calling LLM again")
            return {"messages": messages}

        response = await llm_for_query.ainvoke(messages)
        return {"messages": list(messages) + [response]}

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools_for_query))

    workflow.set_entry_point("agent")

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"continue": "tools", "end": END},
    )

    workflow.add_edge("tools", "agent")

    app = workflow.compile()
    logger.info("✅ LangGraph agent compiled successfully")
    return app

# ============================================================================
# Misc Helpers
# ============================================================================

def get_public_ip():
    try:
        return requests.get("https://api.ipify.org").text
    except Exception:
        return None

def get_venv_python(project_root: Path) -> str:
    candidates = [
        project_root / ".venv" / "bin" / "python",
        project_root / ".venv-wsl" / "bin" / "python",
        project_root / ".venv" / "Scripts" / "python.exe",
        project_root / ".venv" / "Scripts" / "python",
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    raise FileNotFoundError("No valid Python executable found.")

# ============================================================================
# Main Function
# ============================================================================

async def main():
    load_dotenv()

    # Logging setup
    LOG_DIR = PROJECT_ROOT / "logs"
    LOG_DIR.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / "mcp-client.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    logger = logging.getLogger("mcp_use")

    # MCP Server config
    client = MCPClient.from_dict({
        "mcpServers": {
            "local": {
                "command": get_venv_python(PROJECT_ROOT),
                "args": [str(PROJECT_ROOT / "server.py")],
                "cwd": str(PROJECT_ROOT),
                "env": {"CLIENT_IP": get_public_ip()},
            }
        }
    })

    # Load system prompt
    SYSTEM_PROMPT_PATH = PROJECT_ROOT / "prompts/tool_usage_guide.md"
    SYSTEM_PROMPT = (
        SYSTEM_PROMPT_PATH.read_text()
        if SYSTEM_PROMPT_PATH.exists()
        else AGENT_PROMPT
    )

    # LLM setup
    model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    logger.info(f"🤖 Using model: {model_name}")
    llm = ChatOllama(model=model_name, temperature=0)

    # MCP Agent
    mcp_agent = MCPAgent(
        llm=llm,
        client=client,
        max_steps=10,
        system_prompt=SYSTEM_PROMPT,
    )
    mcp_agent.debug = True
    await mcp_agent.initialize()

    tools = mcp_agent._tools

    logger.info(f"🛠 Found {len(tools)} MCP tools:")
    for t in tools:
        logger.info(f"  - {t.name}: {t.description}")

    print("\n✅ MCP Agent ready with LangGraph. Type a prompt (Ctrl+C to exit).\n")

    # Interactive loop
    while True:
        try:
            query = input("> ").strip()
            if not query:
                continue

            logger.info(f"💬 Received query: '{query}'")

            # Tool intent detection
            tools_enabled = await detect_tool_intent(llm, query)

            if tools_enabled:
                logger.info("🛠 Tools enabled")
                llm_for_query = llm.bind_tools(tools)
                tools_for_query = tools
                system_prompt = SYSTEM_PROMPT
            else:
                logger.info("🛑 Tools disabled")
                llm_for_query = llm
                tools_for_query = []
                system_prompt = DIRECT_ANSWER_PROMPT

            agent = create_langgraph_agent(llm_for_query, tools_for_query)

            initial_messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=query),
            ]

            result = await agent.ainvoke({"messages": initial_messages}, config={"recursion_limit": 50})

            messages = result["messages"]
            final_message = messages[-1]

            # Extract tool output
            def extract_tool_text(msg: ToolMessage) -> str:
                content = msg.content
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    return "\n".join(
                        getattr(part, "text", str(part)) for part in content
                    )
                return str(content)

            # Final answer selection
            if isinstance(final_message, AIMessage) and not getattr(final_message, "tool_calls", None):
                answer = final_message.content
            else:
                tool_msgs = [m for m in messages if isinstance(m, ToolMessage)]
                if tool_msgs:
                    raw_tool_text = extract_tool_text(tool_msgs[-1])
                    answer = await summarize_tool_result(llm, SYSTEM_PROMPT, raw_tool_text)
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

# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    asyncio.run(main())
