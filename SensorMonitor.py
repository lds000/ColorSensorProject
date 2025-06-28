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
AVG_WIND_LOG_FILE = "avg_wind_log.txt"
AVG_WIND_INTERVAL = 300  # 5 minutes in seconds
AVG_TEMPERATURE_LOG_FILE = "avg_temperature_log.txt"
AVG_TEMPERATURE_INTERVAL = 300  # 5 minutes in seconds
AVG_FLOW_LOG_FILE = "avg_flow_log.txt"
AVG_FLOW_INTERVAL = 300  # 5 minutes in seconds

# --- LOAD CONFIG ---
CONFIG_FILE = "config.json"
def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"[FATAL] Could not load config.json: {e}")
        return {}

config = load_config()
SENSOR_NAME = config.get("sensor_name", "UnknownSensor")
ENABLE_FLOW_SENSOR = config.get("enable_flow_sensor", True)
ENABLE_DHT22 = config.get("enable_dht22", True)
ENABLE_PRESSURE_SENSOR = config.get("enable_pressure_sensor", True)
ENABLE_WIND_SENSOR = config.get("enable_wind_sensor", True)
ENABLE_COLOR_SENSOR = config.get("enable_color_sensor", True)

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

def trim_stdout_log(max_lines=1000):
    """
    Trims stdout_log.txt to the last max_lines lines.
    """
    log_file = "stdout_log.txt"
    if not os.path.exists(log_file):
        return
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            with open(log_file, "w") as f:
                f.writelines(lines[-max_lines:])
    except Exception as e:
        log_error(f"Failed to trim stdout_log.txt: {e}")

def trim_color_log(max_lines=1000):
    """
    Trims color_log.txt to the last max_lines lines.
    """
    log_file = "color_log.txt"
    if not os.path.exists(log_file):
        return
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            with open(log_file, "w") as f:
                f.writelines(lines[-max_lines:])
    except Exception as e:
        log_error(f"Failed to trim color_log.txt: {e}")

# --- Wind direction calibration constants (from wind_direction_test.py) ---
CAL_N_RAW = 14350  # North
CAL_E_RAW = 21755  # East
COMPASS_LABELS = [
    "N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"
]

def raw_to_degrees(raw):
    """
    Map raw ADC value to degrees using calibration points.
    14350 (N) -> 0°, 21755 (E) -> 90°, wraps for other directions.
    """
    if raw < CAL_N_RAW:
        deg = 270 + (raw / (CAL_N_RAW - 655)) * 90
        if deg > 360:
            deg -= 360
        return deg
    elif raw <= CAL_E_RAW:
        deg = (raw - CAL_N_RAW) * 90 / (CAL_E_RAW - CAL_N_RAW)
        return max(0, deg)
    else:
        deg = 90 + (raw - CAL_E_RAW) * 270 / (32767 - CAL_E_RAW)
        if deg > 360:
            deg -= 360
        return deg

