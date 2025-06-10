import RPi.GPIO as GPIO
import time

FLOW_SENSOR_PIN = 25  # BCM numbering

GPIO.setmode(GPIO.BCM)
GPIO.setup(FLOW_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

pulse_count = 0

def flow_callback(channel):
    global pulse_count
    pulse_count += 1
    print(f"Pulse detected! Total: {pulse_count}")

try:
    GPIO.add_event_detect(FLOW_SENSOR_PIN, GPIO.FALLING, callback=flow_callback)
    print(f"Listening for pulses on GPIO {FLOW_SENSOR_PIN}. Press Ctrl+C to exit.")
    while True:
        time.sleep(1)
        # Optionally print pulse count every second
        print(f"Pulse count: {pulse_count}")
except KeyboardInterrupt:
    print("Exiting...")
finally:
    GPIO.cleanup()
    print("GPIO cleaned up.")
