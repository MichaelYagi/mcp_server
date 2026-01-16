"""
LangGraph Module with Metrics Tracking AND STOP SIGNAL HANDLING
Handles LangGraph agent creation, routing, and execution with performance metrics
"""

import json
import logging
import operator
import time
from typing import TypedDict, Annotated, Sequence
from .stop_signal import is_stop_requested, clear_stop
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# Try to import metrics, but don't fail if not available
try:
    from metrics import metrics
    METRICS_AVAILABLE = True
except ImportError:
    try:
        from client.metrics import metrics
        METRICS_AVAILABLE = True
    except ImportError:
        METRICS_AVAILABLE = False
        # Create dummy metrics if not available
        from collections import defaultdict
        metrics = {
            "agent_runs": 0,
            "agent_errors": 0,
            "agent_times": [],
            "llm_calls": 0,
            "llm_errors": 0,
            "llm_times": [],
            "tool_calls": defaultdict(int),
            "tool_errors": defaultdict(int),
            "tool_times": defaultdict(list),
        }


class AgentState(TypedDict):
    """State that gets passed between nodes in the graph"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    tools: dict
    llm: object
    ingest_completed: bool
    stopped: bool  # NEW: Track if execution was stopped


def router(state):
    """
    Route based on what the agent decided to do
    NOW WITH STOP SIGNAL HANDLING AND A2A COMPLETION CHECK
    """
    last_message = state["messages"][-1]

    logger = logging.getLogger("mcp_client")
    logger.debug(f"🎯 Router: Last message type = {type(last_message).__name__}")

    # ═══════════════════════════════════════════════════════════
    # PRIORITY CHECK: Stop signal (highest priority)
    # ═══════════════════════════════════════════════════════════
    if is_stop_requested():
        logger.warning(f"🛑 Router: Stop requested - ending graph execution")
        # Mark state as stopped
        state["stopped"] = True
        return "continue"  # Go to END

    # Check if already marked as stopped in state
    if state.get("stopped", False):
        logger.warning(f"🛑 Router: Execution already stopped - ending")
        return "continue"

    # ═══════════════════════════════════════════════════════════
    # A2A COMPLETION CHECK: Stop after A2A tool result
    # ═══════════════════════════════════════════════════════════
    if len(state["messages"]) >= 2:
        # Check if second-to-last message was an AI message with send_a2a tool call
        second_last = state["messages"][-2]
        if isinstance(second_last, AIMessage) and hasattr(second_last, "tool_calls"):
            for tc in second_last.tool_calls:
                if tc.get("name") in ["send_a2a", "discover_a2a"]:
                    # Last message should be the tool result
                    from langchain_core.messages import ToolMessage
                    if isinstance(last_message, ToolMessage):
                        logger.info("🛑 Router: A2A tool result received - ending execution")
                        return "continue"  # Go to END

    # If LLM made tool calls, execute them first
    if isinstance(last_message, AIMessage):
        tool_calls = getattr(last_message, "tool_calls", [])
        if tool_calls and len(tool_calls) > 0:
            logger.debug(f"🎯 Router: Found {len(tool_calls)} tool calls - routing to TOOLS")
            return "tools"

    # Detect tool result messages
    if isinstance(last_message, AIMessage):
        if hasattr(last_message, "tool_call_id"):
            # This is a tool RESULT, not a tool call
            logger.info("🛑 Router: Tool result detected - stopping")
            return "continue"

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
        logger.debug(f"🎯 Router: Checking user's original message: {content[:100]}")

        # A2A explicit routing - ONLY route TO tools if not already executed
        if isinstance(user_message, HumanMessage):
            if "send_a2a" in content or "discover_a2a" in content:
                # Check if we already have a ToolMessage for send_a2a/discover_a2a
                has_a2a_result = False
                from langchain_core.messages import ToolMessage
                for msg in reversed(state["messages"]):
                    if isinstance(msg, ToolMessage) and hasattr(msg, 'name'):
                        if msg.name in ["send_a2a", "discover_a2a"]:
                            has_a2a_result = True
                            logger.info("🛑 Router: A2A already executed - ending")
                            break

                if not has_a2a_result:
                    logger.info("🎯 Router: Explicit A2A request detected - routing to tools")
                    return "tools"
                else:
                    return "continue"

        # Check for ingestion request - but only if not already completed
        if "ingest" in content and not ingest_completed:
            # Check if user wants to stop after one batch
            if any(stop_word in content for stop_word in ["stop", "then stop", "don't continue", "don't go on"]):
                logger.info(f"🎯 Router: User requested ONE-TIME ingest - routing there")
                return "ingest"

            # Check if this is a multi-step query
            # Multi-step indicators: "and then", "then", "first...then", etc.
            multi_step_indicators = [
                " and then ", " then ", " after that ", " next ",
                "first", "research.*analyze", "find.*summarize",
                "analyze", "create", "summary", "report"
            ]

            import re
            has_multiple_steps = any(re.search(indicator, content.lower()) for indicator in multi_step_indicators)

            if has_multiple_steps:
                logger.info(f"🎯 Router: INGEST detected with multiple steps - using MULTI-AGENT")
                return "continue"  # Let normal flow handle multi-agent
            else:
                logger.info(f"🎯 Router: User requested INGEST (simple) - routing there")
                return "ingest"  # Simple ingest, use single-agent

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
        logger.debug(f"🎯 Router: Found {len(tool_calls)} tool calls")
        if tool_calls and len(tool_calls) > 0:
            logger.debug(f"🎯 Router: Routing to TOOLS")
            return "tools"

    # Detect tool result messages
    if isinstance(last_message, AIMessage):
        if hasattr(last_message, "tool_call_id"):
            # This is a tool RESULT, not a tool call
            logger.info("🛑 Router: Tool result detected - stopping")
            return "continue"

    # Check for RAG-style questions (knowledge base queries)
    if isinstance(last_message, HumanMessage):
        content = last_message.content.lower()
        if not any(keyword in content for keyword in ["movie", "plex", "search", "find", "show", "media"]):
            if any(keyword in content for keyword in ["what is", "who is", "explain", "tell me about"]):
                logger.info(f"🎯 Router: Routing to RAG (knowledge query)")
                return "rag"

    # Default: continue with normal agent completion
    logger.debug(f"🎯 Router: Continuing to END (normal completion)")
    return "continue"

async def rag_node(state):
    """
    Search RAG and provide context to answer the question
    NOW WITH STOP SIGNAL CHECK
    """
    logger = logging.getLogger("mcp_client")

    # Check stop signal first
    if is_stop_requested():
        logger.warning("🛑 RAG node: Stop requested - skipping RAG search")
        msg = AIMessage(content="Search cancelled by user.")
        return {
            "messages": state["messages"] + [msg],
            "llm": state.get("llm"),
            "stopped": True
        }

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

        # Track tool call timing
        tool_start = time.time()
        result = await rag_search_tool.ainvoke({"query": search_query})
        tool_duration = time.time() - tool_start

        if METRICS_AVAILABLE:
            metrics["tool_calls"]["rag_search_tool"] += 1
            metrics["tool_times"]["rag_search_tool"].append((time.time(), tool_duration))
            logger.info(f"📊 Tracked rag_search_tool: {tool_duration:.2f}s")

        logger.info(f"🔍 RAG tool result type: {type(result)}")
        logger.debug(f"🔍 RAG tool result (first 200 chars): {str(result)[:200]}")

        # Handle different result types
        if isinstance(result, list) and len(result) > 0:
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
            if result.startswith("[TextContent("):
                logger.info("🔍 Detected TextContent string representation")

                try:
                    json_start_marker = "text='"
                    json_start_idx = result.find(json_start_marker)

                    if json_start_idx == -1:
                        raise ValueError("Could not find text=' marker")

                    json_start_idx += len(json_start_marker)

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

                    import codecs
                    try:
                        json_str = codecs.decode(json_str, 'unicode_escape')
                    except Exception as decode_err:
                        logger.warning(f"⚠️ Codecs decode failed: {decode_err}, trying manual decode")
                        json_str = json_str.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                        json_str = json_str.replace('\\\\', '\\').replace('\\"', '"')

                    logger.debug(f"🔍 Extracted JSON (first 100 chars): {json_str[:100]}")

                    result = json.loads(json_str)
                    logger.info("✅ Successfully parsed JSON from TextContent string")

                except (ValueError, json.JSONDecodeError) as e:
                    logger.error(f"❌ Error parsing TextContent: {e}")
                    logger.error(f"❌ Result sample: {result[:500]}")
                    msg = AIMessage(content=f"Error parsing RAG results: {str(e)}")
                    return {"messages": state["messages"] + [msg], "llm": state.get("llm")}
            else:
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

            for i, chunk in enumerate(chunks[:3]):
                logger.debug(f"📄 Chunk {i+1} preview: {chunk[:150]}...")

        if not chunks:
            logger.warning("⚠️ No chunks found in RAG results")
            msg = AIMessage(content="I couldn't find any relevant information in the knowledge base for your query.")
            return {"messages": state["messages"] + [msg], "llm": state.get("llm")}

        # Take top 3 chunks
        context = "\n\n---\n\n".join(chunks[:3])
        logger.info(f"📄 Using top 3 chunks as context")

        # DIAGNOSTIC: Log what we're sending
        logger.debug("=" * 80)
        logger.debug("🔍 CONTEXT BEING SENT TO LLM:")
        logger.debug("=" * 80)
        logger.debug(context[:1500])
        if len(context) > 1500:
            logger.debug(f"... (truncated, total: {len(context)} chars)")
        logger.debug("=" * 80)

        # Create fresh conversation with ONLY the context
        augmented_messages = [
            SystemMessage(content=f"""You are answering a question about movies in a user's Plex library.

