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
from collections import defaultdict

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

# --- Modularized Sensor Reading Functions ---
def get_flow_reading():
    """Read flow sensor if enabled. Returns dict with timestamp, pulses, litres, rate."""
    if not ENABLE_FLOW_SENSOR:
        return {"timestamp": datetime.now().isoformat(), "flow_pulses": None, "flow_litres": None, "flow_rate_lpm": None}
    pulses, litres = poll_flow_meter(1.0)
    if not is_sane_flow(pulses, litres):
        log_error(f"Flow reading out of range: pulses={pulses}, litres={litres}")
        return {"timestamp": datetime.now().isoformat(), "flow_pulses": None, "flow_litres": None, "flow_rate_lpm": None}
    rate = calculate_flow_rate(litres, 1.0)
    return {"timestamp": datetime.now().isoformat(), "flow_pulses": pulses, "flow_litres": litres, "flow_rate_lpm": rate}

def get_pressure_reading(pressure_chan):
    """Read pressure sensor if enabled. Returns dict with timestamp, psi, kpa."""
    if not ENABLE_PRESSURE_SENSOR or pressure_chan is None:
        return {"timestamp": datetime.now().isoformat(), "pressure_psi": None, "pressure_kpa": None}
    try:
        voltage = pressure_chan.voltage
        if voltage is not None:
            psi = (voltage - 0.5) * (100 / (4.5 - 0.5))
            psi = max(0, min(psi, 100))
            kpa = psi * 6.89476
            return {"timestamp": datetime.now().isoformat(), "pressure_psi": psi, "pressure_kpa": kpa}
        else:
            log_error("Pressure sensor voltage read as None.")
    except Exception as e:
        log_error(f"Pressure sensor read error: {e}")
    return {"timestamp": datetime.now().isoformat(), "pressure_psi": None, "pressure_kpa": None}

def get_wind_reading(ads):
    """Read wind speed and direction if enabled. Returns dict with timestamp, speed, deg, compass."""
    if not ENABLE_WIND_SENSOR:
        return {"timestamp": datetime.now().isoformat(), "wind_speed": None, "wind_direction_deg": None, "wind_direction_compass": None}
    wind_pulses = poll_wind_anemometer(1.0)
    speed = (wind_pulses / 20) * 1.75
    deg = None
    compass = None
    if ads is not None:
        try:
            wind_dir_chan = AnalogIn(ads, ADS.P1)
            wind_dir_raw = wind_dir_chan.value
            deg = raw_to_degrees(wind_dir_raw)
            compass = degrees_to_compass(deg)
        except Exception as e:
            log_error(f"Wind direction read error: {e}")
    return {"timestamp": datetime.now().isoformat(), "wind_speed": speed, "wind_direction_deg": deg, "wind_direction_compass": compass}

def get_dht22_reading(dht_device):
    """Read DHT22 if enabled. Returns dict with timestamp, temp, humidity."""
    if not ENABLE_DHT22 or dht_device is None:
        return {"timestamp": datetime.now().isoformat(), "temperature": None, "humidity": None}
    data = read_dht_sensor(dht_device)
    if not data:
        log_error("DHT22: No valid reading this second.")
        return {"timestamp": datetime.now().isoformat(), "temperature": None, "humidity": None}
    temp = data.get("temperature")
    hum = data.get("humidity")
    if not is_sane_temp(temp):
        log_error(f"Temperature out of range: {temp}")
        temp = None
    if not is_sane_humidity(hum):
        log_error(f"Humidity out of range: {hum}")
        hum = None
    return {"timestamp": data["timestamp"], "temperature": temp, "humidity": hum}

def get_color_reading(sensor):
    """Read color sensor if enabled. Returns dict with timestamp, b, lux."""
    if not ENABLE_COLOR_SENSOR or sensor is None:
        return {"timestamp": datetime.now().isoformat(), "moisture": None, "lux": None}
    readings = []
    for i in range(NUM_COLOR_READINGS):
        try:
            data = read_color(sensor)
            readings.append(data)
        except Exception as e:
            log_error(f"Color sensor read error: {e}")
        if i < NUM_COLOR_READINGS - 1:
            time.sleep(COLOR_READ_SPACING)
    if readings:
        avg_b = sum(d['b'] for d in readings) / len(readings)
        avg_lux = sum(d['lux'] for d in readings) / len(readings)
        ts = readings[0]['timestamp']
    else:
        avg_b, avg_lux, ts = None, None, datetime.now().isoformat()
    return {"timestamp": ts, "moisture": avg_b, "lux": avg_lux}

# --- Reporting/Logging Functions ---
def publish_mqtt(client, topic, payload):
    """Publish a JSON payload to MQTT."""
    try:
        client.publish(topic, json.dumps(payload))
        print(f"[DEBUG] Published to {topic}: {payload}")
    except Exception as e:
        log_error(f"Failed to publish to {topic}: {e}")

def log_5min_average(logfile, avg_value, label, sample_count):
    """Append a 5-min average to a log file."""
    try:
        with open(logfile, "a") as f:
            f.write(f"{datetime.now().isoformat()}, {label}={avg_value}, samples={sample_count}\n")
        print(f"[DEBUG] Logged 5-min avg {label}: {avg_value} over {sample_count} samples")
    except Exception as e:
        log_error(f"Failed to write avg {label} log: {e}")

