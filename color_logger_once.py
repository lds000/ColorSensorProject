from adafruit_bitbangio import I2C
from board import D22, D27
import adafruit_tcs34725
import RPi.GPIO as GPIO
import time
from datetime import datetime
import socket
import subprocess
import requests
import json
import os
import argparse
import random
import logging
from logging.handlers import RotatingFileHandler
import traceback

# ---------- CONFIG ----------
def load_config():
    # Default values
    config = {
        "LED_PIN": 17,
        "LOG_FILE": "color_log.txt",
        "ERROR_LOG": "error_log.txt",
        "STDOUT_LOG": "stdout_log.txt",
        "NUM_READINGS": 3,
        "READ_INTERVAL": 5,
        "RECEIVER_URL": "http://100.116.147.6:5000/soil-data"
    }
    # Load from config.json if exists
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            file_config = json.load(f)
            config.update(file_config)
    return config

parser = argparse.ArgumentParser()
parser.add_argument('--num-readings', type=int, help='Number of readings to take')
parser.add_argument('--read-interval', type=int, help='Seconds between readings')
parser.add_argument('--receiver-url', type=str, help='Receiver URL for POST')
args = parser.parse_args()

CONFIG = load_config()
if args.num_readings is not None:
    CONFIG["NUM_READINGS"] = args.num_readings
if args.read_interval is not None:
    CONFIG["READ_INTERVAL"] = args.read_interval
if args.receiver_url is not None:
    CONFIG["RECEIVER_URL"] = args.receiver_url

LED_PIN = CONFIG["LED_PIN"]
LOG_FILE = CONFIG["LOG_FILE"]
ERROR_LOG = CONFIG["ERROR_LOG"]
STDOUT_LOG = CONFIG["STDOUT_LOG"]
NUM_READINGS = CONFIG["NUM_READINGS"]
READ_INTERVAL = CONFIG["READ_INTERVAL"]
RECEIVER_URL = CONFIG["RECEIVER_URL"]

# ---------- LOGGING ENHANCEMENTS ----------
LOG_MAX_BYTES = 1024 * 1024  # 1MB per log file
LOG_BACKUP_COUNT = 3         # Keep up to 3 old log files

# Set up rotating file handlers for logs
for log_file in [LOG_FILE, ERROR_LOG, STDOUT_LOG]:
    handler = RotatingFileHandler(log_file, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
    logger = logging.getLogger(log_file)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

# Update log_stdout and log_error to use logging levels

def log_stdout(msg):
    logger = logging.getLogger(STDOUT_LOG)
    logger.info(msg)
    # Also write to file for compatibility
    with open(STDOUT_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} [INFO] {msg}\n")

def log_error(msg):
    logger = logging.getLogger(ERROR_LOG)
    logger.error(msg)
    # Also write to file for compatibility
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

# Function to get IP address
def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return f"Could not get IP: {e}"

# Function to get WiFi status and info
def get_wifi_info():
    try:
        result = subprocess.run(['iwgetid'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.stdout:
            ssid = result.stdout.strip()
        else:
            ssid = "Not connected to WiFi"
        # Get more info (optional)
        status = subprocess.run(['iwconfig'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return f"SSID: {ssid}\nWiFi Info:\n{status.stdout}"
    except Exception as e:
        return f"Could not get WiFi info: {e}"

# Print network info on startup
print("--- Pi Network Info ---")
print(f"IP Address: {get_ip_address()}")
print(get_wifi_info())
print("-----------------------\n")

# ---------- RETRY DECORATOR ----------
def retry(max_attempts=3, initial_delay=1, backoff=2, jitter=0.5, error_msg=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        if error_msg:
                            log_error(f"{error_msg}: {e}")
                        raise
                    sleep_time = delay + random.uniform(0, jitter)
                    log_stdout(f"Retry {attempt}/{max_attempts} failed: {e}. Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    delay *= backoff
        return wrapper
    return decorator

# ---------- INIT SENSOR (with retry) ----------
@retry(max_attempts=5, initial_delay=2, backoff=2, jitter=1, error_msg="Sensor initialization failed after retries")
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

UNSENT_QUEUE_FILE = "unsent_queue.jsonl"

# ---------- QUEUE UNSENT PAYLOAD ----------
def queue_unsent_payload(payload):
    try:
        with open(UNSENT_QUEUE_FILE, "a") as f:
            f.write(json.dumps(payload) + "\n")
        log_error("Payload queued for resend later.")
    except Exception as e:
        log_error(f"Failed to queue payload: {e}")

# ---------- RESEND QUEUED PAYLOADS ----------
def resend_queued_payloads():
    if not os.path.exists(UNSENT_QUEUE_FILE):
        return
    lines_to_keep = []
    with open(UNSENT_QUEUE_FILE, "r") as f:
        lines = f.readlines()
    for line in lines:
        try:
            payload = json.loads(line)
            send_to_receiver(payload)
        except Exception as e:
            lines_to_keep.append(line)
            log_error(f"Failed to resend queued payload: {e}")
    if lines_to_keep:
        with open(UNSENT_QUEUE_FILE, "w") as f:
            f.writelines(lines_to_keep)
    else:
        os.remove(UNSENT_QUEUE_FILE)

# ---------- HTTP POST SENDER (with retry) ----------
# Update send_to_receiver to queue on failure
@retry(max_attempts=4, initial_delay=2, backoff=2, jitter=1, error_msg="POST to receiver failed after retries")
def send_to_receiver(payload):
    log_stdout(f"Sending payload: {json.dumps(payload)}")
    try:
        response = requests.post(RECEIVER_URL, json=payload, timeout=5)
        log_stdout(f"POST status: {response.status_code}, response: {response.text}")
        response.raise_for_status()
    except Exception as e:
        queue_unsent_payload(payload)
        raise

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

# ---------- ABORT SHUTDOWN CHECK ----------
def should_abort_shutdown():
    try:
        response = requests.get("http://100.116.147.6:5000/abort-shutdown", timeout=2)
        if response.text.strip().lower() == "abort":
            print("Shutdown aborted by parent Pi.")
            return True
    except Exception as e:
        print(f"Could not contact parent Pi: {e}")
    return False

# ---------- MAIN ----------
try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.output(LED_PIN, GPIO.LOW)  # Ensure LED is OFF at start

    log_stdout("Script started.")
    check_wifi()
    sensor = init_sensor()

    # Resend any queued payloads at the start
    resend_queued_payloads()

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
        print(line)  # <-- Add this line to output to console

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
    # Uncomment for battery mode: Only shutdown if parent Pi does not send abort
    # if not should_abort_shutdown():
    #     subprocess.run(["sudo", "shutdown", "now"])
