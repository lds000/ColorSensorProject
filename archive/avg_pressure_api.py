from flask import Flask, request, jsonify
import os
import json

AVG_PRESSURE_LOG_FILE = "avg_pressure_log.txt"
AVG_WIND_LOG_FILE = "avg_wind_log.txt"
AVG_FLOW_LOG_FILE = "avg_flow_log.txt"
AVG_TEMPERATURE_LOG_FILE = "avg_temperature_log.txt"
COLOR_LOG_FILE = "color_log.txt"

AVG_SOIL_TEMPERATURE_LOG_FILE = "avg_soil_temperature_log.txt"

@app.route("/soil-temperature-avg-latest", methods=["GET"])
def get_recent_soil_temp_avg():
    """
    Returns the n most recent 5-min average soil temperature readings from avg_soil_temperature_log.txt.
    Query param: n (default 5)
    """
    n = request.args.get("n", default=5, type=int)
    if n < 1 or n > 500:
        return jsonify({"error": "n must be between 1 and 500"}), 400
    if not os.path.exists(AVG_SOIL_TEMPERATURE_LOG_FILE):
        return jsonify([])
    try:
        with open(AVG_SOIL_TEMPERATURE_LOG_FILE, "r") as f:
            lines = f.readlines()
        lines = [line.strip() for line in lines if line.strip()][-n:]
        results = []
        for line in lines:
            # Example line: 2025-07-11T12:00:00.000000, avg_soil_temp=23.45, samples=12
            try:
                parts = line.split(",")
                timestamp = parts[0].strip()
                avg_soil_temp = float([p for p in parts if "avg_soil_temp=" in p][0].split("=")[1])
                samples = int([p for p in parts if "samples=" in p][0].split("=")[1])
                results.append({
                    "timestamp": timestamp,
                    "avg_soil_temp": avg_soil_temp,
                    "samples": samples
                })
            except Exception:
                continue  # skip malformed lines
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

app = Flask(__name__)

