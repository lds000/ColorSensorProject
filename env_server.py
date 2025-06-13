# env_server.py
# Flask server for collecting, storing, and serving sensor data from multiple sources (plant, sets, environment)
# Provides endpoints for latest and historical data for each sensor group

from flask import Flask, jsonify, request
from datetime import datetime
import threading

# Create the Flask application instance
app = Flask(__name__)

# -----------------------------
# In-memory storage for sensor data
# Each group (plant, sets, environment) has a 'latest' variable and a 'history' list
# HISTORY_LIMITS prevent unbounded memory growth
# -----------------------------

# Legacy endpoints (can be removed if not needed)
env_latest = None  # Latest data for /env-latest
env_history = []   # History for /env-history
HISTORY_LIMIT = 1000  # Max number of history entries for legacy env endpoints

env_env_latest = None  # Latest data for /env-env-latest
env_env_history = []   # History for /env-env-history
ENV_HISTORY_LIMIT = 1000

# Plant data (e.g., moisture, soil temperature)
plant_latest = None  # Latest plant data
plant_history = []   # History of plant data
PLANT_HISTORY_LIMIT = 1000

# Sets data (e.g., flow, pressure)
sets_latest = None  # Latest sets data
sets_history = []   # History of sets data
SETS_HISTORY_LIMIT = 1000

# Environment data (e.g., temperature, humidity, wind, barometric pressure)
environment_latest = None  # Latest environment data
environment_history = []   # History of environment data
ENVIRONMENT_HISTORY_LIMIT = 1000

# -----------------------------
# Flask route definitions
# Each endpoint supports GET (retrieve data) and/or POST (submit new data)
# -----------------------------

@app.route('/env-latest', methods=['GET', 'POST'])
def env_latest_endpoint():
    """
    Legacy endpoint for latest environment data (generic).
    POST: Store new data as latest and append to history.
    GET:  Return latest data if available.
    """
    global env_latest
    if request.method == 'POST':
        data = request.get_json(force=True)
        env_latest = data
        env_history.append(data)
        if len(env_history) > HISTORY_LIMIT:
            env_history.pop(0)  # Remove oldest entry if over limit
        return jsonify({'status': 'ok'}), 200
    else:
        if env_latest is not None:
            return jsonify(env_latest)
        else:
            return jsonify({'error': 'No data yet'}), 404

@app.route('/env-history', methods=['GET'])
def env_history_endpoint():
    """
    Legacy endpoint for full environment data history (generic).
    GET: Return all stored history entries.
    """
    return jsonify(env_history)

@app.route('/env-env-latest', methods=['GET', 'POST'])
def env_env_latest_endpoint():
    """
    Legacy endpoint for latest environment data (redundant).
    POST: Store new data as latest and append to history.
    GET:  Return latest data if available.
    """
    global env_env_latest
    if request.method == 'POST':
        data = request.get_json(force=True)
        env_env_latest = data
        env_env_history.append(data)
        if len(env_env_history) > ENV_HISTORY_LIMIT:
            env_env_history.pop(0)
        return jsonify({'status': 'ok'}), 200
    else:
        if env_env_latest is not None:
            return jsonify(env_env_latest)
        else:
            return jsonify({'error': 'No data yet'}), 404

@app.route('/env-env-history', methods=['GET'])
def env_env_history_endpoint():
    """
    Legacy endpoint for full environment data history (redundant).
    GET: Return all stored history entries.
    """
    return jsonify(env_env_history)

@app.route('/plant-latest', methods=['GET', 'POST'])
def plant_latest_endpoint():
    """
    Endpoint for latest plant sensor data (e.g., moisture, soil temperature).
    POST: Store new data as latest and append to history.
    GET:  Return latest data if available.
    """
    global plant_latest
    if request.method == 'POST':
        data = request.get_json(force=True)
        plant_latest = data
        plant_history.append(data)
        if len(plant_history) > PLANT_HISTORY_LIMIT:
            plant_history.pop(0)
        return jsonify({'status': 'ok'}), 200
    else:
        if plant_latest is not None:
            return jsonify(plant_latest)
        else:
            return jsonify({'error': 'No data yet'}), 404

@app.route('/plant-history', methods=['GET'])
def plant_history_endpoint():
    """
    Endpoint for full plant sensor data history.
    GET: Return all stored history entries.
    """
    return jsonify(plant_history)

@app.route('/sets-latest', methods=['GET', 'POST'])
def sets_latest_endpoint():
    """
    Endpoint for latest sets data (e.g., flow, pressure).
    POST: Store new data as latest and append to history.
    GET:  Return latest data if available.
    """
    global sets_latest
    if request.method == 'POST':
        data = request.get_json(force=True)
        sets_latest = data
        sets_history.append(data)
        if len(sets_history) > SETS_HISTORY_LIMIT:
            sets_history.pop(0)
        return jsonify({'status': 'ok'}), 200
    else:
        if sets_latest is not None:
            return jsonify(sets_latest)
        else:
            return jsonify({'error': 'No data yet'}), 404

@app.route('/sets-history', methods=['GET'])
def sets_history_endpoint():
    """
    Endpoint for full sets data history.
    GET: Return all stored history entries.
    """
    return jsonify(sets_history)

@app.route('/environment-latest', methods=['GET', 'POST'])
def environment_latest_endpoint():
    """
    Endpoint for latest environment data (e.g., temperature, humidity, wind, barometric pressure).
    POST: Store new data as latest and append to history.
    GET:  Return latest data if available.
    """
    global environment_latest
    if request.method == 'POST':
        data = request.get_json(force=True)
        environment_latest = data
        environment_history.append(data)
        if len(environment_history) > ENVIRONMENT_HISTORY_LIMIT:
            environment_history.pop(0)
        return jsonify({'status': 'ok'}), 200
    else:
        if environment_latest is not None:
            return jsonify(environment_latest)
        else:
            return jsonify({'error': 'No data yet'}), 404

@app.route('/environment-history', methods=['GET'])
def environment_history_endpoint():
    """
    Endpoint for full environment data history.
    GET: Return all stored history entries.
    """
    return jsonify(environment_history)

# -----------------------------
# Main entry point
# -----------------------------
if __name__ == '__main__':
    # Start the Flask server, listening on all network interfaces (0.0.0.0) at port 8000
    app.run(host='0.0.0.0', port=8000)
