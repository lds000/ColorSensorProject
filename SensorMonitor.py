import RPi.GPIO as GPIO
import time
from board import D22, D27, D4
from adafruit_bitbangio import I2C
import adafruit_tcs34725
from datetime import datetime, timedelta
import requests
import adafruit_dht
import paho.mqtt.client as mqtt
import json
import os
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# --- CONFIG ---
FLOW_SENSOR_PIN = 25  # BCM numbering
FLOW_PULSES_PER_LITRE = 450
LED_PIN = 17
NUM_COLOR_READINGS = 4
COLOR_READ_SPACING = 2  # seconds between color readings
GROUP_INTERVAL = 5  # minutes between groups
DHT_PIN = D4  # Use board pin object for AM2302/DHT22
WIND_SENSOR_PIN = 13  # BCM numbering for wind anemometer (using blue wire)

ERROR_LOG_FILE = "error_log.txt"
SOFTWARE_VERSION = "1.0.0"
AVG_PRESSURE_LOG_FILE = "avg_pressure_log.txt"
AVG_PRESSURE_INTERVAL = 300  # 5 minutes in seconds

# --- SETUP ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.output(LED_PIN, GPIO.LOW)
GPIO.setup(FLOW_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(WIND_SENSOR_PIN, GPIO.IN)

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

def poll_wind_anemometer(duration_s):
    pulse_count = 0
    last_state = GPIO.input(WIND_SENSOR_PIN)
    start = time.time()
    while time.time() - start < duration_s:
        current_state = GPIO.input(WIND_SENSOR_PIN)
        if last_state == 1 and current_state == 0:
            pulse_count += 1
        last_state = current_state
        time.sleep(0.001)
    return pulse_count

def log_error(msg):
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {msg}\n"
    print(log_entry.strip())
    try:
        # Read existing lines (if file exists)
        if os.path.exists(ERROR_LOG_FILE):
            with open(ERROR_LOG_FILE, "r") as f:
                lines = f.readlines()
        else:
            lines = []
        # Append new entry
        lines.append(log_entry)
        # Keep only the last 100 lines
        lines = lines[-100:]
        with open(ERROR_LOG_FILE, "w") as f:
            f.writelines(lines)
    except Exception as e:
        print(f"[FATAL] Could not write to error log: {e}")

def is_sane_flow(flow_pulses, flow_litres):
    return 0 <= flow_pulses < 10000 and 0.0 <= flow_litres < 100.0

def is_sane_wind(wind_speed):
    return 0.0 <= wind_speed < 50.0

def is_sane_temp(temp):
    return temp is not None and -40.0 < temp < 80.0

def is_sane_humidity(hum):
    return hum is not None and 0.0 <= hum <= 100.0

def calculate_flow_rate(flow_litres, duration_s):
    """
    Calculate the flow rate in liters per minute.

    Args:
        flow_litres (float): The amount of water in liters measured during the duration.
        duration_s (float): The duration in seconds over which the flow was measured.

    Returns:
        float: The flow rate in liters per minute.
    """
    if duration_s > 0:
        return (flow_litres / duration_s) * 60
    return 0

def main():
    print(f"[DEBUG] Starting SensorMonitor main loop... (version {SOFTWARE_VERSION})")
    sensor = init_color_sensor()
    print("[DEBUG] Color sensor initialized.")
    dht_device = adafruit_dht.DHT22(DHT_PIN)
    print("[DEBUG] DHT22 sensor initialized.")
    # --- ADS1115 Pressure Sensor Setup ---
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        pressure_chan = AnalogIn(ads, ADS.P0)  # Channel 0 for pressure sensor
        print("[DEBUG] ADS1115 initialized for pressure sensor.")
    except Exception as e:
        log_error(f"ADS1115 init error: {e}")
        pressure_chan = None
    last_color_time = time.time()
    last_dht_time = 0
    color_readings = []
    set_names = ["Set1", "Set2", "Set3"]  # Replace with your actual set names
    set_cycle_interval = 10  # seconds per set (for demo logic)

    # MQTT setup with reconnect/backoff
    mqtt_broker = "100.116.147.6"
    mqtt_port = 1883
    mqtt_client = mqtt.Client()
    connected = False
    retry_delay = 5
    while not connected:
        try:
            mqtt_client.connect(mqtt_broker, mqtt_port, 60)
            print("[DEBUG] MQTT connected successfully.")
            connected = True
        except Exception as e:
            log_error(f"MQTT connection failed: {e}")
            print(f"[INFO] Retrying MQTT connection in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

    try:
        while True:
            print("[DEBUG] --- New main loop iteration ---")
            # --- Sets (flow and pressure) reporting every second ---
            flow_pulse_count, flow_litres = poll_flow_meter(1.0)
            if not is_sane_flow(flow_pulse_count, flow_litres):
                log_error(f"Flow reading out of range: pulses={flow_pulse_count}, litres={flow_litres}")
                flow_pulse_count, flow_litres = None, None
                flow_rate_lpm = None
            else:
                flow_rate_lpm = calculate_flow_rate(flow_litres, 1.0)  # 1 second duration

            flow_timestamp = datetime.now().isoformat()
            # --- Pressure sensor read (ADS1115) ---
            pressure_psi = None
            pressure_kpa = None
            if pressure_chan is not None:
                try:
                    pressure_voltage = pressure_chan.voltage
                    if pressure_voltage is not None:
                        # 0.5V = 0 PSI, 4.5V = 100 PSI
                        pressure_psi = (pressure_voltage - 0.5) * (100 / (4.5 - 0.5))
                        pressure_psi = max(0, min(pressure_psi, 100))
                        pressure_kpa = pressure_psi * 6.89476
                        print(f"[DEBUG] Pressure: {pressure_voltage:.3f} V, {pressure_psi:.2f} PSI, {pressure_kpa:.2f} kPa")
                        # --- Collect for 5-min average ---
                        pressure_readings.append(pressure_psi)
                    else:
                        log_error("Pressure sensor voltage read as None.")
                except Exception as e:
                    log_error(f"Pressure sensor read error: {e}")
            # --- Log 5-min average pressure ---
            now_time = time.time()
            if now_time - last_pressure_avg_time >= AVG_PRESSURE_INTERVAL and pressure_readings:
                avg_psi = sum(pressure_readings) / len(pressure_readings)
                avg_timestamp = datetime.now().isoformat()
                try:
                    with open(AVG_PRESSURE_LOG_FILE, "a") as f:
                        f.write(f"{avg_timestamp}, avg_psi={avg_psi:.2f}, samples={len(pressure_readings)}\n")
                    print(f"[DEBUG] Logged 5-min avg PSI: {avg_psi:.2f} over {len(pressure_readings)} samples")
                except Exception as e:
                    log_error(f"Failed to write avg pressure log: {e}")
                pressure_readings.clear()
                last_pressure_avg_time = now_time
            sets_data = {
                "timestamp": flow_timestamp,
                "flow_pulses": flow_pulse_count,
                "flow_litres": flow_litres,
                "flow_rate_lpm": flow_rate_lpm,
                "pressure_psi": pressure_psi,
                "pressure_kpa": pressure_kpa,
                "version": SOFTWARE_VERSION
            }
            print(f"[DEBUG] Sets data: {sets_data}")
            try:
                mqtt_client.publish("sensors/sets", json.dumps(sets_data))
                print("[DEBUG] Published sets data to sensors/sets")
            except Exception as e:
                log_error(f"Failed to publish sets data: {e}")
            # --- Environment (temperature, humidity, wind, barometric pressure) reporting every second ---
            dht_data = read_dht_sensor(dht_device)
            # --- Wind speed calculation ---
            wind_pulses = poll_wind_anemometer(1.0)
            wind_speed = (wind_pulses / 20) * 1.75  # m/s, adjust formula if needed
            barometric_pressure = None
            if dht_data:
                temp = dht_data.get("temperature")
                hum = dht_data.get("humidity")
                if not is_sane_temp(temp):
                    log_error(f"Temperature out of range: {temp}")
                    temp = None
                if not is_sane_humidity(hum):
                    log_error(f"Humidity out of range: {hum}")
                    hum = None
                environment_data = {
                    "timestamp": dht_data["timestamp"],
                    "temperature": temp,
                    "humidity": hum,
                    "wind_speed": wind_speed,
                    "barometric_pressure": barometric_pressure,
                    "version": SOFTWARE_VERSION
                }
                print(f"[DEBUG] Environment data: {environment_data}")
                try:
                    mqtt_client.publish("sensors/environment", json.dumps(environment_data))
                    print("[DEBUG] Published environment data to sensors/environment")
                except Exception as e:
                    log_error(f"Failed to publish environment data: {e}")
            else:
                log_error("DHT22: No valid reading this second.")
            # --- Plant (moisture, soil temperature) reporting every 5 minutes ---
            now = time.time()
            if now - last_color_time >= GROUP_INTERVAL * 60:
                color_readings = []
                for i in range(NUM_COLOR_READINGS):
                    try:
                        data = read_color(sensor)
                        color_readings.append(data)
                        print(f"[DEBUG] Color reading {i+1}: {data}")
                    except Exception as e:
                        log_error(f"Color sensor read error: {e}")
                    if i < NUM_COLOR_READINGS - 1:
                        time.sleep(COLOR_READ_SPACING)
                if color_readings:
                    avg_b = sum(d['b'] for d in color_readings) / len(color_readings)
                    avg_lux = sum(d['lux'] for d in color_readings) / len(color_readings)
                    first_timestamp = color_readings[0]['timestamp']
                else:
                    avg_b, avg_lux, first_timestamp = None, None, datetime.now().isoformat()
                soil_temperature = None
                plant_data = {
                    "timestamp": first_timestamp,
                    "moisture": avg_b,
                    "lux": avg_lux,
                    "soil_temperature": soil_temperature,
                    "version": SOFTWARE_VERSION
                }
                print(f"[DEBUG] Plant data: {plant_data}")
                try:
                    mqtt_client.publish("sensors/plant", json.dumps(plant_data))
                    print("[DEBUG] Published plant data to sensors/plant")
                except Exception as e:
                    log_error(f"Failed to publish plant data: {e}")
                last_color_time = now
    except KeyboardInterrupt:
        print("[INFO] Exiting...")
    finally:
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.cleanup()
        mqtt_client.disconnect()
        print("[INFO] GPIO cleaned up and MQTT disconnected.")

if __name__ == "__main__":
    main()
