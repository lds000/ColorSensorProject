
"""
Exhaustive DHT22 Temperature/Humidity Debug Script for Raspberry Pi Zero W
Prints environment temperature and humidity to the console, with detailed debug info and error logging.
Wiring: DHT22 data pin to GPIO 4 (physical pin 7), 10kΩ pull-up to VCC.
"""
import Adafruit_DHT
import time
import os
import sys
import traceback

DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4  # BCM numbering
ERROR_LOG = "error_log.txt"

def log_error(msg):
    with open(ERROR_LOG, "a") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

def print_debug_info():
    print("\n--- DHT22 Debug Info ---")
    print(f"Script PID: {os.getpid()}")
    print(f"Python version: {sys.version}")
    print(f"Current user: {os.getenv('USER') or os.getenv('USERNAME')}")
    print(f"Working directory: {os.getcwd()}")
    print(f"DHT_SENSOR: {DHT_SENSOR}, DHT_PIN: {DHT_PIN}")
    print("Listing /dev/gpiomem and /dev/mem:")
    for dev in ["/dev/gpiomem", "/dev/mem"]:
        print(f"  {dev}: {'Exists' if os.path.exists(dev) else 'Missing'}")
    print("Listing GPIO permissions:")
    try:
        import grp
        print(f"Groups: {os.getgroups()}")
    except Exception:
        print("Could not get group info.")
    print("Listing process info:")
    os.system("ps aux | grep python3")
    print("Listing open files for this process:")
    os.system(f"lsof -p {os.getpid()}")
    print("------------------------\n")

def main():
    print("Starting DHT22 debug script...")
    print_debug_info()
    while True:
        try:
            humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
            print(f"Raw sensor values: humidity={humidity}, temperature={temperature}")
            if humidity is not None and temperature is not None:
                print(f"Temperature: {temperature:.1f}°C  Humidity: {humidity:.1f}%")
            else:
                print("Failed to retrieve data from DHT22 sensor")
                log_error(f"DHT22 read failed: humidity={humidity}, temperature={temperature}")
        except Exception as e:
            print("Exception occurred during DHT22 read!")
            traceback.print_exc()
            log_error(f"Exception: {e}\n{traceback.format_exc()}")
        time.sleep(2)

if __name__ == "__main__":
    main()
