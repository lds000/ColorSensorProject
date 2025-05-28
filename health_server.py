from flask import Flask, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    # Try to get last reading from color_log.txt
    last_reading = None
    try:
        with open('color_log.txt', 'r') as f:
            lines = f.readlines()
            if lines:
                last_reading = lines[-1].strip()
    except Exception as e:
        last_reading = f"Could not read log: {e}"

    # Try to get WiFi info
    wifi_info = None
    try:
        import subprocess
        result = subprocess.run(['iwgetid'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.stdout:
            ssid = result.stdout.strip()
        else:
            ssid = "Not connected to WiFi"
        status = subprocess.run(['iwconfig'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        wifi_info = f"SSID: {ssid}\nWiFi Info:\n{status.stdout}"
    except Exception as e:
        wifi_info = f"Could not get WiFi info: {e}"

    # Uptime
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime = str(datetime.timedelta(seconds=int(uptime_seconds)))
    except Exception:
        uptime = None

    return jsonify({
        'status': 'ok',
        'last_reading': last_reading,
        'wifi_info': wifi_info,
        'uptime': uptime,
        'time': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
