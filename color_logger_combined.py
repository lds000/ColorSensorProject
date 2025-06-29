import requests
from datetime import datetime, timedelta
from sensor import setup_gpio, cleanup_gpio, setup_flow_gpio, cleanup_flow_gpio, init_sensor, read_all_sensors
from logging_utils import log_stdout, log_error
import time
import json
import paho.mqtt.client as mqtt

NUM_READINGS = 4
READ_SPACING = 2  # seconds between readings
READ_INTERVAL = 5  # minutes between groups

LOG_FILE = "color_log.txt"
MQTT_BROKER = "100.116.147.6"
MQTT_PORT = 1883
MQTT_TOPIC = "sensors/plant"


def main():
    setup_gpio()
    setup_flow_gpio()
    sensor = init_sensor()
    try:
        while True:
            readings = []
            first_timestamp = None
            for i in range(NUM_READINGS):
                data = read_all_sensors(sensor)
                if i == 0:
                    first_timestamp = data["timestamp"]
                readings.append(data)
                line = (
                    f"{data['timestamp']}  R:{data['r']}  G:{data['g']}  B:{data['b']}  Lux:{data['lux']:.2f}  Flow(L):{data['flow_litres']:.3f}"
                )
                with open(LOG_FILE, "a") as f:
                    f.write(line + "\n")
                log_stdout(line)
                print(line)
                if i < NUM_READINGS - 1:
                    time.sleep(READ_SPACING)
            # Average blue channel and flow
            avg_b = sum(d['b'] for d in readings) / NUM_READINGS
            total_flow = sum(d['flow_litres'] for d in readings)
            payload = {
                "timestamp": first_timestamp,
                "moisture": avg_b,
                "flow_litres": total_flow
            }
            avg_line = f"AVG {first_timestamp}  B:{avg_b:.1f}  Flow(L):{total_flow:.3f}"
            with open(LOG_FILE, "a") as f:
                f.write(avg_line + "\n")
            log_stdout(avg_line)
            print(avg_line)
            # MQTT publish instead of HTTP POST
            try:
                client = mqtt.Client()
                client.connect(MQTT_BROKER, MQTT_PORT, 60)
                client.publish(MQTT_TOPIC, json.dumps(payload))
                client.disconnect()
            except Exception as e:
                log_error(f"MQTT publish failed: {e}")
            # Wait until next group
            next_group_time = datetime.fromisoformat(first_timestamp) + timedelta(minutes=READ_INTERVAL)
            now = datetime.now()
            sleep_time = (next_group_time - now).total_seconds()
            if sleep_time > 0:
                print(f"Waiting {sleep_time:.1f} seconds until next group...")
                time.sleep(sleep_time)
    finally:
        cleanup_gpio()
        cleanup_flow_gpio()
        log_stdout("GPIO cleaned up. Script finished.")

if __name__ == "__main__":
    main()
