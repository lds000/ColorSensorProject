import RPi.GPIO as GPIO
import time
from board import D22, D27
from adafruit_bitbangio import I2C
import adafruit_tcs34725
from datetime import datetime, timedelta

# --- CONFIG ---
FLOW_SENSOR_PIN = 25  # BCM numbering
FLOW_PULSES_PER_LITRE = 450
LED_PIN = 17
NUM_COLOR_READINGS = 4
COLOR_READ_SPACING = 2  # seconds between color readings
GROUP_INTERVAL = 5  # minutes between groups

# --- SETUP ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.output(LED_PIN, GPIO.LOW)
GPIO.setup(FLOW_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def init_color_sensor():
    i2c = I2C(scl=D22, sda=D27)
    while not i2c.try_lock():
        time.sleep(0.1)
    devices = i2c.scan()
    i2c.unlock()
    addr = 0x29 if 0x29 in devices else (0x2A if 0x2A in devices else None)
    if addr is None:
        print("Color sensor not found on I2C")
        GPIO.output(LED_PIN, GPIO.LOW)
        raise RuntimeError("Color sensor not found on I2C")
    sensor = adafruit_tcs34725.TCS34725(i2c, address=addr)
    sensor.integration_time = 100
    sensor.gain = 4
    print(f"Color sensor initialized at address {hex(addr)}")
    return sensor

def read_color(sensor):
    GPIO.output(LED_PIN, GPIO.HIGH)
    time.sleep(0.3)
    r, g, b = sensor.color_rgb_bytes
    lux = sensor.lux
    GPIO.output(LED_PIN, GPIO.LOW)
    return {
        "timestamp": datetime.now().isoformat(),
        "r": int(r),
        "g": int(g),
        "b": int(b),
        "lux": float(lux)
    }

def poll_flow_meter(duration_s):
    pulse_count = 0
    last_state = GPIO.input(FLOW_SENSOR_PIN)
    start = time.time()
    while time.time() - start < duration_s:
        current_state = GPIO.input(FLOW_SENSOR_PIN)
        if last_state == 1 and current_state == 0:
            pulse_count += 1
        last_state = current_state
        time.sleep(0.001)
    litres = pulse_count / FLOW_PULSES_PER_LITRE
    return pulse_count, litres

def main():
    sensor = init_color_sensor()
    last_color_time = time.time()
    color_readings = []
    try:
        while True:
            # --- Flow reporting every second ---
            flow_pulse_count, flow_litres = poll_flow_meter(1.0)
            flow_timestamp = datetime.now().isoformat()
            print(f"Flow: timestamp={flow_timestamp}, pulses={flow_pulse_count}, litres={flow_litres:.4f}")

            # --- Moisture (color) reporting every 5 minutes ---
            now = time.time()
            if now - last_color_time >= GROUP_INTERVAL * 60:
                print("--- Starting new color group ---")
                color_readings = []
                for i in range(NUM_COLOR_READINGS):
                    data = read_color(sensor)
                    color_readings.append(data)
                    print(f"Color reading {i+1}: {data}")
                    if i < NUM_COLOR_READINGS - 1:
                        time.sleep(COLOR_READ_SPACING)
                avg_b = sum(d['b'] for d in color_readings) / NUM_COLOR_READINGS
                avg_lux = sum(d['lux'] for d in color_readings) / NUM_COLOR_READINGS
                first_timestamp = color_readings[0]['timestamp']
                print(f"Moisture: timestamp={first_timestamp}, avg_b={avg_b:.2f}, avg_lux={avg_lux:.2f}")
                last_color_time = now
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.cleanup()
        print("GPIO cleaned up.")

if __name__ == "__main__":
    main()
