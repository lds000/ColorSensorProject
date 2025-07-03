import RPi.GPIO as GPIO
import time
from board import D22, D27, D4
from adafruit_bitbangio import I2C
import adafruit_tcs34725
from datetime import datetime, timedelta
import requests
import adafruit_dht
import json
import os
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from collections import defaultdict
from sensors.flow_sensor import FlowSensor
from sensors.color_sensor import ColorSensor
from sensors.dht22_sensor import DHT22Sensor
from sensors.wind_sensor import WindSensor
from sensors.pressure_sensor import PressureSensor
from sensors.wind_direction_sensor import WindDirectionSensor
from services.mqtt_publisher import MqttPublisher
from services.log_manager import LogManager

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
AVG_WIND_DIRECTION_LOG_FILE = "avg_wind_direction_log.txt"

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
        log_mgr.log_error(f"Flow reading out of range: pulses={pulses}, litres={litres}")
        return {"timestamp": datetime.now().isoformat(), "flow_pulses": None, "flow_litres": None, "flow_rate_lpm": None}
    rate = calculate_flow_rate(litres, 1.0)
    return {"timestamp": datetime.now().isoformat(), "flow_pulses": pulses, "flow_litres": litres, "flow_rate_lpm": rate}

def get_pressure_reading(pressure_sensor):
    """Read pressure sensor if enabled. Returns dict with timestamp, psi, kpa."""
    if not ENABLE_PRESSURE_SENSOR or pressure_sensor is None:
        return {"timestamp": datetime.now().isoformat(), "pressure_psi": None, "pressure_kpa": None}
    try:
        pressure = pressure_sensor.read()
        return {
            "timestamp": pressure["timestamp"],
            "pressure_psi": pressure["pressure_psi"],
            "pressure_kpa": pressure["pressure_kpa"]
        }
    except Exception as e:
        log_mgr.log_error(f"Pressure sensor read error: {e}")
    return {"timestamp": datetime.now().isoformat(), "pressure_psi": None, "pressure_kpa": None}

def get_wind_reading(wind_sensor):
    """Read wind speed and direction if enabled. Returns dict with timestamp, speed, deg, compass."""
    if not ENABLE_WIND_SENSOR:
        return {"timestamp": datetime.now().isoformat(), "wind_speed": None, "wind_direction_deg": None, "wind_direction_compass": None}
    wind = wind_sensor.read()
    # --- Wind direction reading ---
    if wind_direction_sensor is not None:
        wind_dir = wind_direction_sensor.read()
        wind["wind_direction_deg"] = wind_dir["wind_direction_deg"]
        wind["wind_direction_compass"] = wind_dir["wind_direction_compass"]
    else:
        wind["wind_direction_deg"] = None
        wind["wind_direction_compass"] = None
    return {"timestamp": datetime.now().isoformat(), "wind_speed": wind["wind_speed"], "wind_direction_deg": wind["wind_direction_deg"], "wind_direction_compass": wind["wind_direction_compass"]}

def get_dht22_reading(dht_device):
    """Read DHT22 if enabled. Returns dict with timestamp, temp, humidity. Retries up to 3 times if needed."""
    if not ENABLE_DHT22 or dht_device is None:
        return {"timestamp": datetime.now().isoformat(), "temperature": None, "humidity": None}
    attempts = 3
    for attempt in range(attempts):
        data = read_dht_sensor(dht_device)
        if data and is_sane_temp(data.get("temperature")) and is_sane_humidity(data.get("humidity")):
            temp = data.get("temperature")
            hum = data.get("humidity")
            return {"timestamp": data["timestamp"], "temperature": temp, "humidity": hum}
        time.sleep(0.3)
    log_mgr.log_error("DHT22: No valid reading this second after 3 attempts.")
    return {"timestamp": datetime.now().isoformat(), "temperature": None, "humidity": None}

# --- Reporting/Logging Functions ---
def log_5min_average(logfile, avg_value, label, sample_count):
    """Append a 5-min average to a log file."""
    try:
        with open(logfile, "a") as f:
            f.write(f"{datetime.now().isoformat()}, {label}={avg_value}, samples={sample_count}\n")
        print(f"[DEBUG] Logged 5-min avg {label}: {avg_value} over {sample_count} samples")
    except Exception as e:
        log_mgr.log_error(f"Failed to write avg {label} log: {e}")

