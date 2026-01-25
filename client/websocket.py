"""
WebSocket Module with TRUE Concurrent Processing
Uses asyncio.create_task to handle operations in background
"""

import asyncio
import json
import socket
import websockets

from langchain_core.messages import HumanMessage

from client.commands import handle_command, handle_a2a_commands
from client.langgraph import create_langgraph_agent
from client.stop_signal import request_stop

# Import system monitor conditionally
try:
    from tools.system_monitor import system_monitor_loop
    SYSTEM_MONITOR_AVAILABLE = True
except ImportError:
    SYSTEM_MONITOR_AVAILABLE = False

CONNECTED_WEBSOCKETS = set()
SYSTEM_MONITOR_CLIENTS = set()


async def broadcast_message(message_type, data):
    """Broadcast a message to all connected WebSocket clients"""
    if CONNECTED_WEBSOCKETS:
        message = json.dumps({"type": message_type, **data})
        await asyncio.gather(
            *[ws.send(message) for ws in CONNECTED_WEBSOCKETS],
            return_exceptions=True
        )


async def process_query(websocket, prompt, agent_ref, conversation_state, run_agent_fn, logger, tools):
    """
    Process a query in the background (as a task)
    This allows the WebSocket to continue receiving messages (like :stop)
    """
    try:
        print(f"\n> {prompt}")
        await broadcast_message("user_message", {"text": prompt})

        agent = agent_ref[0]
        result = await run_agent_fn(agent, conversation_state, prompt, logger, tools)

        final_message = result["messages"][-1]
        assistant_text = final_message.content

        print("\n" + assistant_text + "\n")

        await broadcast_message("assistant_message", {
            "text": assistant_text,
            "multi_agent": result.get("multi_agent", False),
            "a2a": result.get("a2a", False)
        })

        await websocket.send(json.dumps({
            "type": "complete",
            "stopped": result.get("stopped", False)
        }))

    except Exception as e:
        logger.error(f"❌ Error processing query: {e}")
        await websocket.send(json.dumps({
            "type": "error",
            "text": str(e)
        }))
        await websocket.send(json.dumps({
            "type": "complete",
            "stopped": False
        }))


