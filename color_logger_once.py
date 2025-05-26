from adafruit_bitbangio import I2C
from board import D22, D27
import adafruit_tcs34725
import RPi.GPIO as GPIO
import time
from datetime import datetime
import socket
import subprocess
import traceback
import requests
import json
import os

# ---------- CONFIG ----------
LED_PIN = 17
LOG_FILE = "color_log.txt"
ERROR_LOG = "error_log.txt"
STDOUT_LOG = "stdout_log.txt"
NUM_READINGS = 3
READ_INTERVAL = 5  # seconds between readings
RECEIVER_URL = "http://100.116.147.6:5000/soil-data"  # Tailscale IP of receiver

def log_stdout(msg):
    with open(STDOUT_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} [INFO] {msg}\n")

def log_error(msg):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} [ERROR] {msg}\n")

# ---------- WI-FI CHECK ----------
def check_wifi():
    try:
        ip = socket.gethostbyname(socket.gethostname())
        status = f"Wi-Fi OK, IP: {ip}"
    except Exception:
        status = "Wi-Fi FAIL"
    log_stdout(status)
    if "FAIL" in status:
        log_error("Wi-Fi not connected")

# ---------- INIT SENSOR ----------
def init_sensor():
    log_stdout("Initializing I2C sensor...")
    i2c = I2C(scl=D22, sda=D27)
    while not i2c.try_lock():
        time.sleep(0.1)
    devices = i2c.scan()
    i2c.unlock()
    log_stdout(f"I2C devices found: {devices}")

    addr = 0x29 if 0x29 in devices else (0x2A if 0x2A in devices else None)
    if addr is None:
        log_error("Sensor not found on I2C")
        GPIO.output(LED_PIN, GPIO.LOW)
        raise RuntimeError("Sensor not found on I2C")

    sensor = adafruit_tcs34725.TCS34725(i2c, address=addr)
    sensor.integration_time = 100
    sensor.gain = 4
    log_stdout(f"Sensor initialized at address {hex(addr)}")
    return sensor

# ---------- WETNESS CALCULATION ----------
def calculate_wetness_percent(b):
    b_dry_min = 14
    b_wet_max = 21
    return max(0.0, min((b - b_dry_min) / (b_wet_max - b_dry_min), 1.0))

# ---------- HTTP POST SENDER ----------
def send_to_receiver(payload):
    log_stdout(f"Sending payload: {json.dumps(payload)}")
    try:
        response = requests.post(RECEIVER_URL, json=payload, timeout=5)
        log_stdout(f"POST status: {response.status_code}, response: {response.text}")
        response.raise_for_status()
    except Exception as e:
        log_error(f"[POST ERROR] {str(e)}")
        log_error(f"Failed payload: {json.dumps(payload)}")

# ---------- SENSOR READER ----------
def read_color(sensor):
    log_stdout("Reading color sensor...")
    GPIO.output(LED_PIN, GPIO.HIGH)
    time.sleep(0.3)
    r, g, b = sensor.color_rgb_bytes
    lux = sensor.lux
    GPIO.output(LED_PIN, GPIO.LOW)
    log_stdout(f"Sensor values: R={r}, G={g}, B={b}, Lux={lux}")
    return {
        "timestamp": datetime.now().isoformat(),
        "r": int(r),
        "g": int(g),
        "b": int(b),
        "lux": float(lux)
    }

# ---------- MAIN ----------
try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.output(LED_PIN, GPIO.LOW)  # Ensure LED is OFF at start

    log_stdout("Script started.")
    check_wifi()
    sensor = init_sensor()

    for i in range(NUM_READINGS):
        data = read_color(sensor)
        wetness = calculate_wetness_percent(data['b'])
        percent_str = f"{wetness * 100:.1f}%"

        line = (
            f"{data['timestamp']}  R:{data['r']}  G:{data['g']}  "
            f"B:{data['b']}  Lux:{data['lux']:.2f}  Wetness:{percent_str}"
        )

        post_data = {
            "timestamp": data["timestamp"],
            "moisture": data["b"],
            "wetness_percent": wetness,
            "lux": data["lux"],
            "sensor_id": "pi_zero_1"
        }

        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
        log_stdout(line)

        send_to_receiver(post_data)
        time.sleep(READ_INTERVAL)

except Exception as e:
    stack = traceback.format_exc()
    log_error(f"{str(e)}\n{stack}")
    log_stdout(f"Exception occurred: {str(e)}\n{stack}")

finally:
    GPIO.output(LED_PIN, GPIO.LOW)  # 🔧 Ensure LED is OFF no matter what
    GPIO.cleanup()
    log_stdout("GPIO cleaned up. Script finished.")
    # subprocess.run(["sudo", "shutdown", "now"])  # Uncomment for battery mode
