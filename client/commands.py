"""
Shared Commands Module (WITH :stats COMMAND)
Handles command processing for both CLI and WebSocket
"""

from langchain_core.messages import SystemMessage


def get_commands_list():
    """Get list of available commands"""
    return [
        ":commands - List all available commands",
        ":stats - Show performance metrics",
        ":tools - List all available tools",
        ":tool <tool> - Get the tool description",
        ":model - View the current active model",
        ":model <model> - Use the model passed",
        ":models - List available models",
        ":multi on - Enable multi-agent mode",
        ":multi off - Disable multi-agent mode",
        ":multi status - Check multi-agent status",
        ":clear history - Clear the chat history"
    ]


def get_tools_list(tools):
    """Get formatted list of all tools"""
    lines = [f"Found {len(tools)} MCP tools:"]
    for t in tools:
        lines.append(f"  - {t.name}")
    return "\n".join(lines)


def get_tool_description(tools, tool_name):
    """Get description for a specific tool"""
    for t in tools:
        if t.name == tool_name:
            return f"  - {t.description}"
    return f"MCP tool {tool_name} not found"


def format_stats_display():
    """Format metrics for CLI/web display"""
    try:
        from client.metrics import prepare_metrics
    except ImportError:
        try:
            from metrics import prepare_metrics
        except ImportError:
            return "Metrics not available"

    metrics = prepare_metrics()

    lines = []
    lines.append("=" * 60)
    lines.append("PERFORMANCE METRICS")
    lines.append("=" * 60)
    lines.append("")

    # Agent Stats
    agent = metrics["agent"]
    lines.append("AGENT EXECUTION:")
    lines.append(f"  Total Runs:    {agent['runs']}")
    lines.append(f"  Errors:        {agent['errors']} ({agent['error_rate']}%)")
    lines.append(f"  Avg Time:      {agent['avg_time']:.2f}s")
    lines.append("")

    # LLM Stats
    llm = metrics["llm"]
    lines.append("LLM CALLS:")
    lines.append(f"  Total Calls:   {llm['calls']}")
    lines.append(f"  Errors:        {llm['errors']}")
    lines.append(f"  Avg Time:      {llm['avg_time']:.2f}s")
    lines.append("")

    # Tool Stats
    tools = metrics["tools"]
    lines.append("TOOL USAGE:")
    lines.append(f"  Total Calls:   {tools['total_calls']}")
    lines.append(f"  Errors:        {tools['total_errors']}")
    lines.append("")

    # Per-Tool Breakdown
    if tools["per_tool"]:
        lines.append("  Top Tools:")
        # Sort by call count
        sorted_tools = sorted(
            tools["per_tool"].items(),
            key=lambda x: x[1]["calls"],
            reverse=True
        )[:10]  # Show top 10

        for tool_name, tool_stats in sorted_tools:
            calls = tool_stats["calls"]
            errors = tool_stats["errors"]
            avg_time = tool_stats["avg_time"]
            lines.append(f"    {tool_name:30s} {calls:3d} calls, {avg_time:5.2f}s avg, {errors} errors")
        lines.append("")

    # Overall
    lines.append("OVERALL:")
    lines.append(f"  Total Errors:  {metrics['overall_errors']}")
    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


