import RPi.GPIO as GPIO
import time
from board import D22, D27
from adafruit_bitbangio import I2C
import adafruit_tcs34725
from logging_utils import log_stdout, log_error
import threading

LED_PIN = 17
FLOW_SENSOR_PIN = 22
FLOW_PULSES_PER_LITRE = 450

flow_pulse_count = 0
flow_lock = None

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.output(LED_PIN, GPIO.LOW)

def cleanup_gpio():
    GPIO.output(LED_PIN, GPIO.LOW)
    GPIO.cleanup()

def init_sensor():
    log_stdout("Initializing I2C sensor...")
    i2c = I2C(scl=D22, sda=D27)
    while not i2c.try_lock():
        time.sleep(0.1)
    devices = i2c.scan()
    i2c.unlock()
    log_stdout(f"I2C devices found: {devices}")

    addr = 0x29 if 0x29 in devices else (0x2A if 0x2A in devices else None)
    if addr is None:
        log_error("Sensor not found on I2C")
        GPIO.output(LED_PIN, GPIO.LOW)
        raise RuntimeError("Sensor not found on I2C")

    sensor = adafruit_tcs34725.TCS34725(i2c, address=addr)
    sensor.integration_time = 100
    sensor.gain = 4
    log_stdout(f"Sensor initialized at address {hex(addr)}")
    return sensor

def read_color(sensor):
    log_stdout("Reading color sensor...")
    GPIO.output(LED_PIN, GPIO.HIGH)
    time.sleep(0.3)
    r, g, b = sensor.color_rgb_bytes
    lux = sensor.lux
    GPIO.output(LED_PIN, GPIO.LOW)
    log_stdout(f"Sensor values: R={r}, G={g}, B={b}, Lux={lux}")
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "r": int(r),
        "g": int(g),
        "b": int(b),
        "lux": float(lux)
    }

def setup_flow_gpio():
    global flow_lock
    # Always set up as input with pull-up before adding event detect
    GPIO.setup(FLOW_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    flow_lock = threading.Lock()
    try:
        GPIO.add_event_detect(FLOW_SENSOR_PIN, GPIO.FALLING, callback=flow_pulse_callback)
        log_stdout(f"Flow meter GPIO {FLOW_SENSOR_PIN} set up with pull-up and event detect.")
    except RuntimeError as e:
        log_error(f"Failed to add edge detection on pin {FLOW_SENSOR_PIN}: {e}. Attempting to remove and re-add.")
        try:
            GPIO.remove_event_detect(FLOW_SENSOR_PIN)
            GPIO.add_event_detect(FLOW_SENSOR_PIN, GPIO.FALLING, callback=flow_pulse_callback)
            log_stdout(f"Flow meter GPIO {FLOW_SENSOR_PIN} event detect re-added after removal.")
        except Exception as e2:
            log_error(f"Failed to re-add edge detection on pin {FLOW_SENSOR_PIN}: {e2}")
            raise

def cleanup_flow_gpio():
    GPIO.remove_event_detect(FLOW_SENSOR_PIN)
    log_stdout(f"Flow meter GPIO {FLOW_SENSOR_PIN} event detect removed.")

def flow_pulse_callback(channel):
    global flow_pulse_count
    if flow_lock:
        with flow_lock:
            flow_pulse_count += 1
    else:
        flow_pulse_count += 1

def get_and_reset_flow_litres():
    global flow_pulse_count
    if flow_lock:
        with flow_lock:
            pulses = flow_pulse_count
            flow_pulse_count = 0
    else:
        pulses = flow_pulse_count
        flow_pulse_count = 0
    litres = pulses / FLOW_PULSES_PER_LITRE
    log_stdout(f"Flow pulses: {pulses}, litres: {litres}")
    return litres

def read_all_sensors(sensor):
    """
    Read both color sensor and flow meter.
    Returns a dict with color and flow data.
    """
    color_data = read_color(sensor)
    flow_litres = get_and_reset_flow_litres()
    # Combine results
    result = color_data.copy()
    result["flow_litres"] = flow_litres
    return result
