import RPi.GPIO as GPIO
import time
from board import D22, D27, D4
from adafruit_bitbangio import I2C
import adafruit_tcs34725
from datetime import datetime, timedelta
import requests
import adafruit_dht

# --- CONFIG ---
FLOW_SENSOR_PIN = 25  # BCM numbering
FLOW_PULSES_PER_LITRE = 450
LED_PIN = 17
NUM_COLOR_READINGS = 4
COLOR_READ_SPACING = 2  # seconds between color readings
GROUP_INTERVAL = 5  # minutes between groups
DHT_PIN = D4  # Use board pin object for AM2302/DHT22

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

def read_dht_sensor(dht_device):
    try:
        temperature = dht_device.temperature
        humidity = dht_device.humidity
        return {
            "timestamp": datetime.now().isoformat(),
            "temperature": temperature,
            "humidity": humidity
        }
    except Exception as e:
        print(f"DHT22 read error: {e}")
        return None

def main():
    sensor = init_color_sensor()
    dht_device = adafruit_dht.DHT22(DHT_PIN)
    last_color_time = time.time()
    last_dht_time = 0
    color_readings = []
    set_names = ["Set1", "Set2", "Set3"]  # Replace with your actual set names
    set_cycle_interval = 10  # seconds per set (for demo logic)
    try:
        while True:
            # --- Sets (flow and pressure) reporting every second ---
            flow_pulse_count, flow_litres = poll_flow_meter(1.0)
            flow_timestamp = datetime.now().isoformat()
            # TODO: Replace this with actual pressure sensor reading
            pressure_kpa = None  # e.g., read_pressure_sensor()
            sets_data = {
                "timestamp": flow_timestamp,
                "flow_pulses": flow_pulse_count,
                "flow_litres": flow_litres,
                "pressure_kpa": pressure_kpa
            }
            print(f"Sets: {sets_data}")
            try:
                requests.post("http://127.0.0.1:8000/sets-latest", json=sets_data, timeout=2)
            except Exception as e:
                print(f"Failed to POST sets data: {e}")

            # --- Environment (temperature, humidity, wind, barometric pressure) reporting every second ---
            dht_data = read_dht_sensor(dht_device)
            # TODO: Add wind speed and barometric pressure readings
            wind_speed = None
            barometric_pressure = None
            if dht_data:
                environment_data = {
                    "timestamp": dht_data["timestamp"],
                    "temperature": dht_data.get("temperature"),
                    "humidity": dht_data.get("humidity"),
                    "wind_speed": wind_speed,
                    "barometric_pressure": barometric_pressure
                }
                print(f"Environment: {environment_data}")
                try:
                    requests.post("http://127.0.0.1:8000/environment-latest", json=environment_data, timeout=2)
                except Exception as e:
                    print(f"Failed to POST environment data: {e}")
            else:
                print("DHT22: No valid reading this second.")

            # --- Plant (moisture, soil temperature) reporting every 5 minutes ---
            now = time.time()
            if now - last_color_time >= GROUP_INTERVAL * 60:
                print("--- Starting new plant group ---")
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
                # TODO: Add soil temperature reading
                soil_temperature = None
                plant_data = {
                    "timestamp": first_timestamp,
                    "moisture": avg_b,
                    "lux": avg_lux,
                    "soil_temperature": soil_temperature
                }
                print(f"Plant: {plant_data}")
                try:
                    requests.post("http://127.0.0.1:8000/plant-latest", json=plant_data, timeout=2)
                except Exception as e:
                    print(f"Failed to POST plant data: {e}")
                last_color_time = now
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.cleanup()
        print("GPIO cleaned up.")

if __name__ == "__main__":
    main()
