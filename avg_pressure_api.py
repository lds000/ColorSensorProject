from flask import Flask, request, jsonify
import os

AVG_PRESSURE_LOG_FILE = "avg_pressure_log.txt"

app = Flask(__name__)

@app.route("/pressure-avg-latest", methods=["GET"])
def get_recent_avg_pressures():
    """
    Returns the n most recent average pressure readings from avg_pressure_log.txt.
    Query param: n (default 5)
    """
    n = request.args.get("n", default=5, type=int)
    if n < 1 or n > 100:
        return jsonify({"error": "n must be between 1 and 100"}), 400
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
