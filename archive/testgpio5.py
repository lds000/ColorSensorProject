import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(13, GPIO.IN)

try:
    while True:
        print("GPIO 13 state:", GPIO.input(13))
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    GPIO.cleanup()
