"""
Command Handlers for MCP Client
Compatible with existing CLI/WebSocket interfaces
"""


def get_commands_list():
    """Get list of available commands"""
    return [
        ":commands - List all available commands",
        ":stop - Stop current operation (ingestion, search, etc.)",
        ":stats - Show performance metrics",
        ":tools - List all available tools",
        ":tool <tool> - Get the tool description",
        ":model - View the current active model",
        ":model <model> - Use the model passed",
        ":models - List available models",
        ":multi on - Enable multi-agent mode",
        ":multi off - Disable multi-agent mode",
        ":multi status - Check multi-agent status",
        ":a2a on - Enable agent-to-agent mode",
        ":a2a off - Disable agent-to-agent mode",
        ":a2a status - Check A2A system status",
        ":clear history - Clear the chat history"
    ]


def list_commands():
    """Print all available commands"""
    print("\nAvailable Commands:")
    for cmd in get_commands_list():
        print(f"  {cmd}")


async def handle_a2a_commands(command: str, orchestrator):
    """
    Handle A2A-specific commands
    Returns result string or None if command not handled
    """
    if command == ":a2a on":
        if orchestrator:
            orchestrator.enable_a2a()
            return "✅ A2A mode enabled\n   Agents will communicate via messages\n   Use ':a2a status' to see agent status"
        return "❌ Multi-agent orchestrator not available"

    elif command == ":a2a off":
        if orchestrator:
            orchestrator.disable_a2a()
            return "🔗 A2A mode disabled\n   Falling back to multi-agent or single-agent mode"
        return "❌ Multi-agent orchestrator not available"

    elif command == ":a2a status":
        if not orchestrator:
            return "❌ Multi-agent orchestrator not available"

        status = orchestrator.get_a2a_status()
        if not status["enabled"]:
            return "A2A mode: DISABLED\n\nUse ':a2a on' to enable agent-to-agent communication"

        output = ["A2A mode: ENABLED", "=" * 60, ""]
        output.append("Agent Status:")
        output.append("-" * 60)

        for agent_name, agent_status in status["agents"].items():
            busy = "🔴 BUSY" if agent_status["is_busy"] else "🟢 IDLE"
            tools_count = len(agent_status["tools"])
            msgs = agent_status["messages_sent"]

            output.append(f"  {agent_name:15} {busy} | Tools: {tools_count:2} | Messages: {msgs:3}")

        output.append("")
        output.append(f"Message Queue: {status['message_queue_size']} messages")
        output.append("=" * 60)

        return "\n".join(output)

    return None


async def handle_multi_agent_commands(command: str, orchestrator, multi_agent_state):
    """
    Handle multi-agent commands
    Returns result string or None if command not handled
    """
    if command == ":multi on":
        if orchestrator:
            multi_agent_state["enabled"] = True
            return "✅ Multi-agent mode enabled\n   Complex queries will be broken down automatically"
        return "❌ Multi-agent orchestrator not available"

    elif command == ":multi off":
        if orchestrator:
            multi_agent_state["enabled"] = False
            return "🤖 Multi-agent mode disabled\n   Using single-agent execution"
        return "❌ Multi-agent orchestrator not available"

    elif command == ":multi status":
        if not orchestrator:
            return "❌ Multi-agent orchestrator not available"

        if multi_agent_state["enabled"]:
            return "Multi-agent mode: ENABLED\n   Complex queries are automatically distributed to specialized agents"
        else:
            return "Multi-agent mode: DISABLED\n   Use ':multi on' to enable"

    return None


def is_command(text: str) -> bool:
    """Check if text is a command"""
    return text.strip().startswith(":")


async def handle_command(
    command: str,
    tools,
    model_name,
    conversation_state,
    models_module,
    system_prompt,
    agent_ref=None,
    create_agent_fn=None,
    logger=None,
    orchestrator=None,
    multi_agent_state=None,
    a2a_state=None
):
    """
    Main command handler compatible with existing CLI/WebSocket interface

    Returns: (handled: bool, response: str, new_agent, new_model)
    """
    command = command.strip()

    # A2A commands
    if command.startswith(":a2a"):
        result = await handle_a2a_commands(command, orchestrator)
        if result:
            return (True, result, None, None)

    # Multi-agent commands
    if command.startswith(":multi"):
        result = await handle_multi_agent_commands(command, orchestrator, multi_agent_state)
        if result:
            return (True, result, None, None)

    # List commands
    if command == ":commands":
        result = "\n".join(get_commands_list())
        return (True, result, None, None)

    # Stop command
    if command == ":stop":
        from client.stop_signal import request_stop
        request_stop()
        return (True, "🛑 Stop signal sent - operations will halt at next checkpoint", None, None)

    # Stats command
    if command == ":stats":
        try:
            from client.metrics import prepare_metrics, format_metrics_summary
            metrics = prepare_metrics()
            summary = format_metrics_summary(metrics)
            return (True, summary, None, None)
        except ImportError:
            return (True, "📊 Stats system not available", None, None)

    # Tools command
    if command == ":tools":
        if tools:
            tool_list = "\n".join([f"  - {tool.name}: {tool.description}" for tool in tools])
            return (True, f"Available tools:\n{tool_list}", None, None)
        return (True, "No tools available", None, None)

    # Tool detail command
    if command.startswith(":tool "):
        tool_name = command[6:].strip()
        for tool in tools:
            if tool.name == tool_name:
                return (True, f"Tool: {tool.name}\n\n{tool.description}", None, None)
        return (True, f"Tool '{tool_name}' not found", None, None)

    # Model commands
    if command == ":model":
        return (True, f"Current model: {model_name}", None, None)

    if command == ":models":
        available = models_module.get_available_models()
        models_list = "\n".join([f"  {'→' if m == model_name else ' '} {m}" for m in available])
        return (True, f"Available models:\n{models_list}", None, None)

    if command.startswith(":model "):
        new_model = command[7:].strip()

        if logger:
            logger.info(f"Switching to model: {new_model}")

        new_agent = await models_module.switch_model(
            new_model,
            tools,
            logger,
            create_agent_fn
        )

        if new_agent is None:
            return (True, f"❌ Model '{new_model}' is not installed", None, None)

        return (True, f"✅ Switched to model: {new_model}", new_agent, new_model)

    # Clear history
    if command == ":clear history":
        conversation_state["messages"] = []
        return (True, "✅ Chat history cleared", None, None)

    # Command not recognized
    return (False, None, None, None)