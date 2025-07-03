import RPi.GPIO as GPIO
import time
from datetime import datetime

class WindSensor:
    """Encapsulates wind speed sensor logic (reed switch anemometer)."""
    def __init__(self, pin):
        self.pin = pin
        GPIO.setup(self.pin, GPIO.IN)

    def read(self, duration_s=1.0):
        pulse_count = 0
        last_state = GPIO.input(self.pin)
        start = time.time()
        while time.time() - start < duration_s:
            current_state = GPIO.input(self.pin)
            if last_state == 1 and current_state == 0:
                pulse_count += 1
            last_state = current_state
            time.sleep(0.001)
        speed = (pulse_count / 20) * 1.75
        return {
            "timestamp": datetime.now().isoformat(),
            "wind_pulses": pulse_count,
            "wind_speed": speed
        }
