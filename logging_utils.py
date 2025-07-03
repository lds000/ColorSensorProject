import os
from datetime import datetime
from services.log_manager import LogManager

ERROR_LOG_FILE = "error_log.txt"

def calculate_flow_rate(litres, duration_seconds):
    """
    Calculate the flow rate in liters per minute.
    Args:
        litres (float): The amount of water in liters measured during the duration.
        duration_seconds (float): The duration in seconds over which the flow was measured.
    Returns:
        float: The flow rate in liters per minute.
    """
    try:
        if litres is None or duration_seconds == 0:
            return 0.0
        return (litres / duration_seconds) * 60
    except Exception as e:
        LogManager.log_error(f"Flow rate calculation error: {e}")
        return 0.0
