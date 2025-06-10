import RPi.GPIO as GPIO
import time

FLOW_SENSOR_PIN = 25  # BCM numbering
GPIO.setmode(GPIO.BCM)
GPIO.setup(FLOW_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

pulse_count = 0
last_state = GPIO.input(FLOW_SENSOR_PIN)

print(f"Polling for pulses on GPIO {FLOW_SENSOR_PIN}. Press Ctrl+C to exit.")
try:
    while True:
        current_state = GPIO.input(FLOW_SENSOR_PIN)
        if last_state == 1 and current_state == 0:
            pulse_count += 1
            print(f"Pulse detected! Total: {pulse_count}")
        last_state = current_state
        time.sleep(0.001)  # 1 ms polling interval
except KeyboardInterrupt:
    print("Exiting...")
finally:
    GPIO.cleanup()
    print("GPIO cleaned up.")
