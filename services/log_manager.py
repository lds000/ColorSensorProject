"""
LogManager: Centralized log file management for the sensor system.
Handles error logging, log trimming, and debug/info logging.

Usage:
    log_mgr = LogManager("error_log.txt")
    log_mgr.log_error("message")
    log_mgr.trim_log_file("log.txt", max_lines=1000)
"""
import time
import threading

class LogManager:
    def __init__(self, error_log_file="error_log.txt"):
        self.error_log_file = error_log_file
        self._lock = threading.Lock()

    def log_error(self, msg):
        """Log a critical error message to the error log file with timestamp."""
        try:
            with self._lock:
                with open(self.error_log_file, "a") as f:
                    f.write(f"[ERROR][{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        except Exception:
            pass

    def log_info(self, msg):
        """Log an info/debug message to the error log file with timestamp."""
        try:
            with self._lock:
                with open(self.error_log_file, "a") as f:
                    f.write(f"[INFO][{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        except Exception:
            pass

    def trim_log_file(self, log_file, max_lines=1000):
        """Trim a log file to the last max_lines lines."""
        try:
            with self._lock:
                with open(log_file, "r") as f:
                    lines = f.readlines()
                if len(lines) > max_lines:
                    with open(log_file, "w") as f:
                        f.writelines(lines[-max_lines:])
        except Exception:
            pass
