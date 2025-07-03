# Flask API for Average Pressure Log
# (Restored from archive by Copilot)

from flask import Flask, jsonify, request
import os
import json
from datetime import datetime

app = Flask(__name__)

AVG_PRESSURE_LOG_FILE = "avg_pressure_log.txt"

@app.route("/avg-pressure-latest", methods=["GET"])
def get_latest_avg_pressure():
    """Return the latest average pressure log entry as JSON."""
    try:
        if not os.path.exists(AVG_PRESSURE_LOG_FILE):
            return jsonify({"error": "No log file found."}), 404
        with open(AVG_PRESSURE_LOG_FILE, "r") as f:
            lines = f.readlines()
        if not lines:
            return jsonify({"error": "Log file is empty."}), 404
        last = lines[-1].strip()
        # Example log line: 2025-07-03T10:00:00, avg_psi=42.1, samples=5
        parts = last.split(", ")
        if len(parts) < 3:
            return jsonify({"error": "Malformed log entry."}), 500
        ts = parts[0]
        avg_psi = parts[1].split("=")[1]
        samples = parts[2].split("=")[1]
        return jsonify({
            "timestamp": ts,
            "avg_psi": float(avg_psi),
            "samples": int(samples)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/avg-pressure-log", methods=["GET"])
def get_all_avg_pressure():
    """Return all average pressure log entries as JSON list."""
    try:
        if not os.path.exists(AVG_PRESSURE_LOG_FILE):
            return jsonify([])
        with open(AVG_PRESSURE_LOG_FILE, "r") as f:
            lines = f.readlines()
        entries = []
        for line in lines:
            parts = line.strip().split(", ")
            if len(parts) < 3:
                continue
            ts = parts[0]
            avg_psi = parts[1].split("=")[1]
            samples = parts[2].split("=")[1]
            entries.append({
                "timestamp": ts,
                "avg_psi": float(avg_psi),
                "samples": int(samples)
            })
        return jsonify(entries)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