@app.route("/pressure-avg-latest", methods=["GET"])
def get_recent_avg_pressures():
    """
    Returns the n most recent average pressure readings from avg_pressure_log.txt.
    Query param: n (default 5)
    """
    n = request.args.get("n", default=5, type=int)
    if n < 1 or n > 500:
        return jsonify({"error": "n must be between 1 and 500"}), 400
    if not os.path.exists(AVG_PRESSURE_LOG_FILE):
        return jsonify([])
    try:
        with open(AVG_PRESSURE_LOG_FILE, "r") as f:
            lines = f.readlines()
        # Get last n non-empty lines
        lines = [line.strip() for line in lines if line.strip()][-n:]
        results = []
        for line in lines:
            # Example line: 2025-06-19T12:00:00.000000, avg_psi=45.23, samples=300
            try:
                parts = line.split(",")
                timestamp = parts[0].strip()
                avg_psi = float(parts[1].split("=")[1])
                samples = int(parts[2].split("=")[1])
                results.append({
                    "timestamp": timestamp,
                    "avg_psi": avg_psi,
                    "samples": samples
                })
            except Exception as e:
                continue  # skip malformed lines
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/wind-avg-latest", methods=["GET"])
def get_recent_avg_wind():
    """
    Returns the n most recent average wind speed readings from avg_wind_log.txt.
    Query param: n (default 5)
    """
    n = request.args.get("n", default=5, type=int)
    if n < 1 or n > 500:
        return jsonify({"error": "n must be between 1 and 500"}), 400
    if not os.path.exists(AVG_WIND_LOG_FILE):
        return jsonify([])
    try:
        with open(AVG_WIND_LOG_FILE, "r") as f:
            lines = f.readlines()
        lines = [line.strip() for line in lines if line.strip()][-n:]
        results = []
        for line in lines:
            # Example line: 2025-06-19T12:00:00.000000, avg_wind=2.34, samples=300
            try:
                parts = line.split(",")
                timestamp = parts[0].strip()
                avg_wind = float(parts[1].split("=")[1])
                samples = int(parts[2].split("=")[1])
                results.append({
                    "timestamp": timestamp,
                    "avg_wind": avg_wind,
                    "samples": samples
                })
            except Exception as e:
                continue  # skip malformed lines
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/flow-avg-latest", methods=["GET"])
def get_recent_avg_flow():
    """
    Returns the n most recent average flow readings from avg_flow_log.txt.
    Query param: n (default 5)
    """
    n = request.args.get("n", default=5, type=int)
    if n < 1 or n > 500:
        return jsonify({"error": "n must be between 1 and 500"}), 400
    if not os.path.exists(AVG_FLOW_LOG_FILE):
        return jsonify([])
    try:
        with open(AVG_FLOW_LOG_FILE, "r") as f:
            lines = f.readlines()
        lines = [line.strip() for line in lines if line.strip()][-n:]
        results = []
        for line in lines:
            # Example line: 2025-06-27T12:00:00.000000, avg_flow=1.23, samples=300
            try:
                parts = line.split(",")
                timestamp = parts[0].strip()
                avg_flow = float(parts[1].split("=")[1])
                samples = int(parts[2].split("=")[1])
                results.append({
                    "timestamp": timestamp,
                    "avg_flow": avg_flow,
                    "samples": samples
                })
            except Exception as e:
                continue  # skip malformed lines
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/temperature-avg-latest2", methods=["GET"])
def get_recent_avg_temperature():
    """
    Returns the n most recent average temperature readings from avg_temperature_log.txt.
    Query param: n (default 5)
    """
    n = request.args.get("n", default=5, type=int)
    if n < 1 or n > 500:
        return jsonify({"error": "n must be between 1 and 500"}), 400
    if not os.path.exists(AVG_TEMPERATURE_LOG_FILE):
        return jsonify([])
    try:
        with open(AVG_TEMPERATURE_LOG_FILE, "r") as f:
            lines = f.readlines()
        lines = [line.strip() for line in lines if line.strip()][-n:]
        results = []
        for line in lines:
            # Example line: 2025-06-27T12:00:00.000000, avg_temp=22.5, samples=300
            try:
                parts = line.split(",")
                timestamp = parts[0].strip()
                avg_temp = float(parts[1].split("=")[1])
                samples = int(parts[2].split("=")[1])
                results.append({
                    "timestamp": timestamp,
                    "avg_temp": avg_temp,
                    "samples": samples
                })
            except Exception as e:
                continue  # skip malformed lines
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/moisture-avg-latest", methods=["GET"])
def get_recent_color_moisture():
    """
    Returns the n most recent color/moisture readings from color_log.txt.
    Query param: n (default 5)
    Output: List of dicts with timestamp (ISO8601) and value (moisture as double)
    Handles both legacy plain text and new JSON lines.
    """
    n = request.args.get("n", default=5, type=int)
    if n < 1 or n > 500:
        return jsonify({"error": "n must be between 1 and 500"}), 400
    if not os.path.exists(COLOR_LOG_FILE):
        return jsonify([])
    try:
        with open(COLOR_LOG_FILE, "r") as f:
            lines = f.readlines()
        # Only keep lines that are not AVG or [INFO]
        data_lines = [line.strip() for line in lines if line.strip() and not line.startswith("AVG") and not line.startswith("[INFO]")]
        # Parse from the end, newest first
        results = []
        for line in reversed(data_lines):
            try:
                if line.startswith("{"):
                    # JSON line
                    obj = json.loads(line)
                    ts = obj.get("timestamp")
                    val = obj.get("moisture")
                    if ts is not None and val is not None:
                        results.append({"timestamp": ts, "value": float(val)})
                else:
                    # Legacy plain text line
                    parts = line.split()
                    ts = parts[0]
                    b = float(parts[3].split(":")[1])
                    results.append({"timestamp": ts, "value": b})
            except Exception:
                continue
            if len(results) >= n:
                break
        results.reverse()  # Return in chronological order
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":

