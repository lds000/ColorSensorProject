import socket
import requests
import json
from logging_utils import log_stdout, log_error

RECEIVER_URL = "http://100.116.147.6:5000/soil-data"

def check_wifi():
    try:
        ip = socket.gethostbyname(socket.gethostname())
        status = f"Wi-Fi OK, IP: {ip}"
    except Exception:
        status = "Wi-Fi FAIL"
    log_stdout(status)
    if "FAIL" in status:
        log_error("Wi-Fi not connected")

def send_to_receiver(payload):
    log_stdout(f"Sending payload: {json.dumps(payload)}")
    try:
        response = requests.post(RECEIVER_URL, json=payload, timeout=5)
        log_stdout(f"POST status: {response.status_code}, response: {response.text}")
        response.raise_for_status()
    except Exception as e:
        log_error(f"[POST ERROR] {str(e)}")
        log_error(f"Failed payload: {json.dumps(payload)}")
