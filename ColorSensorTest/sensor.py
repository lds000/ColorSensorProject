import RPi.GPIO as GPIO
import time
from board import D22, D27
from adafruit_bitbangio import I2C
import adafruit_tcs34725
from logging_utils import log_stdout, log_error

LED_PIN = 17

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.output(LED_PIN, GPIO.LOW)

def cleanup_gpio():
    GPIO.output(LED_PIN, GPIO.LOW)
    GPIO.cleanup()

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

def read_color(sensor):
    log_stdout("Reading color sensor...")
    GPIO.output(LED_PIN, GPIO.HIGH)
    time.sleep(0.3)
    r, g, b = sensor.color_rgb_bytes
    lux = sensor.lux
    GPIO.output(LED_PIN, GPIO.LOW)
    log_stdout(f"Sensor values: R={r}, G={g}, B={b}, Lux={lux}")
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "r": int(r),
        "g": int(g),
        "b": int(b),
        "lux": float(lux)
    }
