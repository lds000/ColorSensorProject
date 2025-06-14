import RPi.GPIO as GPIO
import time

PULSE_PIN = 13  # GPIO pin to poll

GPIO.setmode(GPIO.BCM)
GPIO.setup(PULSE_PIN, GPIO.IN)

print("Polling GPIO 13 for pulses. Press Ctrl+C to stop.")
try:
    while True:
        pulse_count = 0
        last_state = GPIO.input(PULSE_PIN)
        start = time.time()
        while time.time() - start < 1.0:  # 1 second interval
            current_state = GPIO.input(PULSE_PIN)
            if last_state == 1 and current_state == 0:
                pulse_count += 1
            last_state = current_state
            time.sleep(0.001)  # 1 ms polling interval
        print(f"Pulses in 1s: {pulse_count}")
except KeyboardInterrupt:
    print("\nTest stopped by user.")
finally:
    GPIO.cleanup()
