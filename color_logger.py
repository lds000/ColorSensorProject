from adafruit_bitbangio import I2C
from board import D22, D27
import adafruit_tcs34725
import RPi.GPIO as GPIO
import time
from datetime import datetime
import threading
import traceback
import os

# ---------- CONFIG ----------
LED_PIN = 17
INTERVAL_SECONDS = 10
LOG_FILE = "color_log.txt"
ERROR_LOG = "error_log.txt"
STDOUT_LOG = "stdout_log.txt"

# ---------- CLEAR LOGS ON STARTUP ----------
for log_file in [LOG_FILE, ERROR_LOG, STDOUT_LOG]:
    with open(log_file, "w") as f:
        f.write(f"[INFO] {log_file} initialized at {datetime.now().isoformat()}\n")

# ---------- INIT GPIO ----------
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.output(LED_PIN, GPIO.LOW)

# ---------- WAIT FOR SENSOR ----------
def wait_for_sensor(timeout=60):
    start_time = time.time()
    sensor = None

    while time.time() - start_time < timeout:
        try:
            print(f"[INFO] Attempting bitbang I2C connection... {int(time.time() - start_time)}s")
            i2c = I2C(scl=D22, sda=D27)

            while not i2c.try_lock():
                time.sleep(0.1)
            devices = i2c.scan()
            i2c.unlock()

            print(f"[INFO] I2C scan complete. Devices found: {[hex(d) for d in devices]}")

            if 0x29 in devices or 0x2A in devices:
                addr = 0x29 if 0x29 in devices else 0x2A
                print(f"[INFO] Found TCS34725 at address {hex(addr)}. Initializing...")
                sensor = adafruit_tcs34725.TCS34725(i2c, address=addr)
                sensor.integration_time = 100
                sensor.gain = 4
                return sensor
            else:
                print("[WARN] TCS34725 not found on I2C bus. Retrying...")

        except Exception as e:
            error_msg = f"[RETRY ERROR] {datetime.now().isoformat()} - {str(e)}"
            stack = traceback.format_exc()
            print(error_msg)
            with open(ERROR_LOG, "a") as ef:
                ef.write(error_msg + "\n" + stack + "\n")

        time.sleep(1)

    with open(ERROR_LOG, "a") as ef:
        ef.write(f"[INIT TIMEOUT] {datetime.now().isoformat()} - Sensor not found after {timeout} seconds.\n")
    raise RuntimeError("TCS34725 sensor not detected.")

# ---------- INIT SENSOR ----------
sensor = wait_for_sensor()

# ---------- WETNESS CALCULATION ----------
def calculate_wetness_percent(b):
    b_dry_min = 14
    b_wet_max = 21
    percent = (b - b_dry_min) / (b_wet_max - b_dry_min)
    return max(0.0, min(percent, 1.0))

# ---------- SENSOR READER ----------
def read_color():
    GPIO.output(LED_PIN, GPIO.HIGH)
    time.sleep(0.3)
    r, g, b = sensor.color_rgb_bytes
    lux = sensor.lux
    GPIO.output(LED_PIN, GPIO.LOW)
    return {
        "timestamp": datetime.now().isoformat(),
        "r": int(r),
        "g": int(g),
        "b": int(b),
        "lux": float(lux)
    }

# ---------- SENSOR LOOP ----------
def sensor_loop():
    while True:
        try:
            data = read_color()
            wetness = calculate_wetness_percent(data['b'])
            percent_str = f"{wetness * 100:.1f}%"

            log_line = (
                f"{data['timestamp']}  R:{data['r']}  G:{data['g']}  "
                f"B:{data['b']}  Lux:{data['lux']:.2f}  Wetness:{percent_str}"
            )

            with open(LOG_FILE, "a") as f:
                f.write(log_line + "\n")
            with open(STDOUT_LOG, "a") as f:
                f.write(log_line + "\n")

        except Exception as e:
            error_msg = f"[ERROR] {datetime.now().isoformat()} - {str(e)}\n"
            stack = traceback.format_exc()
            with open(ERROR_LOG, "a") as ef:
                ef.write(error_msg + stack)
            with open(STDOUT_LOG, "a") as f:
                f.write(error_msg + stack)

        try:
            time.sleep(INTERVAL_SECONDS)
        except Exception as e:
            with open(ERROR_LOG, "a") as ef:
                ef.write(f"[SLEEP ERROR] {datetime.now().isoformat()} - {str(e)}\n")

# ---------- THREAD WRAPPER ----------
def protected_sensor_loop():
    try:
        sensor_loop()
    except Exception as e:
        with open(ERROR_LOG, "a") as ef:
            ef.write(f"[CRASH] {datetime.now().isoformat()} - {str(e)}\n")
            ef.write(traceback.format_exc() + "\n")

# ---------- MAIN ----------
if __name__ == "__main__":
    try:
        t = threading.Thread(target=protected_sensor_loop)
        t.start()
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        with open(STDOUT_LOG, "a") as f:
            f.write("[INFO] Keyboard interrupt received. Cleaning up.\n")
        GPIO.cleanup()

    except Exception as e:
        with open(ERROR_LOG, "a") as ef:
            ef.write(f"[MAIN ERROR] {datetime.now().isoformat()} - {str(e)}\n")
            ef.write(traceback.format_exc() + "\n")
        GPIO.cleanup()
