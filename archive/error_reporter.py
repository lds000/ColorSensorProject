"""
MQTT Error Reporter Service
--------------------------
Monitors error_log.txt and publishes new errors to the MQTT topic 'status/errors'.

- Publishes each new error line as a JSON message with timestamp and error text.
- Uses the same MQTT broker as the main system (default: 100.116.147.6:1883).
- Designed to run as a background service (systemd recommended).
- Robust error handling and reconnect logic.

Edit MQTT_BROKER, MQTT_PORT, and ERROR_LOG_FILE as needed.
"""
import time
import json
import os
import paho.mqtt.client as mqtt
from datetime import datetime

MQTT_BROKER = "100.116.147.6"
MQTT_PORT = 1883
MQTT_TOPIC = "status/errors"
ERROR_LOG_FILE = "error_log.txt"
POLL_INTERVAL = 2  # seconds


def tail_error_log(file_path):
    """Generator that yields new lines as they are written to the file."""
    with open(file_path, 'r') as f:
        # Go to the end of file
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(POLL_INTERVAL)
                continue
            yield line.strip()

def publish_error(error_text, mqtt_client):
    payload = {
        "timestamp": datetime.now().isoformat(),
        "error": error_text
    }
    mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=0, retain=False)


def main():
    mqtt_client = mqtt.Client()
    while True:
        try:
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            print(f"[INFO] Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            break
        except Exception as e:
            print(f"[ERROR] MQTT connect failed: {e}. Retrying in 5s...")
            time.sleep(5)
    mqtt_client.loop_start()
    print(f"[INFO] Monitoring {ERROR_LOG_FILE} for new errors...")
    for line in tail_error_log(ERROR_LOG_FILE):
        if line:
            print(f"[ERROR] {line}")
            publish_error(line, mqtt_client)

if __name__ == "__main__":
    main()
