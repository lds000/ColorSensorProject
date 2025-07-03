import logging
from datetime import datetime

LOG_FILE = "stdout_log.txt"
ERROR_LOG = "error_log.txt"

# Set up basic logging to file
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[
    logging.FileHandler(LOG_FILE),
    logging.StreamHandler()
])

# Error logger
error_logger = logging.getLogger("error")
error_handler = logging.FileHandler(ERROR_LOG)
error_handler.setLevel(logging.ERROR)
error_logger.addHandler(error_handler)

def log_stdout(msg):
    """Log a message to the STDOUT log file and logger."""
    logging.info(msg)
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} [INFO] {msg}\n")

def log_error(msg):
    """Log an error message to the ERROR log file and logger."""
    error_logger.error(msg)
    with open(ERROR_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} [ERROR] {msg}\n")
