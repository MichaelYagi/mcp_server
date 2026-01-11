"""
LangGraph Module
Handles LangGraph agent creation, routing, and execution
"""

import json
import logging
import operator
from typing import TypedDict, Annotated, Sequence, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode


class AgentState(TypedDict):
    """State that gets passed between nodes in the graph"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    tools: dict
    llm: object
    ingest_completed: bool


def router(state):
    """Route based on what the agent decided to do"""
    last_message = state["messages"][-1]

    logger = logging.getLogger("mcp_client")
    logger.info(f"🎯 Router: Last message type = {type(last_message).__name__}")

    # Check if we just completed an ingest operation
    ingest_completed = state.get("ingest_completed", False)

    # Check if user's ORIGINAL message requested RAG (before LLM processing)
    user_message = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_message = msg
            break

    if user_message:
        content = user_message.content.lower()
        logger.info(f"🎯 Router: Checking user's original message: {content[:100]}")

        # Check for ingestion request - but only if not already completed
        if "ingest" in content and not ingest_completed:
            # Check if user wants to stop after one batch
            if any(stop_word in content for stop_word in ["stop", "then stop", "don't continue", "don't go on"]):
                logger.info(f"🎯 Router: User requested ONE-TIME ingest - routing there")
                return "ingest"
            else:
                logger.info(f"🎯 Router: User requested INGEST - routing there")
                return "ingest"
        elif "ingest" in content and ingest_completed:
            logger.info(f"🎯 Router: Ingest already completed - skipping to END")
            return "continue"

        # Check for EXPLICIT RAG requests (highest priority)
        if any(keyword in content for keyword in
               ["using rag", "use rag", "rag tool", "with rag", "search rag", "query rag"]):
            logger.info(f"🎯 Router: User explicitly requested RAG - routing there")
            return "rag"

    # If the AI made tool calls, go to tools node
    if isinstance(last_message, AIMessage):
        tool_calls = getattr(last_message, "tool_calls", [])
        logger.info(f"🎯 Router: Found {len(tool_calls)} tool calls")
        if tool_calls and len(tool_calls) > 0:
            logger.info(f"🎯 Router: Routing to TOOLS")
            return "tools"

    # Check for RAG-style questions (knowledge base queries)
    if isinstance(last_message, HumanMessage):
        content = last_message.content.lower()
        if not any(keyword in content for keyword in ["movie", "plex", "search", "find", "show", "media"]):
            if any(keyword in content for keyword in ["what is", "who is", "explain", "tell me about"]):
                logger.info(f"🎯 Router: Routing to RAG (knowledge query)")
                return "rag"

    # Default: continue with normal agent completion
    logger.info(f"🎯 Router: Continuing to END (normal completion)")
    return "continue"

async def rag_node(state):
    """Search RAG and provide context to answer the question"""
    logger = logging.getLogger("mcp_client")

    # Get the user's original question (most recent HumanMessage)
    user_message = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_message = msg
            break

    if not user_message:
        logger.error("❌ No user message found in RAG node")
        msg = AIMessage(content="Error: Could not find user's question.")
        return {"messages": state["messages"] + [msg], "llm": state.get("llm")}

    original_query = user_message.content

    # Extract the actual search terms from the query
    # Remove common RAG-related phrases to get the real question
    search_query = original_query.lower()
    for phrase in ["using the rag tool", "use the rag tool", "using rag", "use rag", "with rag",
                   "search rag for", "query rag for", "rag search for", "and my plex library",
                   "in my plex library", "from my plex library", "in my plex collection",
                   "from my plex collection"]:
        search_query = search_query.replace(phrase, "")

    search_query = search_query.strip().strip(",").strip()

    logger.info(f"🔍 RAG Node - Original query: {original_query}")
    logger.info(f"🔍 RAG Node - Cleaned search query: {search_query}")

    # Find the rag_search_tool
    tools_dict = state.get("tools", {})
    rag_search_tool = None

    # Debug: Log available tools
    available_tools = []
    for tool in tools_dict.values() if isinstance(tools_dict, dict) else tools_dict:
        if hasattr(tool, 'name'):
            available_tools.append(tool.name)
            if tool.name == "rag_search_tool":
                rag_search_tool = tool
                break

    logger.info(f"🔍 RAG Node - Available tools: {available_tools}")
    logger.info(f"🔍 RAG Node - Looking for 'rag_search_tool'")

    if not rag_search_tool:
        logger.error(f"❌ RAG search tool not found! Available: {available_tools}")
        msg = AIMessage(content=f"RAG search is not available. Available tools: {', '.join(available_tools)}")
        return {"messages": state["messages"] + [msg], "llm": state.get("llm")}

    try:
        logger.info(f"🔍 Calling rag_search_tool with query: {search_query}")
        result = await rag_search_tool.ainvoke({"query": search_query})

        logger.info(f"🔍 RAG tool result type: {type(result)}")
        logger.info(f"🔍 RAG tool result (first 200 chars): {str(result)[:200]}")

        # Handle different result types - check for actual objects first
        if isinstance(result, list) and len(result) > 0:
            # Check if it's a list of TextContent objects
            if hasattr(result[0], 'text'):
                logger.info("🔍 Detected actual TextContent object list")
                result_text = result[0].text
                try:
                    result = json.loads(result_text)
                    logger.info("✅ Successfully parsed JSON from TextContent object")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error from TextContent: {e}")
                    logger.error(f"❌ TextContent string: {result_text[:500]}")
                    msg = AIMessage(content=f"Error parsing RAG results: {str(e)}")
                    return {"messages": state["messages"] + [msg], "llm": state.get("llm")}
        elif isinstance(result, str):
            # Check if it's a string representation of TextContent
            if result.startswith("[TextContent("):
                logger.info("🔍 Detected TextContent string representation")

                # The actual JSON starts after text=' and before ', annotations
                # But we need to be very careful about finding the right boundaries
                # Look for the pattern: text='<JSON_HERE>', annotations

                try:
                    # Find where the JSON actually starts
                    json_start_marker = "text='"
                    json_start_idx = result.find(json_start_marker)

                    if json_start_idx == -1:
                        raise ValueError("Could not find text=' marker")

                    json_start_idx += len(json_start_marker)

                    # Now we need to find where it ends
                    # The JSON ends with }' followed by , annotations
                    # Look for }'<anything>, annotations
                    # Use a more robust approach: count braces

                    brace_count = 0
                    in_string = False
                    escape_next = False
                    json_end_idx = json_start_idx

                    for i in range(json_start_idx, len(result)):
                        char = result[i]

                        if escape_next:
                            escape_next = False
                            continue

                        if char == '\\':
                            escape_next = True
                            continue

                        if char == '"' and not in_string:
                            in_string = True
                        elif char == '"' and in_string:
                            in_string = False
                        elif char == '{' and not in_string:
                            brace_count += 1
                        elif char == '}' and not in_string:
                            brace_count -= 1
                            if brace_count == 0:
                                json_end_idx = i + 1
                                break

                    if json_end_idx == json_start_idx:
                        raise ValueError("Could not find end of JSON")

                    json_str = result[json_start_idx:json_end_idx]

                    # The JSON string is escaped as a Python string literal
                    # Use codecs to decode the escape sequences properly
                    import codecs
                    try:
                        # Decode Python string escapes: \n, \t, \', \", \\, etc.
                        json_str = codecs.decode(json_str, 'unicode_escape')
                    except Exception as decode_err:
                        logger.warning(f"⚠️ Codecs decode failed: {decode_err}, trying manual decode")
                        # Fallback to manual replacement if codecs fails
                        json_str = json_str.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                        json_str = json_str.replace('\\\\', '\\').replace('\\"', '"')

                    logger.info(f"🔍 Extracted JSON (first 100 chars): {json_str[:100]}")

                    result = json.loads(json_str)
                    logger.info("✅ Successfully parsed JSON from TextContent string")

                except (ValueError, json.JSONDecodeError) as e:
                    logger.error(f"❌ Error parsing TextContent: {e}")
                    logger.error(f"❌ Result sample: {result[:500]}")
                    msg = AIMessage(content=f"Error parsing RAG results: {str(e)}")
                    return {"messages": state["messages"] + [msg], "llm": state.get("llm")}
            else:
                # Regular JSON string
                try:
                    result = json.loads(result)
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error: {e}")
                    logger.error(f"❌ Result string: {result[:500]}")
                    msg = AIMessage(content=f"Error parsing RAG results: {str(e)}")
                    return {"messages": state["messages"] + [msg], "llm": state.get("llm")}

        chunks = []
        if isinstance(result, dict):
            results_list = result.get("results", [])
            chunks = [item.get("text", "") for item in results_list if isinstance(item, dict)]
            logger.info(f"✅ Extracted {len(chunks)} chunks from RAG results")

            # Log a preview of the chunks
            for i, chunk in enumerate(chunks[:3]):
                logger.info(f"📄 Chunk {i+1} preview: {chunk[:150]}...")

        if not chunks:
            logger.warning("⚠️ No chunks found in RAG results")
            msg = AIMessage(content="I couldn't find any relevant information in the knowledge base for your query.")
            return {"messages": state["messages"] + [msg], "llm": state.get("llm")}

        # Take top 3 chunks
        context = "\n\n---\n\n".join(chunks[:3])
        logger.info(f"📄 Using top {min(3, len(chunks))} chunks as context")

        # Build augmented prompt with balanced constraints
        augmented_messages = state["messages"][:-1] + [
            SystemMessage(content=f"""You are a helpful assistant answering questions based on retrieved information.

