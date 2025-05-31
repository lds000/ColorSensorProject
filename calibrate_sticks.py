import time
import json
from datetime import datetime
import os
from busio import I2C  # Use busio instead of adafruit_bitbangio
import argparse

from board import SCL, SDA  # Use hardware I2C pins
import adafruit_tcs34725
import RPi.GPIO as GPIO

# --- CONFIG ---
LED_PIN = 17
NUM_READINGS = 5
READ_INTERVAL = 1  # seconds between readings
CALIBRATION_FILE = "calibration.json"


def init_sensor():
    print("Initializing I2C sensor...")
    i2c = I2C(SCL, SDA)  # Use hardware I2C
    while not i2c.try_lock():
        time.sleep(0.1)
    devices = i2c.scan()
    i2c.unlock()
    addr = 0x29 if 0x29 in devices else (0x2A if 0x2A in devices else None)
    if addr is None:
        raise RuntimeError("Sensor not found on I2C")
    sensor = adafruit_tcs34725.TCS34725(i2c, address=addr)
    sensor.integration_time = 100
    sensor.gain = 4
    print(f"Sensor initialized at address {hex(addr)}")
    return sensor


def read_color(sensor):
    GPIO.output(LED_PIN, GPIO.HIGH)
    time.sleep(0.3)
    r, g, b = sensor.color_rgb_bytes
    lux = sensor.lux
    GPIO.output(LED_PIN, GPIO.LOW)
    return {"r": int(r), "g": int(g), "b": int(b), "lux": float(lux)}


parser = argparse.ArgumentParser()
parser.add_argument('--break-mode', action='store_true', help='Pause for user input after each reading')
args = parser.parse_args()


def average_readings(sensor, label):
    print(f"Take {NUM_READINGS} readings for {label}...")
    readings = []
    for i in range(NUM_READINGS):
        data = read_color(sensor)
        readings.append(data)
        print(f"  Reading {i+1}: R={data['r']} G={data['g']} B={data['b']} Lux={data['lux']:.2f}")
        if args.break_mode:
            input("Press Enter to continue...")
        time.sleep(READ_INTERVAL)
    avg = {k: sum(d[k] for d in readings) / NUM_READINGS for k in readings[0]}
    print(f"  Average: R={avg['r']:.1f} G={avg['g']:.1f} B={avg['b']:.1f} Lux={avg['lux']:.2f}")
    return avg


def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.output(LED_PIN, GPIO.LOW)
    try:
        sensor = init_sensor()
        input("Insert WHITE (control) stick and press Enter...")
        white_avg = average_readings(sensor, "WHITE stick")
        input("Insert BLUE (positive) stick and press Enter...")
        blue_avg = average_readings(sensor, "BLUE stick")
        calibration = {
            "timestamp": datetime.now().isoformat(),
            "white_stick": white_avg,
            "blue_stick": blue_avg
        }
        with open(CALIBRATION_FILE, "w") as f:
            json.dump(calibration, f, indent=2)
        print(f"Calibration saved to {CALIBRATION_FILE}")
    finally:
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.cleanup()

if __name__ == "__main__":
    main()
