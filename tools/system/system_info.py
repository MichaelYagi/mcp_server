import psutil
import platform
import shutil
import json


def get_system_stats():
    """Gathers CPU, RAM, and Disk usage."""
    # CPU usage
    cpu_pct = psutil.cpu_percent(interval=1)

    # RAM usage
    mem = psutil.virtual_memory()

    # Disk usage (C: for Windows)
    total, used, free = shutil.disk_usage("C:\\")

    stats = {
        "os": platform.system(),
        "cpu_usage_percent": cpu_pct,
        "memory_usage_percent": mem.percent,
        "disk_free_gb": round(free / (2 ** 30), 2),
        "disk_total_gb": round(total / (2 ** 30), 2)
    }

    return json.dumps(stats, indent=2)