import os
import subprocess

# Start the SensorMonitor systemd service
SERVICE_NAME = "sensormonitor.service"

try:
    subprocess.run(["sudo", "systemctl", "start", SERVICE_NAME], check=True)
    print(f"Service '{SERVICE_NAME}' started successfully.")
except subprocess.CalledProcessError as e:
    print(f"Failed to start service '{SERVICE_NAME}': {e}")
