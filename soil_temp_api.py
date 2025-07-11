"""
Flask API for latest 5-min average soil temperature
Reads from avg_soil_temperature_log.txt and returns JSON
"""
from flask import Flask, jsonify
import os

app = Flask(__name__)
AVG_SOIL_TEMPERATURE_LOG_FILE = "avg_soil_temperature_log.txt"

@app.route('/soil-temperature-avg-latest', methods=['GET'])
def soil_temperature_avg_latest():
    """
    Returns the latest 5-min average soil temperature from avg_soil_temperature_log.txt.
    """
    if not os.path.exists(AVG_SOIL_TEMPERATURE_LOG_FILE):
        return jsonify({"error": "Log file not found"}), 404
    try:
        with open(AVG_SOIL_TEMPERATURE_LOG_FILE, "r") as f:
            lines = f.readlines()
        if not lines:
            return jsonify({"error": "No data available"}), 404
        last_line = lines[-1]
        # Example: "2025-07-11T12:00:00.000000, avg_soil_temp=23.45, samples=300"
        parts = last_line.strip().split(",")
        avg_temp = None
        timestamp = None
        for part in parts:
            if "avg_soil_temp=" in part:
                try:
                    avg_temp = float(part.split("=")[1])
                except Exception:
                    avg_temp = None
            elif "T" in part:
                timestamp = part.strip()
        if avg_temp is None:
            return jsonify({"error": "Malformed log entry"}), 500
        return jsonify({
            "timestamp": timestamp,
            "avg_soil_temperature": avg_temp
        })
    except Exception as e:
        # Log error to error_log.txt
        with open("error_log.txt", "a") as errf:
            errf.write(f"Flask soil temp endpoint error: {str(e)}\n")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
