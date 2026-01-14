"""
Global Stop Signal Module
Provides a simple global flag to stop long-running operations
"""

import logging

logger = logging.getLogger("mcp_client")

# Global stop signal dictionary
STOP_SIGNAL = {"requested": False}


def request_stop():
    """Request that all operations stop at their next checkpoint"""
    STOP_SIGNAL["requested"] = True
    logger.info("🛑 Stop signal requested")


def clear_stop():
    """Clear the stop signal (call at start of operations)"""
    STOP_SIGNAL["requested"] = False


def is_stop_requested() -> bool:
    """Check if stop has been requested"""
    return STOP_SIGNAL["requested"]


def check_stop_and_raise():
    """
    Check stop signal and raise an exception if requested.
    Use this in operations that can't return early gracefully.
    """
    if STOP_SIGNAL["requested"]:
        raise StopRequestedException("Operation stopped by user")


class StopRequestedException(Exception):
    """Exception raised when a stop is requested"""
    pass