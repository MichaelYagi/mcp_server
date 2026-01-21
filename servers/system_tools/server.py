"""
System Tools MCP Server
Runs over stdio transport
"""
import json
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP
from tools.system import get_hardware_specs
from tools.system.system_info import get_system_stats
from tools.system.processes import list_processes, kill_process

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Create the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remove any existing handlers (in case something already configured it)
root_logger.handlers.clear()

# Create formatter
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Create file handler
file_handler = logging.FileHandler(LOG_DIR / "mcp_system_tools_server.log", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Add handlers to root logger
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Disable propagation to avoid duplicate logs
logging.getLogger("mcp").setLevel(logging.DEBUG)
logging.getLogger("mcp_system_tools_server").setLevel(logging.INFO)

logger = logging.getLogger("mcp_system_tools_server")
logger.info("🚀 Server logging initialized - writing to logs/mcp_system_tools_server.log")

mcp = FastMCP("system-tools-server")

@mcp.tool()
def get_hardware_specs_tool() -> str:
    """
    Get detailed hardware specifications including CPU, GPU, and RAM.

    Args:
        None

    Returns:
        JSON string with:
        - cpu: {model, cores, threads, frequency}
        - gpu: [{name, vram, driver_version}] (array of GPUs)
        - ram: {total_gb, type, speed_mhz}
        - platform: Operating system name

    Works across Windows, Linux, and macOS.

    Use when user asks about hardware specs, system specs, CPU, GPU, graphics card, or RAM.
    """
    logger.info(f"🛠 [server] get_hardware_specs_tool called")
    result = get_hardware_specs()
    return json.dumps(result, indent=2)


@mcp.tool()
def get_system_info() -> str:
    """
    Retrieve current system health and resource usage.

    Args:
        None

    Returns:
        JSON string with:
        - os: {name, version, architecture}
        - cpu: {usage_percent, load_average}
        - memory: {total_gb, used_gb, available_gb, percent_used}
        - disk: {total_gb, used_gb, free_gb, percent_used}
        - uptime: System uptime in seconds

    Use when user asks about system performance, diagnostics, or machine status.
    """
    logger.info(f"🛠 [server] get_system_info called")
    return get_system_stats()


@mcp.tool()
def list_system_processes(top_n: int = 10) -> str:
    """
    List active system processes sorted by resource usage.

    Args:
        top_n (int, optional): Number of top processes to return (default: 10)

    Returns:
        JSON string with array of processes, each containing:
        - pid: Process ID
        - name: Process name
        - cpu_percent: CPU usage percentage
        - memory_percent: RAM usage percentage
        - status: Process status (running, sleeping, etc.)

    Use when user asks what is running or wants to inspect system activity.
    """
    logger.info(f"🛠 [server] list_system_processes called with top_n: {top_n}")
    return list_processes(top_n)


@mcp.tool()
def terminate_process(pid: int) -> str:
    """
    Terminate a process by its process ID (PID).

    Args:
        pid (int, required): The process ID to terminate

    Returns:
        JSON string with:
        - success: Boolean indicating if termination succeeded
        - pid: The process ID that was terminated
        - message: Confirmation or error message

    Use when user explicitly requests to stop or kill a specific process.
    """
    logger.info(f"🛠 [server] terminate_process called with pid: {pid}")
    return kill_process(pid)

if __name__ == "__main__":
    logger.info(f"🛠 [server] system-tools-server running with stdio enabled")
    mcp.run(transport="stdio")