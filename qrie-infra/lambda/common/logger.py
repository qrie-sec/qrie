"""
Centralized logging utility for qrie Lambda functions.

Usage:
    from common.logger import debug, info, error
    
    debug("Detailed diagnostic information")
    info("General informational messages")
    error("Error conditions")

Environment Variables:
    DEBUG=true - Enables DEBUG level logging (default: false)
"""
import os
import sys
from datetime import datetime

# Parse DEBUG environment variable
_DEBUG_ENABLED = os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes')


def _log(level: str, message: str):
    """Internal logging function with timestamp and level."""
    print(f"{level}: {message}", file=sys.stdout, flush=True)


def debug(message: str):
    """Log DEBUG level message. Only shown when DEBUG=true environment variable is set."""
    if _DEBUG_ENABLED:
        _log("DEBUG", message)


def info(message: str):
    """Log INFO level message. Always shown."""
    _log("INFO", message)


def error(message: str):
    """Log ERROR level message. Always shown."""
    _log("ERROR", message)


# Convenience function to check if debug is enabled
def is_debug_enabled() -> bool:
    """Returns True if DEBUG logging is enabled."""
    return _DEBUG_ENABLED
