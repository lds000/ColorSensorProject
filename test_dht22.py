"""
Minimal DHT22 Temperature/Humidity Reader for Raspberry Pi Zero W
Prints environment temperature and humidity to the console.
Wiring: DHT22 data pin to GPIO 4 (physical pin 7), 10kΩ pull-up to VCC.
"""
import Adafruit_DHT
import time

DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4  # BCM numbering

while True:
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    if humidity is not None and temperature is not None:
        print(f"Temperature: {temperature:.1f}°C  Humidity: {humidity:.1f}%")
    else:
        print("Failed to retrieve data from DHT22 sensor")
    time.sleep(2)
