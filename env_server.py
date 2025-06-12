from flask import Flask, jsonify, request
from datetime import datetime
import threading

app = Flask(__name__)

# In-memory storage for latest and history
env_latest = None
env_history = []
HISTORY_LIMIT = 1000  # Limit history to avoid memory issues

@app.route('/env-latest', methods=['GET', 'POST'])
def env_latest_endpoint():
    global env_latest
    if request.method == 'POST':
        data = request.get_json(force=True)
        env_latest = data
        # Also append to history
        env_history.append(data)
        if len(env_history) > HISTORY_LIMIT:
            env_history.pop(0)
        return jsonify({'status': 'ok'}), 200
    else:  # GET
        if env_latest is not None:
            return jsonify(env_latest)
        else:
            return jsonify({'error': 'No data yet'}), 404

@app.route('/env-history', methods=['GET'])
def env_history_endpoint():
    # Return the full history (or just the latest if you want)
    return jsonify(env_history)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
