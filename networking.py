import socket
import json
import paho.mqtt.client as mqtt
from logging_utils import log_stdout, log_error

MQTT_BROKER = "100.116.147.6"
MQTT_PORT = 1883
MQTT_TOPIC = "sensors/plant"

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
        client = mqtt.Client()
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.publish(MQTT_TOPIC, json.dumps(payload))
        client.disconnect()
        log_stdout("MQTT publish successful")
    except Exception as e:
        log_error(f"[MQTT ERROR] {str(e)}")
        log_error(f"Failed payload: {json.dumps(payload)}")