async def websocket_handler(websocket, agent_ref, tools, logger, conversation_state, run_agent_fn,
                            models_module, model_name, system_prompt, orchestrator=None,
                            multi_agent_state=None, a2a_state=None):
    """
    Handle WebSocket connections with TRUE concurrent processing

    KEY: Long operations run as background tasks, allowing :stop to be processed immediately
    """
    CONNECTED_WEBSOCKETS.add(websocket)

    # Track current background task (if any)
    current_task = None

    try:
        async for raw in websocket:

            if not raw or not raw.strip():
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"type": "user", "text": raw}

            # ═══════════════════════════════════════════════════════════
            # IMMEDIATE STOP HANDLING - Always processed immediately
            # ═══════════════════════════════════════════════════════════
            if data.get("type") == "user" and data.get("text") == ":stop":
                import sys

                logger.warning("🛑 STOP SIGNAL ACTIVATED - Operations will halt at next checkpoint")

                # Set stop flag immediately
                request_stop()

                # Print to CLI
                print("\n🛑 Stop requested - operation will halt at next checkpoint")
                print("   This may take a few seconds for the current step to complete.")
                print("   Watch for '🛑 Stopped' messages below.\n")
                sys.stdout.flush()

                # Send IMMEDIATE response to web UI
                await websocket.send(json.dumps({
                    "type": "assistant_message",
                    "text": "🛑 Stop requested - operation will halt at next checkpoint.\n\nThis may take a few seconds for the current step to complete."
                }))

                # Send completion immediately so UI resets
                await websocket.send(json.dumps({
                    "type": "complete",
                    "stopped": True
                }))

                continue  # Don't process further

            # ═══════════════════════════════════════════════════════════
            # Fast operations - process synchronously
            # ═══════════════════════════════════════════════════════════

            if data.get("type") == "subscribe_system_stats":
                SYSTEM_MONITOR_CLIENTS.add(websocket)
                await websocket.send(json.dumps({
                    "type": "subscribed",
                    "subscription": "system_stats"
                }))
                continue

            if data.get("type") == "unsubscribe_system_stats":
                SYSTEM_MONITOR_CLIENTS.discard(websocket)
                await websocket.send(json.dumps({
                    "type": "unsubscribed",
                    "subscription": "system_stats"
                }))
                continue

            # ═══════════════════════════════════════════════════════════
            # UPDATED: List models - Now shows both Ollama and GGUF
            # ═══════════════════════════════════════════════════════════
            if data.get("type") == "list_models":
                # Get unified model list (both Ollama and GGUF)
                all_models = models_module.get_all_models()

                # Extract just the model names for the dropdown
                model_names = [m["name"] for m in all_models]

                last = models_module.load_last_model()
                await websocket.send(json.dumps({
                    "type": "models_list",
                    "models": model_names,
                    "all_models": all_models,  # Include full info for future enhancement
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

            if data.get("type") == "metrics_request":
                try:
                    from client.metrics import prepare_metrics
                    metrics_data = prepare_metrics()
                except ImportError:
                    try:
                        from metrics import prepare_metrics
                        metrics_data = prepare_metrics()
                    except ImportError:
                        metrics_data = {
                            "agent": {"runs": 0, "errors": 0, "error_rate": 0, "avg_time": 0, "times": []},
                            "llm": {"calls": 0, "errors": 0, "avg_time": 0, "times": []},
                            "tools": {"total_calls": 0, "total_errors": 0, "per_tool": {}},
                            "overall_errors": 0
                        }
                await websocket.send(json.dumps({
                    "type": "metrics_response",
                    "metrics": metrics_data
                }))
                continue

            # ═══════════════════════════════════════════════════════════
            # UPDATED: Switch model - Now auto-detects backend
            # ═══════════════════════════════════════════════════════════
            if data.get("type") == "switch_model":
                model_name = data.get("model")

                # Use unified switch_model that auto-detects backend
                new_agent = await models_module.switch_model(
                    model_name,
                    tools,
                    logger,
                    create_agent_fn=create_langgraph_agent,
                    a2a_state=a2a_state
                )

                if new_agent is None:
                    await websocket.send(json.dumps({
                        "type": "model_error",
                        "message": f"Model '{model_name}' not found"
                    }))
                    continue

                # Clear conversation history when switching models
                conversation_state["messages"] = []
                logger.info("✅ Chat history cleared after model switch")

                agent_ref[0] = new_agent
                await websocket.send(json.dumps({
                    "type": "model_switched",
                    "model": model_name
                }))
                continue

            # ═══════════════════════════════════════════════════════════
            # User messages - Create background task for long operations
            # ═══════════════════════════════════════════════════════════
            if data.get("type") == "user" or "text" in data:
                prompt = data.get("text")

                # Handle :a2a commands (fast - process inline)
                if prompt.startswith(":a2a"):
                    result = await handle_a2a_commands(prompt, orchestrator)
                    if result:
                        await broadcast_message("assistant_message", {"text": result})
                        await websocket.send(json.dumps({
                            "type": "complete",
                            "stopped": False
                        }))
                        continue

                # Handle :multi commands (fast - process inline)
                if prompt.startswith(":multi"):
                    from client.commands import handle_multi_agent_commands
                    result = await handle_multi_agent_commands(prompt, orchestrator, multi_agent_state)
                    if result:
                        await broadcast_message("assistant_message", {"text": result})
                        await websocket.send(json.dumps({
                            "type": "complete",
                            "stopped": False
                        }))
                        continue

                # Handle other commands (fast - process inline)
                if prompt.startswith(":"):
                    handled, response, new_agent, new_model = await handle_command(
                        prompt, tools, model_name, conversation_state, models_module,
                        system_prompt, agent_ref=agent_ref,
                        create_agent_fn=lambda llm, t: agent_ref[0].__class__(llm, t),
                        logger=logger,
                        orchestrator=orchestrator,
                        multi_agent_state=multi_agent_state,
                        a2a_state=a2a_state
                    )
                    if handled:
                        if response:
                            await broadcast_message("assistant_message", {"text": response})
                        if new_agent:
                            agent_ref[0] = new_agent
                        if new_model:
                            model_name = new_model
                        await websocket.send(json.dumps({
                            "type": "complete",
                            "stopped": False
                        }))
                        continue

                # ═══════════════════════════════════════════════════════════
                # Normal query - Run as BACKGROUND TASK
                # This allows WebSocket to continue processing messages (like :stop)
                # ═══════════════════════════════════════════════════════════

                # Cancel previous task if still running (optional)
                if current_task and not current_task.done():
                    logger.warning("⚠️ Cancelling previous task")
                    current_task.cancel()

                # Create background task for query processing
                current_task = asyncio.create_task(
                    process_query(websocket, prompt, agent_ref, conversation_state,
                                run_agent_fn, logger, tools)
                )

                # Don't await - let it run in background!
                # The WebSocket loop continues immediately and can process :stop

    finally:
        # Cancel any running task when connection closes
        if current_task and not current_task.done():
            current_task.cancel()

        CONNECTED_WEBSOCKETS.discard(websocket)
        SYSTEM_MONITOR_CLIENTS.discard(websocket)


async def start_websocket_server(agent, tools, logger, conversation_state, run_agent_fn, models_module,
                                 model_name, system_prompt, orchestrator=None, multi_agent_state=None,
                                 a2a_state=None, host="0.0.0.0", port=8765):
    """Start the WebSocket server for chat (WITH MULTI-AGENT STATE + A2A)"""

    async def handler(websocket):
        try:
            await websocket_handler(
                websocket, [agent], tools, logger, conversation_state, run_agent_fn,
                models_module, model_name, system_prompt,
                orchestrator=orchestrator,
                multi_agent_state=multi_agent_state,
                a2a_state=a2a_state
            )
        except websockets.exceptions.ConnectionClosed:
            pass

    server = await websockets.serve(handler, host, port)

    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        logger.info(f"🌐 WebSocket listening on {host}:{port}")
        logger.info(f"   Local: ws://localhost:{port}")
        logger.info(f"   Network: ws://{local_ip}:{port}")
    except:
        logger.info(f"🌐 WebSocket server at ws://{host}:{port}")

    return server


async def start_log_websocket_server(log_handler_fn, host="0.0.0.0", port=8766):
    """Start a separate WebSocket server for log streaming"""
    import logging

    server = await websockets.serve(log_handler_fn, host, port)

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


def get_system_monitor_clients():
    """Get the set of system monitor WebSocket clients"""
    return SYSTEM_MONITOR_CLIENTS


def is_system_monitor_available():
    """Check if system monitor is available"""
    return SYSTEM_MONITOR_AVAILABLE