from flask import Flask, jsonify, request
from datetime import datetime
import threading

app = Flask(__name__)

# In-memory storage for latest and history
env_latest = None
env_history = []
HISTORY_LIMIT = 1000  # Limit history to avoid memory issues

env_env_latest = None
env_env_history = []
ENV_HISTORY_LIMIT = 1000

plant_latest = None
plant_history = []
PLANT_HISTORY_LIMIT = 1000

sets_latest = None
sets_history = []
SETS_HISTORY_LIMIT = 1000

environment_latest = None
environment_history = []
ENVIRONMENT_HISTORY_LIMIT = 1000

@app.route('/env-latest', methods=['GET', 'POST'])
def env_latest_endpoint():
    global env_latest
    if request.method == 'POST':
        data = request.get_json(force=True)
        env_latest = data
        env_history.append(data)
        if len(env_history) > HISTORY_LIMIT:
            env_history.pop(0)
        return jsonify({'status': 'ok'}), 200
    else:
        if env_latest is not None:
            return jsonify(env_latest)
        else:
            return jsonify({'error': 'No data yet'}), 404

@app.route('/env-history', methods=['GET'])
def env_history_endpoint():
    # Return the full history (or just the latest if you want)
    return jsonify(env_history)

@app.route('/env-env-latest', methods=['GET', 'POST'])
def env_env_latest_endpoint():
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
    return jsonify(env_env_history)

@app.route('/plant-latest', methods=['GET', 'POST'])
def plant_latest_endpoint():
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
    return jsonify(plant_history)

@app.route('/sets-latest', methods=['GET', 'POST'])
def sets_latest_endpoint():
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
    return jsonify(sets_history)

@app.route('/environment-latest', methods=['GET', 'POST'])
def environment_latest_endpoint():
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
    return jsonify(environment_history)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
