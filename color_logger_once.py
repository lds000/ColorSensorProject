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
from requests.auth import HTTPDigestAuth
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

print("=== SCRIPT STARTED: color_logger_once.py ===")

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
    """Log a message to the STDOUT log file and logger."""
    logger = logging.getLogger(STDOUT_LOG)
    logger.info(msg)
    with open(STDOUT_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} [INFO] {msg}\n")

def log_error(msg):
    """Log an error message to the ERROR log file and logger."""
    logger = logging.getLogger(ERROR_LOG)
    logger.error(msg)
    with open(ERROR_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} [ERROR] {msg}\n")

# ---------- WI-FI CHECK ----------
def check_wifi():
    """Check Wi-Fi connectivity and log the status."""
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
    """Get the current IP address of the Pi."""
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
    """Get Wi-Fi SSID and additional info."""
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
    """Retry decorator for functions that may fail, with exponential backoff."""
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
    """Initialize the I2C color sensor with retries."""
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
def calculate_wetness_percent(b, calibration=None):
    """Calculate wetness percent from blue channel value, using calibration if available."""
    if calibration and 'white_stick' in calibration and 'blue_stick' in calibration:
        b_dry = calibration['white_stick']['b']
        b_wet = calibration['blue_stick']['b']
        # Avoid division by zero
        if b_wet == b_dry:
            return 0.0
        return max(0.0, min((b - b_dry) / (b_wet - b_dry), 1.0))
    # Fallback to hardcoded values if no calibration
    b_dry_min = 14
    b_wet_max = 21
    return max(0.0, min((b - b_dry_min) / (b_wet_max - b_dry_min), 1.0))

UNSENT_QUEUE_FILE = "unsent_queue.jsonl"

# ---------- QUEUE UNSENT PAYLOAD ----------
def queue_unsent_payload(payload):
    """Queue a payload for later resend if POST fails."""
    try:
        with open(UNSENT_QUEUE_FILE, "a") as f:
            f.write(json.dumps(payload) + "\n")
        log_error("Payload queued for resend later.")
    except Exception as e:
        log_error(f"Failed to queue payload: {e}")

# ---------- RESEND QUEUED PAYLOADS ----------
def resend_queued_payloads():
    """Attempt to resend all queued payloads."""
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
    """Send a payload to the receiver via HTTP POST, queue if fails."""
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
    """Read color sensor values and return as a dict."""
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
    """Check with parent Pi if shutdown should be aborted."""
    try:
        response = requests.get("http://100.116.147.6:5000/abort-shutdown", timeout=2)
        if response.text.strip().lower() == "abort":
            print("Shutdown aborted by parent Pi.")
            return True
    except Exception as e:
        print(f"Could not contact parent Pi: {e}")
    return False

# ---------- PISUGAR CLASS ----------
class PiSugar:
    """Class to interact with PiSugar hardware for status and sleep control."""
    def __init__(self):
        pass

    def get_status(self):
        """Fetch PiSugar status (battery, voltage, charging, model) via netcat."""
        import subprocess
        try:
            result = subprocess.run(
                ["nc", "-q", "0", "127.0.0.1", "8423"],
                input="get battery\nget voltage\nget charging\nget model\n",
                text=True,
                capture_output=True,
                timeout=2
            )
            status = {"battery": "N/A", "voltage": "N/A", "charging": "N/A", "model": "N/A"}
            for line in result.stdout.splitlines():
                if ':' in line:
                    k, v = line.split(':', 1)
                    status[k.strip()] = v.strip()
            return status
        except Exception as e:
            log_error(f"Failed to fetch PiSugar status (nc): {e}")
            return {"error": str(e)}

    def sleep(self, seconds):
        """Trigger PiSugar sleep for a given number of seconds via netcat."""
        import subprocess
        try:
            cmd = f"sleep {seconds}\n"
            subprocess.run(
                ["nc", "-q", "0", "127.0.0.1", "8423"],
                input=cmd,
                text=True,
                timeout=2
            )
            log_stdout(f"Triggered PiSugar sleep for {seconds} seconds via nc.")
            print(f"Triggered PiSugar sleep for {seconds} seconds via nc.")
        except Exception as e:
            log_error(f"Failed to trigger PiSugar sleep via nc: {e}")
            print(f"Failed to trigger PiSugar sleep via nc: {e}")
            # If sleep fails, wait as fallback
            time.sleep(seconds)

# ---------- LOAD CALIBRATION ----------
def load_calibration(calibration_file="calibration.json"):
    """Load calibration values from calibration.json if present."""
    if os.path.exists(calibration_file):
        with open(calibration_file, "r") as f:
            return json.load(f)
    return None

# ---------- VERSION ----------
SCRIPT_VERSION = 3  # Bumped version for deployment test

