"""
Metrics Module
Tracks performance metrics for MCP components with timestamps
"""

import time
from collections import defaultdict

metrics = {
    "agent_runs": 0,
    "agent_errors": 0,
    "agent_times": [],  # list of (timestamp, duration) tuples
    "llm_calls": 0,
    "llm_errors": 0,
    "llm_times": [],  # list of (timestamp, duration) tuples
    "tool_calls": defaultdict(int),  # tool_name: count
    "tool_errors": defaultdict(int),  # tool_name: count
    "tool_times": defaultdict(list),  # tool_name: [(timestamp, duration), ...]
}

def prepare_metrics():
    """Prepare metrics data for broadcasting, with computations and timestamps"""
    tool_total_calls = sum(metrics["tool_calls"].values())
    tool_total_errors = sum(metrics["tool_errors"].values())
    total_errors = metrics["agent_errors"] + metrics["llm_errors"] + tool_total_errors
    agent_error_rate = (metrics["agent_errors"] / metrics["agent_runs"] * 100) if metrics["agent_runs"] > 0 else 0

    # Calculate averages from (timestamp, duration) tuples
    agent_durations = [duration for _, duration in metrics["agent_times"]] if metrics["agent_times"] else []
    llm_durations = [duration for _, duration in metrics["llm_times"]] if metrics["llm_times"] else []

    agent_avg_time = sum(agent_durations) / len(agent_durations) if agent_durations else 0
    llm_avg_time = sum(llm_durations) / len(llm_durations) if llm_durations else 0

    # Calculate tool averages
    tool_avg_times = {}
    for tool_name, time_list in metrics["tool_times"].items():
        durations = [duration for _, duration in time_list] if time_list else []
        tool_avg_times[tool_name] = sum(durations) / len(durations) if durations else 0

    # Limit time series to last 100 for graphs
    recent_agent_times = metrics["agent_times"][-100:]
    recent_llm_times = metrics["llm_times"][-100:]
    recent_tool_times = {k: v[-100:] for k, v in metrics["tool_times"].items()}

    # Format timestamps and durations for frontend
    def format_time_series(time_list):
        """Convert [(timestamp, duration), ...] to {timestamps: [...], durations: [...]}"""
        if not time_list:
            return {"timestamps": [], "durations": []}

        timestamps, durations = zip(*time_list)
        return {
            "timestamps": list(timestamps),
            "durations": list(durations)
        }

    return {
        "agent": {
            "runs": metrics["agent_runs"],
            "errors": metrics["agent_errors"],
            "error_rate": round(agent_error_rate, 2),
            "avg_time": round(agent_avg_time, 2),
            "times": format_time_series(recent_agent_times),
        },
        "llm": {
            "calls": metrics["llm_calls"],
            "errors": metrics["llm_errors"],
            "avg_time": round(llm_avg_time, 2),
            "times": format_time_series(recent_llm_times),
        },
        "tools": {
            "total_calls": tool_total_calls,
            "total_errors": tool_total_errors,
            "per_tool": {
                name: {
                    "calls": metrics["tool_calls"][name],
                    "errors": metrics["tool_errors"][name],
                    "avg_time": round(tool_avg_times.get(name, 0), 2),
                    "times": format_time_series(recent_tool_times.get(name, []))
                } for name in metrics["tool_calls"]
            }
        },
        "overall_errors": total_errors
    }