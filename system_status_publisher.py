"""
System Status MQTT Publisher for Raspberry Pi Zero W
Publishes system health info (CPU temp, RAM, disk, uptime, etc.) to MQTT topic 'status/system' every 10 seconds.
"""

import time
import json
import paho.mqtt.client as mqtt
import os
import platform
import subprocess


# DS18B20 device IDs (update these if you swap sensors)
DS18B20_ENV_ID = "28-000000523788"  # Environment sensor
DS18B20_SOIL_ID = "28-00000053ca7e"  # Soil sensor


def read_specific_ds18b20_temp(device_id):
    """
    Reads temperature from a specific DS18B20 sensor by device ID.
    Returns temperature in Celsius, or None on error.
    Logs a warning if the sensor is missing or cannot be read.
    """
    device_path = f"/sys/bus/w1/devices/{device_id}/w1_slave"
    if not os.path.exists(device_path):
        print(f"WARNING: DS18B20 sensor {device_id} not found (unplugged or not detected)")
        return None
    try:
        with open(device_path, "r") as f:
            lines = f.readlines()
        if lines[0].strip()[-3:] != "YES":
            print(f"WARNING: DS18B20 sensor {device_id} present but not returning valid data")
            return None
        temp_str = lines[1].split("t=")[-1]
        return float(temp_str) / 1000.0
    except Exception as e:
        print(f"ERROR reading DS18B20 sensor {device_id}: {e}")
        return None

MQTT_BROKER = "100.116.147.6"  # Change to your broker IP if needed
MQTT_PORT = 1883
MQTT_TOPIC = "status/system"
PUBLISH_INTERVAL = 10  # seconds

client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)

def get_cpu_temp():
    try:
        # Works on Pi Zero W and most Pi models
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_str = f.read().strip()
        return float(temp_str) / 1000.0
    except Exception:
        return None

def get_mem_info():
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
        mem_total = int([l for l in lines if l.startswith("MemTotal")][0].split()[1])
        mem_free = int([l for l in lines if l.startswith("MemFree")][0].split()[1])
        return {"total_kb": mem_total, "free_kb": mem_free}
    except Exception:
        return None

def get_disk_info():
    try:
        st = os.statvfs("/")
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        return {"total_bytes": total, "free_bytes": free}
    except Exception:
        return None

def get_uptime():
    try:
        with open("/proc/uptime", "r") as f:
            uptime = float(f.read().split()[0])
        return uptime
    except Exception:
        return None

def get_loadavg():
    try:
        with open("/proc/loadavg", "r") as f:
            parts = f.read().split()
        return {"1min": float(parts[0]), "5min": float(parts[1]), "15min": float(parts[2])}
    except Exception:
        return None

def get_hostname():
    return platform.node()

def get_ip():
    try:
        result = subprocess.run(["hostname", "-I"], stdout=subprocess.PIPE)
        return result.stdout.decode().strip().split()[0]
    except Exception:
        return None

def get_temp_warnings(cpu_temp):
    if cpu_temp is None:
        return None
    if cpu_temp > 70:
        return "HIGH_TEMP"
    elif cpu_temp > 60:
        return "ELEVATED_TEMP"
    return None



def build_status_payload():
    cpu_temp = get_cpu_temp()
    mem = get_mem_info()
    disk = get_disk_info()
    uptime = get_uptime()
    load = get_loadavg()
    hostname = get_hostname()
    ip = get_ip()
    temp_warn = get_temp_warnings(cpu_temp)
    # Read DS18B20 sensors only
    env_temp = read_specific_ds18b20_temp(DS18B20_ENV_ID)
    soil_temp = read_specific_ds18b20_temp(DS18B20_SOIL_ID)
    if env_temp is None:
        print("System status: Environment sensor missing or unplugged.")
    if soil_temp is None:
        print("System status: Soil sensor missing or unplugged.")
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "hostname": hostname,
        "ip": ip,
        "cpu_temp_c": cpu_temp,
        "cpu_temp_warning": temp_warn,
        "env_temp_c": env_temp,
        "soil_temp_c": soil_temp,
        "mem": mem,
        "disk": disk,
        "uptime_sec": uptime,
        "loadavg": load,
        "system_health": "OK" if not temp_warn else temp_warn
    }

def main():
    while True:
        payload = build_status_payload()
        client.publish(MQTT_TOPIC, json.dumps(payload), qos=0, retain=False)
        time.sleep(PUBLISH_INTERVAL)

if __name__ == "__main__":
    main()