# ---------- HEALTH CHECK SERVER ----------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            pisugar_status = PiSugar().get_status()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'status': 'ok',
                'script': 'color_logger_once.py',
                'version': SCRIPT_VERSION,
                'timestamp': datetime.now().isoformat(),
                'pisugar_status': pisugar_status
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()


def start_health_server(port=8080):
    """Start a simple HTTP server for health checks in a background thread."""
    def run_server():
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        server.serve_forever()
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    log_stdout(f"Health check server started on port {port}")

# ---------- MAIN ----------
try:
    print("[DEBUG] Attempting to start health check server on port 8080...")
    log_stdout("[DEBUG] Attempting to start health check server on port 8080...")
    try:
        start_health_server(8080)
        print("[DEBUG] Health check server start call completed.")
        log_stdout("[DEBUG] Health check server start call completed.")
    except Exception as e:
        print(f"[ERROR] Failed to start health check server: {e}")
        log_error(f"[ERROR] Failed to start health check server: {e}")
    calibration = load_calibration()
    if calibration:
        print(f"Loaded calibration: {calibration}")
        log_stdout(f"Loaded calibration: {calibration}")
    else:
        print("No calibration file found. Running without calibration.")
        log_stdout("No calibration file found. Running without calibration.")
    while True:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LED_PIN, GPIO.OUT)
        GPIO.output(LED_PIN, GPIO.LOW)  # Ensure LED is OFF at start

        log_stdout("Script started.")
        check_wifi()
        sensor = init_sensor()
        pisugar = PiSugar()

        # Resend any queued payloads at the start
        resend_queued_payloads()

        # Parameterize sensor_id
        sensor_id = CONFIG.get("SENSOR_ID", "pi_zero_1")
        if hasattr(args, 'sensor_id') and args.sensor_id:
            sensor_id = args.sensor_id

        for i in range(NUM_READINGS):
            print("--- DEBUG: Entering main loop ---")
            print(f"color_logger_once.py version: {SCRIPT_VERSION} (deployed {datetime.now().isoformat()})")
            print("--- DEBUG: After version print ---")
            data = read_color(sensor)
            wetness = calculate_wetness_percent(data['b'], calibration)
            percent_str = f"{wetness * 100:.1f}%"

            # Add calibration info to log and payload
            if calibration:
                data['calibration'] = calibration

            line = (
                f"{data['timestamp']}  R:{data['r']}  G:{data['g']}  "
                f"B:{data['b']}  Lux:{data['lux']:.2f}  Wetness:{percent_str}"
            )

            pisugar_status = pisugar.get_status()
            print(f"PiSugar status: {pisugar_status}")
            log_stdout(f"PiSugar status: {pisugar_status}")

            post_data = {
                "timestamp": data["timestamp"],
                "moisture": data["b"],
                "wetness_percent": wetness,
                "lux": data["lux"],
                "sensor_id": sensor_id,
                "pisugar_status": pisugar_status,
                "script_version": SCRIPT_VERSION,  # Add version to payload
                "calibration": calibration if calibration else None
            }

            with open(LOG_FILE, "a") as f:
                f.write(line + "\n")
            log_stdout(line)
            print(line)  # <-- Add this line to output to console

            try:
                send_to_receiver(post_data)
            except Exception as e:
                log_error(f"Send to receiver failed for reading {i+1}: {e}")
                log_stdout(f"Send to receiver failed for reading {i+1}: {e}")
            time.sleep(READ_INTERVAL)

        # After measurements, stay awake for 2 minutes to allow abort
        print("Staying awake for 2 minutes before sleep. Press Ctrl+C to abort.")
        log_stdout("Staying awake for 2 minutes before sleep. Press Ctrl+C to abort.")
        time.sleep(120)

        # Sleep for 5 minutes using PiSugar API (now via netcat)
        try:
            pisugar.sleep(300)
        except Exception as e:
            log_error(f"Failed to trigger PiSugar sleep: {e}")
            print(f"Failed to trigger PiSugar sleep: {e}")
            # If sleep fails, wait 5 minutes as fallback
            time.sleep(300)

except Exception as e:
    stack = traceback.format_exc()
    log_error(f"{str(e)}\n{stack}")
    log_stdout(f"Exception occurred: {str(e)}\n{stack}")

finally:
    try:
        GPIO.output(LED_PIN, GPIO.LOW)  # 🔧 Ensure LED is OFF no matter what
    except Exception as e:
        log_error(f"Failed to set LED_PIN LOW in finally: {e}")
    GPIO.cleanup()
    log_stdout("GPIO cleaned up. Script finished.")
    # Uncomment for battery mode: Only shutdown if parent Pi does not send abort
    # if not should_abort_shutdown():
    #     subprocess.run(["sudo", "shutdown", "now"])
