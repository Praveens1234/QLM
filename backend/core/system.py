import psutil
import logging
import os

logger = logging.getLogger("QLM.System")

def check_memory(required_mb: int = 500) -> bool:
    """
    Check if there is enough free memory.
    """
    try:
        mem = psutil.virtual_memory()
        available_mb = mem.available / (1024 * 1024)
        if available_mb < required_mb:
            logger.warning(f"Low memory: {available_mb:.2f}MB available, {required_mb}MB required.")
            return False
        return True
    except Exception as e:
        logger.error(f"Failed to check memory: {e}")
        return True # Assume OK if check fails

def get_system_status() -> dict:
    """
    Get current system status (CPU, RAM).
    """
    try:
        mem = psutil.virtual_memory()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "ram_percent": mem.percent,
            "ram_available_mb": round(mem.available / (1024 * 1024), 2),
            "ram_total_mb": round(mem.total / (1024 * 1024), 2)
        }
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return {}