def degrees_to_compass(degrees):
    idx = int((degrees + 22.5) // 45)
    return COMPASS_LABELS[idx]

def main():
    print(f"[DEBUG] Starting SensorMonitor main loop... (version {SOFTWARE_VERSION})")
    # --- Sensor initialization based on config ---
    sensor = None
    if ENABLE_COLOR_SENSOR:
        try:
            sensor = init_color_sensor()
            print("[DEBUG] Color sensor initialized.")
        except Exception as e:
            log_error(f"Color sensor init error: {e}")
            sensor = None
    dht_device = None
    if ENABLE_DHT22:
        try:
            dht_device = adafruit_dht.DHT22(DHT_PIN)
            print("[DEBUG] DHT22 sensor initialized.")
        except Exception as e:
            log_error(f"DHT22 init error: {e}")
            dht_device = None
    # --- ADS1115 Pressure Sensor Setup ---
    ads = None
    pressure_chan = None
    if ENABLE_PRESSURE_SENSOR:
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
    # --- Initialize pressure and wind averaging variables at the top of main() ---
    global pressure_readings, last_pressure_avg_time
    pressure_readings = []
    last_pressure_avg_time = time.time()
    global wind_speed_readings, last_wind_avg_time
    wind_speed_readings = []
    last_wind_avg_time = time.time()
    # --- Add temperature and flow averaging variables ---
    global temperature_readings, last_temperature_avg_time
    temperature_readings = []
    last_temperature_avg_time = time.time()
    global flow_litres_readings, last_flow_avg_time
    flow_litres_readings = []
    last_flow_avg_time = time.time()
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
            pressure_psi = None
            pressure_kpa = None
            print("[DEBUG] --- New main loop iteration ---")
            # --- Sets (flow and pressure) reporting every second ---
            flow_pulse_count, flow_litres = None, None
            flow_rate_lpm = None
            flow_timestamp = datetime.now().isoformat()
            if ENABLE_FLOW_SENSOR:
                flow_pulse_count, flow_litres = poll_flow_meter(1.0)
                if not is_sane_flow(flow_pulse_count, flow_litres):
                    log_error(f"Flow reading out of range: pulses={flow_pulse_count}, litres={flow_litres}")
                    flow_pulse_count, flow_litres = None, None
                    flow_rate_lpm = None
                else:
                    flow_rate_lpm = calculate_flow_rate(flow_litres, 1.0)
                    flow_litres_readings.append(flow_litres)
            # --- Pressure sensor read (ADS1115) ---
            if ENABLE_PRESSURE_SENSOR and pressure_chan is not None:
                try:
                    pressure_voltage = pressure_chan.voltage
                    if pressure_voltage is not None:
                        pressure_psi = (pressure_voltage - 0.5) * (100 / (4.5 - 0.5))
                        pressure_psi = max(0, min(pressure_psi, 100))
                        pressure_kpa = pressure_psi * 6.89476
                        print(f"[DEBUG] Pressure: {pressure_voltage:.3f} V, {pressure_psi:.2f} PSI, {pressure_kpa:.2f} kPa")
                        pressure_readings.append(pressure_psi)
                    else:
                        log_error("Pressure sensor voltage read as None.")
                except Exception as e:
                    log_error(f"Pressure sensor read error: {e}")
            # --- Log 5-min average flow ---
            now_time = time.time()
            if now_time - last_flow_avg_time >= AVG_FLOW_INTERVAL:
                if flow_litres_readings:
                    avg_flow = sum(flow_litres_readings) / len(flow_litres_readings)
                    avg_timestamp = datetime.now().isoformat()
                    try:
                        with open(AVG_FLOW_LOG_FILE, "a") as f:
                            f.write(f"{avg_timestamp}, avg_flow={avg_flow:.4f}, samples={len(flow_litres_readings)}\n")
                        print(f"[DEBUG] Logged 5-min avg flow: {avg_flow:.4f} L over {len(flow_litres_readings)} samples")
                    except Exception as e:
                        log_error(f"Failed to write avg flow log: {e}")
                    flow_litres_readings.clear()
                else:
                    log_error("[FLOW AVG] No valid flow readings to average in last 5 minutes.")
                last_flow_avg_time = now_time
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
                "sensor_name": SENSOR_NAME,
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
            dht_data = None
            if ENABLE_DHT22 and dht_device is not None:
                dht_data = read_dht_sensor(dht_device)
            wind_speed = None
            wind_direction_deg = None
            wind_direction_compass = None
            if ENABLE_WIND_SENSOR:
                wind_pulses = poll_wind_anemometer(1.0)
                wind_speed = (wind_pulses / 20) * 1.75
                wind_speed_readings.append(wind_speed)
                if ads is not None:
                    try:
                        wind_dir_chan = AnalogIn(ads, ADS.P1)
                        wind_dir_raw = wind_dir_chan.value
                        wind_direction_deg = raw_to_degrees(wind_dir_raw)
                        wind_direction_compass = degrees_to_compass(wind_direction_deg)
                        print(f"[DEBUG] Wind direction: raw={wind_dir_raw}, {wind_direction_deg:.1f}° ({wind_direction_compass})")
                    except Exception as e:
                        log_error(f"Wind direction read error: {e}")
            barometric_pressure = None
            temp = None
            hum = None
            if dht_data:
                temp = dht_data.get("temperature")
                hum = dht_data.get("humidity")
                if not is_sane_temp(temp):
                    log_error(f"Temperature out of range: {temp}")
                    temp = None
                else:
                    temperature_readings.append(temp)
                if not is_sane_humidity(hum):
                    log_error(f"Humidity out of range: {hum}")
                    hum = None
            environment_data = {
                "sensor_name": SENSOR_NAME,
                "timestamp": dht_data["timestamp"] if dht_data else datetime.now().isoformat(),
                "temperature": temp,
                "humidity": hum,
                "wind_speed": wind_speed,
                "wind_direction_deg": wind_direction_deg,
                "wind_direction_compass": wind_direction_compass,
                "barometric_pressure": barometric_pressure,
                "version": SOFTWARE_VERSION
            }
            print(f"[DEBUG] Environment data: {environment_data}")
            try:
                mqtt_client.publish("sensors/environment", json.dumps(environment_data))
                print("[DEBUG] Published environment data to sensors/environment")
            except Exception as e:
                log_error(f"Failed to publish environment data: {e}")
            # --- Plant (moisture, soil temperature) reporting every 5 minutes ---
            now = time.time()
            if ENABLE_COLOR_SENSOR and sensor is not None and now - last_color_time >= GROUP_INTERVAL * 60:
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
                    "sensor_name": SENSOR_NAME,
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
                with open("color_log.txt", "a") as f:
                    f.write(json.dumps(plant_data) + "\n")
                trim_color_log(1000)
                last_color_time = now
            # --- Trim stdout_log.txt to 1000 lines ---
            trim_stdout_log(1000)
    except KeyboardInterrupt:
        print("[INFO] Exiting...")
    finally:
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.cleanup()
        mqtt_client.disconnect()
        print("[INFO] GPIO cleaned up and MQTT disconnected.")

if __name__ == "__main__":
    main()
