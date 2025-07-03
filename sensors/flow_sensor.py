import RPi.GPIO as GPIO
import time
from datetime import datetime

class FlowSensor:
    """Encapsulates flow sensor logic (YF-S201 or similar)."""
    def __init__(self, pin, pulses_per_litre):
        self.pin = pin
        self.pulses_per_litre = pulses_per_litre
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

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
        litres = pulse_count / self.pulses_per_litre
        return {
            "timestamp": datetime.now().isoformat(),
            "flow_pulses": pulse_count,
            "flow_litres": litres
        }