# --- Main Loop with Scheduler ---
def main():
    print(f"[DEBUG] Starting SensorMonitor main loop... (version {SOFTWARE_VERSION})")
    log_mgr = LogManager(ERROR_LOG_FILE)
    # Sensor initialization
    flow_sensor = None
    color_sensor = None
    dht22_sensor = None
    wind_sensor = None
    pressure_sensor = None
    ads = None
    wind_direction_sensor = None
    if ENABLE_FLOW_SENSOR:
        try:
            flow_sensor = FlowSensor(FLOW_SENSOR_PIN, FLOW_PULSES_PER_LITRE)
            print("[DEBUG] Flow sensor initialized.")
        except Exception as e:
            log_mgr.log_error(f"Flow sensor init error: {e}")
            flow_sensor = None
    if ENABLE_COLOR_SENSOR:
        try:
            color_sensor = ColorSensor(LED_PIN, NUM_COLOR_READINGS, COLOR_READ_SPACING)
            print("[DEBUG] Color sensor initialized.")
        except Exception as e:
            log_mgr.log_error(f"Color sensor init error: {e}")
            color_sensor = None
    if ENABLE_DHT22:
        try:
            dht22_sensor = DHT22Sensor(DHT_PIN)
            print("[DEBUG] DHT22 sensor initialized.")
        except Exception as e:
            log_mgr.log_error(f"DHT22 init error: {e}")
            dht22_sensor = None
    if ENABLE_WIND_SENSOR:
        try:
            wind_sensor = WindSensor(WIND_SENSOR_PIN)
            print("[DEBUG] Wind sensor initialized.")
        except Exception as e:
            log_mgr.log_error(f"Wind sensor init error: {e}")
            wind_sensor = None
    if ENABLE_PRESSURE_SENSOR or True:  # Ensure ADS is always initialized if wind direction is needed
        try:
            import busio
            import board
            ads = ADS.ADS1115(busio.I2C(board.SCL, board.SDA))
            print("[DEBUG] ADS1115 initialized.")
            if ENABLE_PRESSURE_SENSOR:
                pressure_sensor = PressureSensor(ads)
                print("[DEBUG] Pressure sensor initialized.")
            # --- Wind direction sensor ---
            wind_direction_sensor = WindDirectionSensor(ads)
            print("[DEBUG] Wind direction sensor initialized.")
        except Exception as e:
            log_mgr.log_error(f"ADS1115 init error: {e}")
            pressure_sensor = None
            wind_direction_sensor = None
    # MQTT setup (now using MqttPublisher)
    mqtt_broker = "100.116.147.6"
    mqtt_port = 1883
    mqtt_publisher = MqttPublisher(mqtt_broker, mqtt_port, log_file=ERROR_LOG_FILE)
    # Scheduler state
    last_run = defaultdict(lambda: 0)
    readings_accum = defaultdict(list)
    last_flow_log_time = 0  # For 5s logging when flow > 0
    try:
        while True:
            now = time.time()
            # --- Step 1: Collect all sensor readings ---
            if flow_sensor is not None:
                try:
                    flow = flow_sensor.read()
                    flow["flow_rate_lpm"] = calculate_flow_rate(flow["flow_litres"], 1.0)
                except Exception as e:
                    log_mgr.log_error(f"Flow reading out of range: {e}")
                    flow = {"timestamp": datetime.now().isoformat(), "flow_pulses": None, "flow_litres": None, "flow_rate_lpm": None}
            else:
                flow = {"timestamp": datetime.now().isoformat(), "flow_pulses": None, "flow_litres": None, "flow_rate_lpm": None}
            if pressure_sensor is not None:
                try:
                    pressure = pressure_sensor.read()
                except Exception as e:
                    log_mgr.log_error(f"Pressure sensor read error: {e}")
                    pressure = {"timestamp": datetime.now().isoformat(), "pressure_psi": None, "pressure_kpa": None}
            else:
                pressure = {"timestamp": datetime.now().isoformat(), "pressure_psi": None, "pressure_kpa": None}
            if wind_sensor is not None:
                wind = wind_sensor.read()
            else:
                wind = {"timestamp": datetime.now().isoformat(), "wind_speed": None}
            # --- Wind direction reading ---
            if wind_direction_sensor is not None:
                wind_dir = wind_direction_sensor.read()
                wind["wind_direction_deg"] = wind_dir["wind_direction_deg"]
                wind["wind_direction_compass"] = wind_dir["wind_direction_compass"]
            else:
                wind["wind_direction_deg"] = None
                wind["wind_direction_compass"] = None
            if dht22_sensor is not None:
                try:
                    dht = dht22_sensor.read()
                except Exception as e:
                    log_mgr.log_error(f"DHT22: No valid reading this second after 3 attempts. {e}")
                    dht = {"timestamp": datetime.now().isoformat(), "temperature": None, "humidity": None}
            else:
                dht = {"timestamp": datetime.now().isoformat(), "temperature": None, "humidity": None}
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
            mqtt_publisher.publish("sensors/sets", sets_data)
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
            mqtt_publisher.publish("sensors/environment", environment_data)
            # --- Step 3: Accumulate for 5-min and 5-sec averages ---
            if flow["flow_litres"] is not None:
                readings_accum["flow"].append(flow["flow_litres"])
                # New: maintain a separate 5-sec accumulator for granular logging
                if "flow_5s" not in readings_accum:
                    readings_accum["flow_5s"] = []
                readings_accum["flow_5s"].append(flow["flow_litres"])
            if pressure["pressure_psi"] is not None:
                readings_accum["pressure"].append(pressure["pressure_psi"])
            if wind["wind_speed"] is not None:
                readings_accum["wind"].append(wind["wind_speed"])
            if dht["temperature"] is not None:
                readings_accum["temperature"].append(dht["temperature"])
            if wind["wind_direction_deg"] is not None:
                if "wind_direction" not in readings_accum:
                    readings_accum["wind_direction"] = []
                readings_accum["wind_direction"].append({
                    "wind_direction_deg": wind["wind_direction_deg"],
                    "wind_direction_compass": wind["wind_direction_compass"]
                })
            # --- Step 4: Conditional avg_flow logging (dual-accumulator) ---
            avg_flow_5min = None
            avg_flow_5s = None
            if readings_accum["flow"]:
                avg_flow_5min = sum(readings_accum["flow"]) / len(readings_accum["flow"])
            if "flow_5s" in readings_accum and readings_accum["flow_5s"]:
                avg_flow_5s = sum(readings_accum["flow_5s"]) / len(readings_accum["flow_5s"])
            # Log every 5 minutes (regardless of flow value)
            if now - last_run["flow_avg"] >= AVG_FLOW_INTERVAL:
                if avg_flow_5min is not None:
                    log_5min_average(AVG_FLOW_LOG_FILE, f"{avg_flow_5min:.4f}", "avg_flow", len(readings_accum["flow"]))
                    readings_accum["flow"] = []
                last_run["flow_avg"] = now
                last_flow_log_time = now  # Reset 5s timer after 5min log
                # Also clear the 5s accumulator to avoid overlap
                readings_accum["flow_5s"] = []
            # Log every 5 seconds if avg_flow_5s > 0 (but do not reset 5min timer)
            elif avg_flow_5s is not None and avg_flow_5s > 0 and now - last_flow_log_time >= 5:
                log_5min_average(AVG_FLOW_LOG_FILE, f"{avg_flow_5s:.4f}", "avg_flow", len(readings_accum["flow_5s"]))
                readings_accum["flow_5s"] = []
                last_flow_log_time = now
            # --- Step 5: 5-min average logging (scheduler pattern) ---
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
            # --- RESTORED: Wind direction 5-min average logging ---
            if now - last_run["wind_direction_avg"] >= AVG_WIND_INTERVAL:
                wind_dir_degs = [x["wind_direction_deg"] for x in readings_accum.get("wind_direction", []) if x["wind_direction_deg"] is not None]
                wind_dir_compass = [x["wind_direction_compass"] for x in readings_accum.get("wind_direction", []) if x["wind_direction_compass"] is not None]
                if wind_dir_degs:
                    avg_deg = sum(wind_dir_degs) / len(wind_dir_degs)
                    from collections import Counter
                    compass = Counter(wind_dir_compass).most_common(1)[0][0] if wind_dir_compass else None
                    log_5min_average(AVG_WIND_DIRECTION_LOG_FILE, f"{avg_deg:.2f},{compass}", "avg_wind_direction", len(wind_dir_degs))
                readings_accum["wind_direction"] = []
                last_run["wind_direction_avg"] = now
            # --- Step 6: Plant/color reporting every GROUP_INTERVAL minutes ---
            if ENABLE_COLOR_SENSOR and color_sensor is not None and now - last_run["color"] >= GROUP_INTERVAL * 60:
                color_readings = color_sensor.read()
                if color_readings:
                    avg_b = sum(d['b'] for d in color_readings) / len(color_readings)
                    avg_lux = sum(d['lux'] for d in color_readings) / len(color_readings)
                    ts = color_readings[0]['timestamp']
                    try:
                        with open("calibration.json", "r") as f:
                            calib = json.load(f)
                        b_dry = float(calib["white_stick"]["b"])
                        b_wet = float(calib["blue_stick"]["b"])
                        if b_wet == b_dry:
                            moisture_pct = 0.0
                        else:
                            moisture_pct = (avg_b - b_dry) / (b_wet - b_dry) * 100.0
                            moisture_pct = max(0.0, min(100.0, moisture_pct))
                    except Exception as e:
                        log_mgr.log_error(f"Failed to load or use calibration.json: {e}")
                        moisture_pct = None
                else:
                    avg_lux, ts, moisture_pct = None, datetime.now().isoformat(), None
                plant_data = {
                    "sensor_name": SENSOR_NAME,
                    "timestamp": ts,
                    "moisture": moisture_pct,
                    "lux": avg_lux,
                    "soil_temperature": None,
                    "version": SOFTWARE_VERSION
                }
                mqtt_publisher.publish("sensors/plant", plant_data)
                with open("color_log.txt", "a") as f:
                    f.write(json.dumps(plant_data) + "\n")
                log_mgr.trim_log_file("color_log.txt", 1000)
                last_run["color"] = now
            # --- Step 7: Trim stdout_log.txt ---
            # trim_stdout_log(1000)  # Disabled: handled by logrotate or external tool
    except KeyboardInterrupt:
        print("[INFO] Exiting...")
    finally:
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.cleanup()
        # No explicit disconnect needed; MqttPublisher handles cleanup
        print("[INFO] GPIO cleaned up and MQTT publisher stopped.")

if __name__ == "__main__":
    main()