Here is the relevant context from the knowledge base:

{context}

Instructions:
- Use the context above to answer the user's question
- If the context contains relevant information, use it to provide a helpful answer
- If the context doesn't contain enough information to answer fully, say what you can determine from the context and note what's missing
- Be specific and reference details from the context when possible
- Do not invent information that isn't in the context"""),
            user_message  # Use the original user message
        ]

        llm = state.get("llm")
        logger.info(f"🔍 LLM from state: type={type(llm)}, value={llm}")

        if not llm or not hasattr(llm, 'ainvoke'):
            logger.warning("⚠️ LLM not provided or invalid in state, creating new instance")
            from langchain_ollama import ChatOllama
            llm = ChatOllama(model="llama3.1:8b", temperature=0)
            logger.info("📝 Created new LLM instance for RAG")

        logger.info("🧠 Calling LLM with RAG context")
        response = await llm.ainvoke(augmented_messages)
        logger.info(f"✅ RAG response generated: {response.content[:100]}...")

        return {"messages": state["messages"] + [response], "llm": state.get("llm")}

    except Exception as e:
        logger = logging.getLogger("mcp_client")
        logger.error(f"❌ Error in RAG node: {e}")
        msg = AIMessage(content=f"Error searching knowledge base: {str(e)}")
        return {"messages": state["messages"] + [msg], "llm": state.get("llm")}


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
            # Log the FULL response content
            content = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"🔧 No tool calls. Full response: {content}")  # Changed from [:200]

        if hasattr(response, 'content'):
            if not response.content or not response.content.strip():
                logger.info("⚠️ LLM returned empty content (may have tool_calls)")

        return {
            "messages": messages + [response],
            "tools": state.get("tools", {}),
            "llm": state.get("llm"),
            "ingest_completed": state.get("ingest_completed", False),
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
                "llm": state.get("llm"),
                "ingest_completed": state.get("ingest_completed", False),
            }

        try:
            logger.info("📥 Starting ingest operation...")
            limit = 5  # default
            messages = state["messages"]

            # Find the most recent AIMessage with tool_calls
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        if tool_call.get('name') == 'plex_ingest_batch':
                            args = tool_call.get('args', {})
                            limit = args.get('limit', 5)
                            logger.info(f"📥 Using limit={limit} from LLM tool call")
                            break
                    break

            logger.info(f"📥 Starting ingest operation with limit={limit}...")
            result = await ingest_tool.ainvoke({"limit": limit})

            logger.info(f"🔍 Raw result type: {type(result)}")
            logger.info(f"🔍 Raw result: {result}")

            if isinstance(result, list) and len(result) > 0:
                if hasattr(result[0], 'text'):
                    logger.info("🔍 Detected TextContent object in list")
                    result = result[0].text
                    logger.info(f"🔍 Extracted text from object, length: {len(result)}")

            if isinstance(result, str) and result.startswith('[TextContent('):
                logger.info("🔍 Detected TextContent string, extracting...")
                import re

                # More robust extraction that handles escaped quotes
                # Look for text=' and then find the matching ', taking into account escaping
                start_marker = "text='"
                start_idx = result.find(start_marker)

                if start_idx != -1:
                    start_idx += len(start_marker)

                    # Now find the closing quote, accounting for escape sequences
                    # We need to find ', annotations= or ', type=
                    end_markers = ["', annotations=", "', type="]
                    end_idx = -1

                    for marker in end_markers:
                        idx = result.find(marker, start_idx)
                        if idx != -1:
                            if end_idx == -1 or idx < end_idx:
                                end_idx = idx

                    if end_idx != -1:
                        json_str = result[start_idx:end_idx]

                        # Decode escape sequences
                        import codecs
                        try:
                            json_str = codecs.decode(json_str, 'unicode_escape')
                        except Exception as decode_err:
                            logger.warning(f"⚠️ Codecs decode failed: {decode_err}, trying manual decode")
                            json_str = json_str.replace('\\n', '\n').replace('\\t', '\t')
                            json_str = json_str.replace('\\\\', '\\').replace("\\'", "'").replace('\\"', '"')

                        result = json_str
                        logger.info(f"🔍 Extracted text, length: {len(result)}")
                    else:
                        logger.error(f"❌ Could not find end marker in TextContent")
                        logger.error(f"❌ First 500 chars: {result[:500]}")
                else:
                    logger.error(f"❌ Could not find start marker in TextContent")
                    logger.error(f"❌ First 500 chars: {result[:500]}")

            if isinstance(result, str):
                # Check if it's a TextContent string
                if result.startswith('[TextContent('):
                    logger.info("🔍 Detected TextContent string, extracting...")
                    import re
                    match = re.search(r"text='([^']*(?:\\'[^']*)*)'", result)
                    if match:
                        result = match.group(1).replace("\\'", "'").replace("\\n", "\n")
                        logger.info(f"🔍 Extracted text, length: {len(result)}")
                    else:
                        logger.error(f"❌ Could not extract text from TextContent")
                        logger.error(f"❌ First 500 chars: {result[:500]}")

                # Now try to parse as JSON
                try:
                    result = json.loads(result)
                    logger.info(f"✅ Successfully parsed JSON result")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error: {e}")
                    logger.error(f"❌ Result type: {type(result)}")
                    logger.error(f"❌ Result length: {len(result) if isinstance(result, str) else 'N/A'}")
                    logger.error(f"❌ First 1000 chars of result: {str(result)[:1000]}")

                    msg = AIMessage(
                        content=f"Error: Could not parse ingestion result (length: {len(result)} chars). Check logs for details.")
                    return {
                        "messages": state["messages"] + [msg],
                        "tools": state.get("tools", {}),
                        "llm": state.get("llm"),
                        "ingest_completed": True,
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
                                f"📊 **Remaining to ingest:** {remaining}\n\n"
                                f"Ingestion complete. You can now search this content using the RAG tool."
                    )
                else:
                    msg = AIMessage(
                        content=f"✅ All items already ingested.\n\n📊 **Total items in RAG:** {total_ingested}"
                    )

            logger.info("✅ Ingest operation completed successfully")

        except Exception as e:
            logger.error(f"❌ Error in ingest_node: {e}")
            import traceback
            traceback.print_exc()
            msg = AIMessage(content=f"Ingestion failed: {str(e)}")

        return {
            "messages": state["messages"] + [msg],
            "tools": state.get("tools", {}),
            "llm": state.get("llm"),
            "ingest_completed": True,  # Mark as completed
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
            "continue": END  # Changed from "agent": END to avoid confusion
        }
    )

    workflow.add_edge("tools", "agent")
    workflow.add_edge("ingest", END)
    workflow.add_edge("rag", END)

    app = workflow.compile()
    logger.info("✅ LangGraph agent compiled successfully")

    return app


