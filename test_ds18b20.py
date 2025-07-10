"""
test_ds18b20.py: Minimal test script for DS18B20 soil temperature sensor on Raspberry Pi.
- Reads temperature from the first detected 1-Wire sensor.
- Handles errors and logs to error_log.txt.
- Prints temperature to console.

Wiring:
- Data: Connect to GPIO4 (physical pin 7)
- 4.7kΩ pull-up resistor between data and 3.3V
- Enable 1-Wire in raspi-config
"""
import os
import glob
import time

def log_error(msg):
    try:
        with open("error_log.txt", "a") as f:
            f.write(f"[DS18B20][{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

def read_ds18b20_temp():
    base_dir = "/sys/bus/w1/devices/"
    try:
        device_folders = glob.glob(base_dir + "28-*")
        if not device_folders:
            raise RuntimeError("No DS18B20 sensor found (no 28-* folder in /sys/bus/w1/devices)")
        device_file = os.path.join(device_folders[0], "w1_slave")
        with open(device_file, "r") as f:
            lines = f.readlines()
        if lines[0].strip()[-3:] != 'YES':
            raise RuntimeError("CRC check failed: " + lines[0].strip())
        equals_pos = lines[1].find('t=')
        if equals_pos == -1:
            raise RuntimeError("Temperature data not found in sensor output")
        temp_c = float(lines[1][equals_pos+2:]) / 1000.0
        return temp_c
    except Exception as e:
        log_error(f"DS18B20 read error: {e}")
        return None

def main():
    temp = read_ds18b20_temp()
    if temp is not None:
        print(f"Soil temperature: {temp:.2f} °C")
    else:
        print("Failed to read soil temperature. See error_log.txt for details.")

if __name__ == "__main__":
    main()
