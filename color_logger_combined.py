import requests
from datetime import datetime
from sensor import setup_gpio, cleanup_gpio, setup_flow_gpio, cleanup_flow_gpio, init_sensor, read_all_sensors
from logging_utils import log_stdout, log_error
import time
import json

RECEIVER_URL = "http://100.116.147.6:5000/soil-data"  # Change as needed
NUM_READINGS = 4
READ_SPACING = 2  # seconds between readings
READ_INTERVAL = 5  # minutes between groups

LOG_FILE = "color_log.txt"


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
            try:
                resp = requests.post(RECEIVER_URL, json=payload, timeout=5)
                log_stdout(f"POST status: {resp.status_code}, response: {resp.text}")
                resp.raise_for_status()
            except Exception as e:
                log_error(f"POST failed: {e}")
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