async def run_agent(agent, conversation_state, user_message, logger, tools, system_prompt, llm=None, max_history=20):
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

        # Initialize with system message if needed
        if not conversation_state["messages"]:
            conversation_state["messages"].append(
                SystemMessage(content=system_prompt)
            )

        # Add the new user message
        conversation_state["messages"].append(
            HumanMessage(content=user_message)
        )

        # Trim history BEFORE invoking agent
        conversation_state["messages"] = conversation_state["messages"][-max_history:]

        # Ensure system message is at the start after trimming
        if not isinstance(conversation_state["messages"][0], SystemMessage):
            conversation_state["messages"].insert(0, SystemMessage(content=system_prompt))

        logger.info(f"🧠 Starting agent with {len(conversation_state['messages'])} messages")

        tool_registry = {tool.name: tool for tool in tools}

        # Invoke the agent
        result = await agent.ainvoke({
            "messages": conversation_state["messages"],
            "tools": tool_registry,
            "llm": llm,
            "ingest_completed": False
        })

        new_messages = result["messages"][len(conversation_state["messages"]):]
        logger.info(f"📨 Agent added {len(new_messages)} new messages")
        conversation_state["messages"].extend(new_messages)

        # Reset loop count
        conversation_state["loop_count"] = 0

        # Debug: Log final state
        logger.info(f"📨 Final conversation has {len(conversation_state['messages'])} messages")
        for i, msg in enumerate(conversation_state['messages'][-5:]):  # Only log last 5
            msg_type = type(msg).__name__
            content_preview = msg.content[:100] if hasattr(msg, 'content') else str(msg)[:100]
            logger.info(f"  [-{5 - i}] {msg_type}: {content_preview}")

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