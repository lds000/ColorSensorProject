from datetime import datetime

ERROR_LOG = "error_log.txt"
STDOUT_LOG = "stdout_log.txt"

def log_stdout(msg):
    with open(STDOUT_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} [INFO] {msg}\n")

def log_error(msg):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} [ERROR] {msg}\n")
