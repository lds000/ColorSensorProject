import os
from datetime import datetime

ERROR_LOG_FILE = "error_log.txt"

def log_error(message):
    """Log critical errors with timestamp to error_log.txt and print to console."""
    try:
        ts = datetime.now().isoformat()
        with open(ERROR_LOG_FILE, "a") as f:
            f.write(f"[{ts}] ERROR: {message}\n")
        print(f"[ERROR] {message}")
    except Exception as e:
        print(f"[FATAL] Could not write to error_log.txt: {e}")

def trim_log_file(log_file, max_lines):
    """Trim a log file to the last max_lines lines for log rotation and disk space safety."""
    try:
        if not os.path.exists(log_file):
            return
        with open(log_file, "r") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            with open(log_file, "w") as f:
                f.writelines(lines[-max_lines:])
    except Exception as e:
        log_error(f"Failed to trim {log_file}: {e}")

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
        log_error(f"Flow rate calculation error: {e}")
        return 0.0
