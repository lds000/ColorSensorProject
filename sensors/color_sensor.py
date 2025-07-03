import time
from datetime import datetime
import adafruit_tcs34725
from adafruit_bitbangio import I2C
from board import D22, D27
import RPi.GPIO as GPIO

class ColorSensor:
    """Encapsulates TCS34725 color sensor logic."""
    def __init__(self, led_pin, num_readings=4, read_spacing=2):
        self.led_pin = led_pin
        self.num_readings = num_readings
        self.read_spacing = read_spacing
        self.sensor = None
        self._init_sensor()

    def _init_sensor(self):
        i2c = I2C(scl=D22, sda=D27)
        while not i2c.try_lock():
            time.sleep(0.1)
        devices = i2c.scan()
        i2c.unlock()
        addr = 0x29 if 0x29 in devices else (0x2A if 0x2A in devices else None)
        if addr is None:
            GPIO.output(self.led_pin, GPIO.LOW)
            raise RuntimeError("Color sensor not found on I2C")
        self.sensor = adafruit_tcs34725.TCS34725(i2c, address=addr)
        self.sensor.integration_time = 100
        self.sensor.gain = 4

    def read(self):
        readings = []
        for i in range(self.num_readings):
            GPIO.output(self.led_pin, GPIO.HIGH)
            time.sleep(0.3)
            r, g, b = self.sensor.color_rgb_bytes
            lux = self.sensor.lux
            GPIO.output(self.led_pin, GPIO.LOW)
            readings.append({
                "timestamp": datetime.now().isoformat(),
                "r": int(r),
                "g": int(g),
                "b": int(b),
                "lux": float(lux)
            })
            if i < self.num_readings - 1:
                time.sleep(self.read_spacing)
        return readings