# --- Main Loop with Scheduler ---
def main():
    print(f"[DEBUG] Starting SensorMonitor main loop... (version {SOFTWARE_VERSION})")
    # Sensor initialization
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
    ads = None
    pressure_chan = None
    if ENABLE_PRESSURE_SENSOR:
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            ads = ADS.ADS1115(i2c)
            pressure_chan = AnalogIn(ads, ADS.P0)
            print("[DEBUG] ADS1115 initialized for pressure sensor.")
        except Exception as e:
            log_error(f"ADS1115 init error: {e}")
            pressure_chan = None
    # MQTT setup
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
    # Scheduler state
    last_run = defaultdict(lambda: 0)
    readings_accum = defaultdict(list)
    try:
        while True:
            now = time.time()
            # --- Step 1: Collect all sensor readings ---
            flow = get_flow_reading()
            pressure = get_pressure_reading(pressure_chan)
            wind = get_wind_reading(ads)
            dht = get_dht22_reading(dht_device)
            # --- Step 2: Publish/report per-second data ---
            sets_data = {
                "sensor_name": SENSOR_NAME,
                "timestamp": flow["timestamp"],
                "flow_pulses": flow["flow_pulses"],
                "flow_litres": flow["flow_litres"],
                "flow_rate_lpm": flow["flow_rate_lpm"],
                "pressure_psi": pressure["pressure_psi"],
                "pressure_kpa": pressure["pressure_kpa"],
                "version": SOFTWARE_VERSION
            }
            publish_mqtt(mqtt_client, "sensors/sets", sets_data)
            environment_data = {
                "sensor_name": SENSOR_NAME,
                "timestamp": dht["timestamp"],
                "temperature": dht["temperature"],
                "humidity": dht["humidity"],
                "wind_speed": wind["wind_speed"],
                "wind_direction_deg": wind["wind_direction_deg"],
                "wind_direction_compass": wind["wind_direction_compass"],
                "barometric_pressure": None,
                "version": SOFTWARE_VERSION
            }
            publish_mqtt(mqtt_client, "sensors/environment", environment_data)
            # --- Step 3: Accumulate for 5-min averages ---
            if flow["flow_litres"] is not None:
                readings_accum["flow"].append(flow["flow_litres"])
            if pressure["pressure_psi"] is not None:
                readings_accum["pressure"].append(pressure["pressure_psi"])
            if wind["wind_speed"] is not None:
                readings_accum["wind"].append(wind["wind_speed"])
            if dht["temperature"] is not None:
                readings_accum["temperature"].append(dht["temperature"])
            # --- Step 4: 5-min average logging (scheduler pattern) ---
            if now - last_run["flow_avg"] >= AVG_FLOW_INTERVAL:
                if readings_accum["flow"]:
                    avg_flow = sum(readings_accum["flow"]) / len(readings_accum["flow"])
                    log_5min_average(AVG_FLOW_LOG_FILE, f"{avg_flow:.4f}", "avg_flow", len(readings_accum["flow"]))
                    readings_accum["flow"] = []
                last_run["flow_avg"] = now
            if now - last_run["pressure_avg"] >= AVG_PRESSURE_INTERVAL:
                if readings_accum["pressure"]:
                    avg_psi = sum(readings_accum["pressure"]) / len(readings_accum["pressure"])
                    log_5min_average(AVG_PRESSURE_LOG_FILE, f"{avg_psi:.2f}", "avg_psi", len(readings_accum["pressure"]))
                    readings_accum["pressure"] = []
                last_run["pressure_avg"] = now
            if now - last_run["wind_avg"] >= AVG_WIND_INTERVAL:
                if readings_accum["wind"]:
                    avg_wind = sum(readings_accum["wind"]) / len(readings_accum["wind"])
                    log_5min_average(AVG_WIND_LOG_FILE, f"{avg_wind:.2f}", "avg_wind", len(readings_accum["wind"]))
                    readings_accum["wind"] = []
                last_run["wind_avg"] = now
            if now - last_run["temperature_avg"] >= AVG_TEMPERATURE_INTERVAL:
                if readings_accum["temperature"]:
                    avg_temp = sum(readings_accum["temperature"]) / len(readings_accum["temperature"])
                    log_5min_average(AVG_TEMPERATURE_LOG_FILE, f"{avg_temp:.2f}", "avg_temp", len(readings_accum["temperature"]))
                    readings_accum["temperature"] = []
                last_run["temperature_avg"] = now
            # --- Step 5: Plant/color reporting every GROUP_INTERVAL minutes ---
            if ENABLE_COLOR_SENSOR and sensor is not None and now - last_run["color"] >= GROUP_INTERVAL * 60:
                color = get_color_reading(sensor)
                plant_data = {
                    "sensor_name": SENSOR_NAME,
                    "timestamp": color["timestamp"],
                    "moisture": color["moisture"],
                    "lux": color["lux"],
                    "soil_temperature": None,
                    "version": SOFTWARE_VERSION
                }
                publish_mqtt(mqtt_client, "sensors/plant", plant_data)
                with open("color_log.txt", "a") as f:
                    f.write(json.dumps(plant_data) + "\n")
                trim_color_log(1000)
                last_run["color"] = now
            # --- Step 6: Trim stdout_log.txt ---
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
