import RPi.GPIO as GPIO
import time

# GPIO pin connected to the wind speed transmitter's pulse output (blue wire)
WIND_SENSOR_PIN = 13  # BCM numbering for wind anemometer

def poll_wind_anemometer(duration_s):
    """
    Polls the wind anemometer for a given duration and counts pulses.
    Returns the number of pulses detected.
    """
    pulse_count = 0
    last_state = GPIO.input(WIND_SENSOR_PIN)
    start = time.time()
    while time.time() - start < duration_s:
        current_state = GPIO.input(WIND_SENSOR_PIN)
        if last_state == 1 and current_state == 0:
            pulse_count += 1
        last_state = current_state
        time.sleep(0.001)  # 1ms polling
    return pulse_count

if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(WIND_SENSOR_PIN, GPIO.IN)
    print("Wind speed test started. Press Ctrl+C to stop.")
    try:
        while True:
            duration = 1.0  # seconds
            pulses = poll_wind_anemometer(duration)
            # 20 pulses = 1 rotation = 1.75 m/s
            wind_speed_mps = (pulses / 20) * 1.75  # m/s
            wind_speed_mph = wind_speed_mps * 2.23694  # 1 m/s = 2.23694 mph
            print(f"Pulses: {pulses}, Wind speed: {wind_speed_mph:.2f} mph ({wind_speed_mps:.2f} m/s)")
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
    finally:
        GPIO.cleanup()
