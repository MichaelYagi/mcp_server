"""
LangGraph Module
Handles LangGraph agent creation, routing, and execution
"""

import json
import logging
import operator
from typing import TypedDict, Annotated, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode


class AgentState(TypedDict):
    """State that gets passed between nodes in the graph"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    tools: dict


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


def create_langgraph_agent(llm_with_tools, tools):
    """Create and compile the LangGraph agent"""
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


async def run_agent(agent, conversation_state, user_message, logger, tools, system_prompt, max_history=20):
    """Execute the agent with the given user message"""
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
                SystemMessage(content=system_prompt)
            )

        conversation_state["messages"].append(
            HumanMessage(content=user_message)
        )

        conversation_state["messages"] = conversation_state["messages"][-max_history:]

        if not isinstance(conversation_state["messages"][0], SystemMessage):
            conversation_state["messages"].insert(0, SystemMessage(content=system_prompt))

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