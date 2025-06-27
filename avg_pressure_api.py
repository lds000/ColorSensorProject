from flask import Flask, request, jsonify
import os

AVG_PRESSURE_LOG_FILE = "avg_pressure_log.txt"
AVG_WIND_LOG_FILE = "avg_wind_log.txt"
AVG_FLOW_LOG_FILE = "avg_flow_log.txt"
AVG_TEMPERATURE_LOG_FILE = "avg_temperature_log.txt"

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

@app.route("/temperature-avg-latest", methods=["GET"])
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
