import os
import subprocess

# Stop the SensorMonitor systemd service
SERVICE_NAME = "sensormonitor.service"

try:
    subprocess.run(["sudo", "systemctl", "stop", SERVICE_NAME], check=True)
    print(f"Service '{SERVICE_NAME}' stopped successfully.")
except subprocess.CalledProcessError as e:
    print(f"Failed to stop service '{SERVICE_NAME}': {e}")
