import adafruit_dht
from datetime import datetime
import time

class DHT22Sensor:
    """Encapsulates DHT22 temperature/humidity sensor logic."""
    def __init__(self, pin):
        self.device = adafruit_dht.DHT22(pin)

    def read(self, retries=3):
        for attempt in range(retries):
            try:
                temperature = self.device.temperature
                humidity = self.device.humidity
                return {
                    "timestamp": datetime.now().isoformat(),
                    "temperature": temperature,
                    "humidity": humidity
                }
            except Exception:
                time.sleep(0.3)
        return {
            "timestamp": datetime.now().isoformat(),
            "temperature": None,
            "humidity": None
        }
