from flask import Flask, jsonify, request
import os
import json
from datetime import datetime
import subprocess
import threading

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

@app.route('/ota-update', methods=['POST'])
def ota_update():
    # Optional: require a secret token for security
    token = request.headers.get('X-OTA-Token')
    required_token = os.environ.get('OTA_TOKEN')
    if required_token and token != required_token:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    def do_update():
        subprocess.call(['git', 'pull'])
        # Optionally restart main script or reboot here
        # subprocess.call(['systemctl', 'restart', 'color_logger'])
        # subprocess.call(['reboot'])
    threading.Thread(target=do_update).start()
    return jsonify({'status': 'ok', 'message': 'OTA update triggered'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
