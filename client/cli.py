"""
CLI Module
Handles command-line interface and user input
"""

import asyncio
import threading
from queue import Queue

from langchain_core.messages import SystemMessage

from client.websocket import broadcast_message


def list_commands():
    """Print available CLI commands"""
    print(":commands - List all available commands")
    print(":tools - List all available tools")
    print(":tool <tool> - Get the tool description")
    print(":model - View the current active model")
    print(":model <model> - Use the model passed")
    print(":models - List available models")
    print(":clear history - Clear the chat history")


def input_thread(input_queue, stop_event):
    """Thread to handle blocking input() calls"""
    while not stop_event.is_set():
        try:
            query = input("> ")
            input_queue.put(query)
        except (EOFError, KeyboardInterrupt):
            break


async def cli_input_loop(agent, logger, tools, model_name, conversation_state, run_agent_fn, models_module, system_prompt, create_agent_fn):
    """Handle CLI input using a separate thread"""
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
                    models_module.list_models_formatted()
                    continue

                if query.startswith(":model "):
                    parts = query.split(maxsplit=1)
                    if len(parts) == 1:
                        print("Usage: :model <model_name>")
                        continue

                    new_model_name = parts[1]
                    new_agent = await models_module.switch_model(new_model_name, tools, logger, create_agent_fn)
                    if new_agent is None:
                        continue

                    agent = new_agent
                    model_name = new_model_name
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
                        conversation_state["messages"].append(SystemMessage(content=system_prompt))
                        print(f"Chat history cleared.")
                        continue

                    else:
                        print(f"Unknown clear target: {target}")
                        continue

                logger.info(f"💬 Received query: '{query}'")

                print(f"\n> {query}")

                await broadcast_message("cli_user_message", {"text": query})

                result = await run_agent_fn(agent, conversation_state, query, logger, tools)

                final_message = result["messages"][-1]
                assistant_text = final_message.content

                print("\n" + assistant_text + "\n")
                logger.info("✅ Query completed successfully")

                await broadcast_message("cli_assistant_message", {"text": assistant_text})

    except KeyboardInterrupt:
        print("\n👋 Exiting.")
    finally:
        stop_event.set()