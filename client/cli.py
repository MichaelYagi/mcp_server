"""
CLI Module (WITH MULTI-AGENT SUPPORT + A2A - FIXED STATE + REAL-TIME STOP)
Handles command-line interface and user input
"""

from prompt_toolkit import prompt
import asyncio
import threading
from queue import Queue

from client.websocket import broadcast_message
from client.commands import handle_command, get_commands_list, handle_a2a_commands, handle_multi_agent_commands
from client.stop_signal import request_stop


def list_commands():
    """Print available CLI commands"""
    for line in get_commands_list():
        print(line)


def input_thread(input_queue, stop_event):
    """Thread to handle blocking input() calls"""
    while not stop_event.is_set():
        try:
            query = prompt("> ")
            input_queue.put(query)
        except (EOFError, KeyboardInterrupt):
            break


async def cli_input_loop(agent, logger, tools, model_name, conversation_state, run_agent_fn, models_module,
                         system_prompt, create_agent_fn, orchestrator=None, multi_agent_state=None, a2a_state=None):
    """Handle CLI input using a separate thread (with multi-agent + A2A support + REAL-TIME STOP)"""
    input_queue = Queue()
    stop_event = threading.Event()

    thread = threading.Thread(target=input_thread, args=(input_queue, stop_event), daemon=True)
    thread.start()

    try:
        while True:
            await asyncio.sleep(0.1)

            if not input_queue.empty():
                query = input_queue.get().strip()

                if query == ":stop":
                    request_stop()
                    print("\n🛑 Stop requested - operation will halt at next checkpoint")
                    print("   This may take a few seconds for the current step to complete.")
                    print("   Watch for '🛑 Stopped' messages below.\n")
                    await broadcast_message("cli_stop_message", {"text": "🛑 Stop requested"})
                    continue

                if not query:
                    continue

                # Handle A2A commands first
                if query.startswith(":a2a"):
                    result = await handle_a2a_commands(query, orchestrator)
                    if result:
                        print(result)
                        await broadcast_message("cli_assistant_message", {"text": result})
                    continue

                # Handle multi-agent commands
                if query.startswith(":multi"):
                    result = await handle_multi_agent_commands(query, orchestrator, multi_agent_state)
                    if result:
                        print(result)
                        await broadcast_message("cli_assistant_message", {"text": result})
                    continue

                # Handle other commands
                if query.startswith(":"):
                    handled, response, new_agent, new_model = await handle_command(
                        query,
                        tools,
                        model_name,
                        conversation_state,
                        models_module,
                        system_prompt,
                        agent_ref=[agent],
                        create_agent_fn=create_agent_fn,
                        logger=logger,
                        orchestrator=orchestrator,
                        multi_agent_state=multi_agent_state,
                        a2a_state=a2a_state
                    )

                    if handled:
                        if response:
                            print(response)
                            await broadcast_message("cli_assistant_message", {"text": response})
                        if new_agent:
                            agent = new_agent
                        if new_model:
                            model_name = new_model
                        continue

                logger.info(f"💬 Received query: '{query}'")

                print(f"\n> {query}")

                await broadcast_message("cli_user_message", {"text": query})

                result = await run_agent_fn(agent, conversation_state, query, logger, tools)

                final_message = result["messages"][-1]
                assistant_text = final_message.content

                print("\n" + assistant_text + "\n")
                logger.info("✅ Query completed successfully")

                await broadcast_message("cli_assistant_message", {
                    "text": assistant_text,
                    "multi_agent": result.get("multi_agent", False),
                    "a2a": result.get("a2a", False)
                })

    except KeyboardInterrupt:
        print("\n👋 Exiting.")
    finally:
        stop_event.set()