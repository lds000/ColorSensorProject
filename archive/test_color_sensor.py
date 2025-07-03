"""
Test script for TCS34725 color sensor on Raspberry Pi Zero W.
Reads a single value and prints RGB, lux, and raw data to the console.
Handles errors and logs to error_log.txt if needed.
"""
import time
from board import D22, D27
from adafruit_bitbangio import I2C
import adafruit_tcs34725
from datetime import datetime
import RPi.GPIO as GPIO
import os

LED_PIN = 17
ERROR_LOG_FILE = "error_log.txt"

def log_error(msg):
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {msg}\n"
    print(log_entry.strip())
    try:
        if os.path.exists(ERROR_LOG_FILE):
            with open(ERROR_LOG_FILE, "r") as f:
                lines = f.readlines()
        else:
            lines = []
        lines.append(log_entry)
        lines = lines[-100:]
        with open(ERROR_LOG_FILE, "w") as f:
            f.writelines(lines)
    except Exception as e:
        print(f"[FATAL] Could not write to error log: {e}")

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.output(LED_PIN, GPIO.LOW)
    try:
        print("[INFO] Initializing I2C and color sensor...")
        i2c = I2C(scl=D22, sda=D27)
        while not i2c.try_lock():
            time.sleep(0.1)
        devices = i2c.scan()
        i2c.unlock()
        addr = 0x29 if 0x29 in devices else (0x2A if 0x2A in devices else None)
        if addr is None:
            print("[ERROR] Color sensor not found on I2C bus.")
            log_error("Color sensor not found on I2C bus.")
            return
        sensor = adafruit_tcs34725.TCS34725(i2c, address=addr)
        sensor.integration_time = 100
        sensor.gain = 4
        print(f"[INFO] Color sensor initialized at address {hex(addr)}")
        # Turn on LED for reading
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(0.3)
        r, g, b = sensor.color_rgb_bytes
        lux = sensor.lux
        raw = sensor.color_raw
        GPIO.output(LED_PIN, GPIO.LOW)
        print("[RESULT] TCS34725 Color Sensor Reading:")
        print(f"  Timestamp: {datetime.now().isoformat()}")
        print(f"  RGB: R={r}, G={g}, B={b}")
        print(f"  Lux: {lux}")
        print(f"  Raw: {raw}")
    except Exception as e:
        log_error(f"Color sensor test error: {e}")
        print(f"[ERROR] {e}")
    finally:
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.cleanup()
        print("[INFO] GPIO cleaned up.")

if __name__ == "__main__":
    main()