async def handle_command(query, tools, model_name, conversation_state, models_module, system_prompt, agent_ref=None,
                         create_agent_fn=None, logger=None, orchestrator=None, multi_agent_state=None):
    """
    Process a command starting with ':'
    Returns: (handled: bool, response: str, new_agent: object or None, new_model: str or None)
    """
    query = query.strip()

    if query == ":commands":
        return True, "\n".join(get_commands_list()), None, None

    if query == ":stop":
        # Import and trigger stop signal
        try:
            from client.stop_signal import request_stop
            request_stop()
            return True, "🛑 Stop requested. Operations will halt at their next checkpoint.", None, None
        except ImportError:
            return True, "Stop signal module not available.", None, None

    if query == ":stats":
        return True, format_stats_display(), None, None

    if query == ":tools":
        return True, get_tools_list(tools), None, None

    if query.startswith(":tool "):
        parts = query.split(maxsplit=1)
        if len(parts) == 1:
            return True, "Usage: :tool <tool_name>", None, None
        tool_name = parts[1]
        return True, get_tool_description(tools, tool_name), None, None

    if query == ":models":
        models = models_module.get_available_models()
        lines = ["Available models:"]
        for model in models:
            lines.append(f"  - {model}")
        return "\n".join(lines), None, None

    if query.startswith(":model "):
        parts = query.split(maxsplit=1)
        if len(parts) == 1:
            return True, "Usage: :model <model_name>", None, None

        new_model_name = parts[1]
        new_agent = await models_module.switch_model(new_model_name, tools, logger, create_agent_fn)
        if new_agent is None:
            return True, f"Model '{new_model_name}' is not installed.", None, None

        return True, f"Model switched to {new_model_name}", new_agent, new_model_name

    if query == ":model":
        return True, f"Using model: {model_name}", None, None

    if query.startswith(":clear "):
        parts = query.split()
        if len(parts) == 1:
            return True, "Specify what to clear", None, None

        target = parts[1]
        if target == "history":
            conversation_state["messages"] = []
            conversation_state["messages"].append(SystemMessage(content=system_prompt))
            return True, "Chat history cleared.", None, None
        else:
            return True, f"Unknown clear target: {target}", None, None

    # Multi-agent commands (update shared state dict)
    if query == ":multi on":
        if multi_agent_state is not None:
            multi_agent_state["enabled"] = True
            if logger:
                logger.info(f"Multi-agent mode ENABLED (state dict updated: {multi_agent_state})")
        else:
            if logger:
                logger.warning("multi_agent_state is None, cannot enable")
        return True, "Multi-agent mode ENABLED\nComplex queries will be broken down and executed by specialized agents.", None, None

    if query == ":multi off":
        if multi_agent_state is not None:
            multi_agent_state["enabled"] = False
            if logger:
                logger.info(f"Multi-agent mode DISABLED (state dict updated: {multi_agent_state})")
        else:
            if logger:
                logger.warning("multi_agent_state is None, cannot disable")
        return True, "Multi-agent mode DISABLED\nAll queries will use single-agent execution.", None, None

    if query == ":multi status":
        # Check actual state from the dict
        if multi_agent_state is not None:
            is_enabled = multi_agent_state.get("enabled", True)
            if logger:
                logger.info(f"Status check - multi_agent_state: {multi_agent_state}")
        else:
            is_enabled = True
            if logger:
                logger.warning("multi_agent_state is None, defaulting to enabled")

        status = "ENABLED" if is_enabled else "DISABLED"
        details = []
        details.append(f"Multi-agent mode: {status}")
        details.append("")

        if orchestrator:
            details.append("Multi-agent system is available and ready.")
        else:
            details.append("Multi-agent system is NOT available.")
            details.append("   Add multi_agent.py to client/ directory to enable.")
            return True, "\n".join(details), None, None

        details.append("")
        details.append("When enabled, complex queries are automatically:")
        details.append("  - Broken down into subtasks")
        details.append("  - Assigned to specialized agents (Researcher, Coder, Analyst, Writer, Planner)")
        details.append("  - Executed in parallel where possible")
        details.append("  - Results are aggregated")
        details.append("")
        details.append("Examples of multi-agent queries:")
        details.append("  - 'Research X, analyze Y, and write Z'")
        details.append("  - 'Find A then compare with B'")
        details.append("  - 'Gather data and create a report'")
        details.append("")
        details.append("Simple queries (weather, todos, search) use single-agent automatically.")

        return True, "\n".join(details), None, None

    return False, None, None, None