The library has already been searched. Here are the ACTUAL RESULTS:

{context}

Your job: Answer the question using ONLY the movies listed above.

CORRECT response format:
"Based on your Plex library, here are movies that match:

1. [Title from results above] ([Year]) - [Brief description from results]
2. [Title from results above] ([Year]) - [Brief description from results]

etc."

WRONG responses:
- Suggesting to use tools (the search already happened!)
- Mentioning movies not in the results above
- Saying "let's search" or "we can use"

The movies shown above ARE the search results. Just present them."""),
            user_message
        ]

        llm = state.get("llm")
        logger.debug(f"🔍 LLM from state: type={type(llm)}, value={llm}")

        if not llm or not hasattr(llm, 'ainvoke'):
            logger.warning("⚠️ LLM not provided or invalid in state, creating new instance")
            from langchain_ollama import ChatOllama
            llm = ChatOllama(model="llama3.1:8b", temperature=0)
            logger.info("📝 Created new LLM instance for RAG")

        logger.info("🧠 Calling LLM with RAG context")

        # Track LLM call for RAG
        llm_start = time.time()
        response = await llm.ainvoke(augmented_messages)
        llm_duration = time.time() - llm_start

        if METRICS_AVAILABLE:
            metrics["llm_calls"] += 1
            metrics["llm_times"].append((time.time(), llm_duration))

        logger.info(f"✅ RAG response generated: {response.content[:100]}...")

        return {"messages": state["messages"] + [response], "llm": state.get("llm")}

    except Exception as e:
        logger.error(f"❌ Error in RAG node: {e}")
        if METRICS_AVAILABLE:
            metrics["tool_errors"]["rag_search_tool"] += 1
        msg = AIMessage(content=f"Error searching knowledge base: {str(e)}")
        return {"messages": state["messages"] + [msg], "llm": state.get("llm")}


def filter_tools_by_intent(user_message: str, all_tools: list) -> list:
    """
    Filter tools based on user intent to reduce confusion.
    Only show the LLM the tools relevant to the current request.
    """
    user_message_lower = user_message.lower()
    logger = logging.getLogger("mcp_client")

    # Developer override: explicit tool name
    if "send_a2a" in user_message_lower:
        logger.info("🎯 Explicit A2A override: send_a2a")
        return [t for t in all_tools if t.name == "send_a2a"]

    if "discover_a2a" in user_message_lower:
        logger.info("🎯 Explicit A2A override: discover_a2a")
        return [t for t in all_tools if t.name == "discover_a2a"]

    a2a_keywords = [
        "send to remote",
        "ask the remote agent",
        "use a2a",
        "using a2a",
        "call the remote agent",
        "ask the other agent"
    ]

    if any(keyword in user_message_lower for keyword in a2a_keywords):
        logger.info("🎯 Detected A2A intent")
        return [t for t in all_tools if t.name in ["send_a2a", "discover_a2a"]]

    # To-do/task keywords - COMPREHENSIVE LIST
    todo_keywords = [
        # Adding
        "add to my todo", "add to my tasks", "remind me to", "i need to", "don't forget",
        "create a todo", "create a task", "new todo", "new task",

        # Viewing/Listing
        "todo list", "my todos", "my tasks", "task list", "what do i need to do",
        "show my todos", "list my todos", "show my tasks", "what's in my todo",
        "what's on my todo", "check my todos", "view my todos", "see my todos",
        "display todos", "display tasks", "show tasks", "list tasks",

        # Status-specific
        "incomplete todos", "non complete todos", "unfinished todos", "open todos",
        "pending todos", "active todos", "incomplete tasks", "unfinished tasks",
        "open tasks", "pending tasks", "active tasks",

        # Searching
        "find todos", "search todos", "find tasks", "search tasks",
        "todos about", "tasks about", "todos for", "tasks for",

        # Updating
        "update todo", "update task", "change todo", "modify todo",
        "mark as complete", "mark as done", "complete todo", "finish todo",

        # Deleting
        "delete todo", "remove todo", "delete task", "remove task",
        "clear todos", "clear tasks"
    ]

    if any(keyword in user_message_lower for keyword in todo_keywords):
        logger.info("🎯 Detected TODO intent")
        return [t for t in all_tools if t.name in [
            "add_todo_item", "list_todo_items", "search_todo_items",
            "update_todo_item", "delete_todo_item", "delete_all_todo_items"
        ]]

    # Note/memory keywords
    note_keywords = [
        "remember", "save this", "make a note", "write down", "store this",
        "note that", "keep track of", "record this", "jot down",
        "save note", "add note", "create note"
    ]

    if any(keyword in user_message_lower for keyword in note_keywords):
        logger.info("🎯 Detected MEMORY/NOTE intent")
        return [t for t in all_tools if t.name in [
            "rag_add_tool", "add_entry", "list_entries", "get_entry", "search_entries"
        ]]

    # RAG search keywords
    rag_search_keywords = [
        "using the rag tool", "search my notes", "what do i know about",
        "find information", "search for information", "look up in notes",
        "what did i save about", "search notes", "find in notes"
    ]

    if any(keyword in user_message_lower for keyword in rag_search_keywords):
        logger.info("🎯 Detected RAG SEARCH intent")
        return [t for t in all_tools if t.name in [
            "rag_search_tool", "search_entries", "search_semantic", "search_by_tag"
        ]]

    # PLEX INGESTION keywords
    ingest_keywords = [
        "ingest", "ingest from plex", "ingest plex", "process subtitles",
        "add to rag", "ingest items", "ingest next", "ingest from my plex",
        "process plex", "add plex to rag"
    ]

    if any(keyword in user_message_lower for keyword in ingest_keywords):
        logger.info("🎯 Detected PLEX INGEST intent")
        return [t for t in all_tools if t.name in [
            "plex_find_unprocessed", "plex_ingest_items",
            "plex_ingest_single", "plex_ingest_batch",
            "plex_get_stats", "rag_search_tool",
        ]]

    # Media/Plex keywords
    media_keywords = [
        "find movie", "find movies", "search plex", "what movies", "show me",
        "movies about", "films about", "search for movie", "look for movie",
        "search media", "find film", "find films"
    ]

    if any(keyword in user_message_lower for keyword in media_keywords):
        logger.info("🎯 Detected MEDIA search intent")
        return [t for t in all_tools if t.name in [
            "semantic_media_search_text", "scene_locator_tool", "find_scene_by_title"
        ]]

    # Weather keywords
    if any(keyword in user_message_lower for keyword in ["weather", "temperature", "forecast"]):
        logger.info("🎯 Detected WEATHER intent")
        return [t for t in all_tools if t.name in [
            "get_weather_tool", "get_location_tool"
        ]]

    # System/hardware keywords
    if any(keyword in user_message_lower for keyword in [
        "system", "hardware", "cpu", "gpu", "memory", "processes", "specs"
    ]):
        logger.info("🎯 Detected SYSTEM intent")
        return [t for t in all_tools if t.name in [
            "get_hardware_specs_tool", "get_system_info", "list_system_processes", "terminate_process"
        ]]

    # Default: return all tools but log warning
    logger.warning(f"🎯 No specific intent detected for: '{user_message}' - using all {len(all_tools)} tools")
    return all_tools


def create_langgraph_agent(llm_with_tools, tools):
    """Create and compile the LangGraph agent"""
    logger = logging.getLogger("mcp_client")

    # IMPORTANT: Store the base LLM (without tools) for dynamic binding
    # llm_with_tools is a RunnableBinding, we need the underlying LLM
    base_llm = llm_with_tools.bound if hasattr(llm_with_tools, 'bound') else llm_with_tools

    async def call_model(state: AgentState):
        # Check stop signal first
        if is_stop_requested():
            logger.warning("🛑 call_model: Stop requested - returning empty response")
            empty_response = AIMessage(content="Operation cancelled by user.")
            return {
                "messages": state["messages"] + [empty_response],
                "tools": state.get("tools", {}),
                "llm": state.get("llm"),
                "ingest_completed": state.get("ingest_completed", False),
                "stopped": True
            }

        messages = state["messages"]

        # Get user's original message for tool filtering
        user_message = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_message = msg.content
                break

        # Filter tools based on user intent
        if user_message:
            # Get all available tools from state
            all_tools = list(state.get("tools", {}).values())
            filtered_tools = filter_tools_by_intent(user_message, all_tools)
            tool_names = [t.name for t in filtered_tools]
            logger.info(f"🎯 Filtered to {len(filtered_tools)} relevant tools: {tool_names}")

            # Bind the filtered tools to the BASE LLM
            llm_to_use = base_llm.bind_tools(filtered_tools)
        else:
            # No user message, use all tools
            llm_to_use = llm_with_tools

        # If the last message is a tool result, do NOT filter tools again
        if isinstance(messages[-1], AIMessage) and hasattr(messages[-1], "tool_call_id"):
            llm_to_use = llm_with_tools

        logger.info(f"🧠 Calling LLM with {len(messages)} messages")

        start_time = time.time()
        try:
            response = await llm_to_use.ainvoke(messages)
            duration = time.time() - start_time

            # Track LLM metrics
            if METRICS_AVAILABLE:
                metrics["llm_calls"] += 1
                metrics["llm_times"].append((time.time(), duration))

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
                content = response.content if hasattr(response, 'content') else str(response)
                logger.debug(f"🔧 No tool calls. Full response: {content}")

            if hasattr(response, 'content'):
                if not response.content or not response.content.strip():
                    logger.info("⚠️ LLM returned empty content (may have tool_calls)")

            return {
                "messages": messages + [response],
                "tools": state.get("tools", {}),
                "llm": state.get("llm"),
                "ingest_completed": state.get("ingest_completed", False),
                "stopped": state.get("stopped", False)
            }
        except Exception as e:
            duration = time.time() - start_time
            if METRICS_AVAILABLE:
                metrics["llm_errors"] += 1
                metrics["llm_times"].append((time.time(), duration))
            logger.error(f"❌ Model call failed after {duration:.2f}s: {e}")
            raise

    async def ingest_node(state: AgentState):
        # Check stop signal first
        if is_stop_requested():
            logger.warning("🛑 ingest_node: Stop requested - skipping ingestion")
            msg = AIMessage(content="Ingestion cancelled by user.")
            return {
                "messages": state["messages"] + [msg],
                "tools": state.get("tools", {}),
                "llm": state.get("llm"),
                "ingest_completed": True,
                "stopped": True
            }

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
                "ingest_completed": True,
                "stopped": False
            }

        try:
            logger.info("📥 Starting ingest operation...")
            limit = 5
            messages = state["messages"]

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

            logger.debug(f"🔍 Raw result type: {type(result)}")
            logger.debug(f"🔍 Raw result: {result}")

            if isinstance(result, list) and len(result) > 0:
                if hasattr(result[0], 'text'):
                    logger.info("🔍 Detected TextContent object in list")
                    result = result[0].text
                    logger.debug(f"🔍 Extracted text from object, length: {len(result)}")

            if isinstance(result, str) and result.startswith('[TextContent('):
                logger.info("🔍 Detected TextContent string, extracting...")
                import re

                start_marker = "text='"
                start_idx = result.find(start_marker)

                if start_idx != -1:
                    start_idx += len(start_marker)

                    end_markers = ["', annotations=", "', type="]
                    end_idx = -1

                    for marker in end_markers:
                        idx = result.find(marker, start_idx)
                        if idx != -1:
                            if end_idx == -1 or idx < end_idx:
                                end_idx = idx

                    if end_idx != -1:
                        json_str = result[start_idx:end_idx]

                        import codecs
                        try:
                            json_str = codecs.decode(json_str, 'unicode_escape')
                        except Exception as decode_err:
                            logger.warning(f"⚠️ Codecs decode failed: {decode_err}, trying manual decode")
                            json_str = json_str.replace('\\n', '\n').replace('\\t', '\t')
                            json_str = json_str.replace('\\\\', '\\').replace("\\'", "'").replace('\\"', '"')

                        result = json_str
                        logger.debug(f"🔍 Extracted text, length: {len(result)}")

            if isinstance(result, str):
                try:
                    result = json.loads(result)
                    logger.info(f"✅ Successfully parsed JSON result")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error: {e}")
                    msg = AIMessage(
                        content=f"Error: Could not parse ingestion result. Check logs for details.")
                    return {
                        "messages": state["messages"] + [msg],
                        "tools": state.get("tools", {}),
                        "llm": state.get("llm"),
                        "ingest_completed": True,
                        "stopped": False
                    }

            # Check if ingestion was stopped
            was_stopped = result.get('stopped', False) if isinstance(result, dict) else False

            if isinstance(result, dict) and "error" in result:
                msg = AIMessage(content=f"Ingestion error: {result['error']}")
            elif was_stopped:
                # Ingestion was stopped
                stop_reason = result.get('stop_reason', 'Stopped by user')
                items_processed = result.get('items_processed', 0)
                msg = AIMessage(
                    content=f"🛑 **Ingestion stopped:** {stop_reason}\n\n"
                            f"Items processed before stop: {items_processed}"
                )
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

            logger.info("✅ Ingest operation completed")

        except Exception as e:
            logger.error(f"❌ Error in ingest_node: {e}")
            import traceback
            traceback.print_exc()
            msg = AIMessage(content=f"Ingestion failed: {str(e)}")
            was_stopped = False

        return {
            "messages": state["messages"] + [msg],
            "tools": state.get("tools", {}),
            "llm": state.get("llm"),
            "ingest_completed": True,
            "stopped": was_stopped
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
            "continue": END
        }
    )

    workflow.add_edge("tools", "agent")
    workflow.add_edge("ingest", END)
    workflow.add_edge("rag", END)

    app = workflow.compile()
    logger.info("✅ LangGraph agent compiled successfully")

    return app


async def run_agent(agent, conversation_state, user_message, logger, tools, system_prompt, llm=None, max_history=20):
    """Execute the agent with the given user message and track metrics"""

    start_time = time.time()

    # ═══════════════════════════════════════════════════════════
    # CLEAR STOP SIGNAL AT START OF NEW REQUEST
    # This ensures old stop requests don't block new requests
    # ═══════════════════════════════════════════════════════════
    clear_stop()
    logger.info("✅ Stop signal cleared for new request")

    try:
        if METRICS_AVAILABLE:
            metrics["agent_runs"] += 1

        conversation_state["loop_count"] += 1

        if conversation_state["loop_count"] >= 5:
            logger.error("⚠️ Loop detected — stopping early after 5 iterations.")
            if METRICS_AVAILABLE:
                metrics["agent_errors"] += 1
                duration = time.time() - start_time
                metrics["agent_times"].append((time.time(), duration))

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
        # NOTE: ainvoke is atomic - can't check stop mid-execution
        # However, individual nodes (router, call_model, ingest_node, rag_node) DO check stop
        result = await agent.ainvoke({
            "messages": conversation_state["messages"],
            "tools": tool_registry,
            "llm": llm,
            "ingest_completed": False,
            "stopped": False
        })

        new_messages = result["messages"][len(conversation_state["messages"]):]
        logger.info(f"📨 Agent added {len(new_messages)} new messages")
        conversation_state["messages"].extend(new_messages)

        # Check if execution was stopped
        was_stopped = result.get("stopped", False)
        if was_stopped:
            logger.warning("🛑 Agent execution was stopped")

        # Track tool calls from AIMessages with tool_calls
        if METRICS_AVAILABLE:
            from langchain_core.messages import ToolMessage
            tool_calls_seen = set()

            for msg in new_messages:
                # Track from ToolMessage to avoid double counting
                if isinstance(msg, ToolMessage):
                    tool_name = getattr(msg, 'name', None)
                    tool_id = getattr(msg, 'tool_call_id', None)

                    if tool_name and tool_id and tool_id not in tool_calls_seen:
                        tool_calls_seen.add(tool_id)
                        metrics["tool_calls"][tool_name] += 1
                        logger.debug(f"📊 Tracked tool: {tool_name}")

        # Reset loop count
        conversation_state["loop_count"] = 0

        # Track successful agent run
        if METRICS_AVAILABLE:
            duration = time.time() - start_time
            metrics["agent_times"].append((time.time(), duration))
            logger.info(f"✅ Agent run completed in {duration:.2f}s (stopped={was_stopped})")

        # Debug: Log final state
        logger.debug(f"📨 Final conversation has {len(conversation_state['messages'])} messages")
        for i, msg in enumerate(conversation_state['messages'][-5:]):
            msg_type = type(msg).__name__
            content_preview = msg.content[:100] if hasattr(msg, 'content') else str(msg)[:100]
            logger.debug(f"  [-{5 - i}] {msg_type}: {content_preview}")

        return {"messages": conversation_state["messages"]}

    except Exception as e:
        if METRICS_AVAILABLE:
            metrics["agent_errors"] += 1
            duration = time.time() - start_time
            metrics["agent_times"].append((time.time(), duration))

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

        logger.exception(f"❌ Unexpected error in agent execution")
        error_text = getattr(e, "args", [str(e)])[0]
        error_msg = AIMessage(
            content=f"An error occurred while running the agent:\n\n{error_text}"
        )
        conversation_state["messages"].append(error_msg)
        return {"messages": conversation_state["messages"]}