"""
WebSocket Module
Handles WebSocket servers for chat, logs, and system monitor
"""

import asyncio
import json
import socket
import websockets

from langchain_core.messages import HumanMessage

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


async def websocket_handler(websocket, agent_ref, tools, logger, conversation_state, run_agent_fn, models_module):
    """Handle WebSocket connections for chat"""
    CONNECTED_WEBSOCKETS.add(websocket)

    try:
        async for raw in websocket:

            if not raw or not raw.strip():
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"type": "user", "text": raw}

            # Handle system stats subscription
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

            if data.get("type") == "list_models":
                models = models_module.get_available_models()
                last = models_module.load_last_model()
                await websocket.send(json.dumps({
                    "type": "models_list",
                    "models": models,
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

            if data.get("type") == "switch_model":
                model_name = data.get("model")

                new_agent = await models_module.switch_model(
                    model_name,
                    tools,
                    logger,
                    lambda llm, t: agent_ref[0].__class__(llm, t)
                )

                if new_agent is None:
                    await websocket.send(json.dumps({
                        "type": "model_error",
                        "message": f"Model '{model_name}' is not installed."
                    }))
                    continue

                agent_ref[0] = new_agent

                await websocket.send(json.dumps({
                    "type": "model_switched",
                    "model": model_name
                }))
                continue

            if data.get("type") == "user" or "text" in data:
                prompt = data.get("text")

                print(f"\n> {prompt}")

                await broadcast_message("user_message", {"text": prompt})

                agent = agent_ref[0]
                result = await run_agent_fn(agent, conversation_state, prompt, logger, tools)

                final_message = result["messages"][-1]
                assistant_text = final_message.content

                print("\n" + assistant_text + "\n")

                await broadcast_message("assistant_message", {"text": assistant_text})
    finally:
        CONNECTED_WEBSOCKETS.discard(websocket)
        SYSTEM_MONITOR_CLIENTS.discard(websocket)


async def start_websocket_server(agent, tools, logger, conversation_state, run_agent_fn, models_module, host="0.0.0.0",
                                 port=8765):
    """Start the WebSocket server for chat"""

    async def handler(websocket):
        try:
            await websocket_handler(websocket, [agent], tools, logger, conversation_state, run_agent_fn, models_module)
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