"""
MqttPublisher: Centralized MQTT connection and publishing for sensor data.
Handles connection, reconnection, and error logging for robust operation.

Usage:
    mqtt = MqttPublisher(broker, port, topic_prefix)
    mqtt.publish(topic, payload)
"""
import time
import json
import logging
import threading
import paho.mqtt.client as mqtt

class MqttPublisher:
    def __init__(self, broker, port=1883, topic_prefix=None, client_id=None, log_file="error_log.txt"):
        self.broker = broker
        self.port = port
        self.topic_prefix = topic_prefix or ""
        self.client_id = client_id or f"SensorPublisher-{int(time.time())}"
        self.log_file = log_file
        self._lock = threading.Lock()
        self._connected = False
        self._client = mqtt.Client(client_id=self.client_id)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_log = self._on_log
        self._client.on_publish = self._on_publish
        self._connect()

    def _connect(self):
        try:
            self._client.connect(self.broker, self.port, keepalive=60)
            self._client.loop_start()
        except Exception as e:
            self._log_error(f"MQTT connect error: {e}")
            self._connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
        else:
            self._log_error(f"MQTT connection failed with code {rc}")
            self._connected = False

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        if rc != 0:
            self._log_error(f"Unexpected MQTT disconnect (rc={rc}), reconnecting...")
            self._connect()

    def _on_log(self, client, userdata, level, buf):
        if level >= mqtt.MQTT_LOG_ERR:
            self._log_error(f"MQTT log: {buf}")

    def _on_publish(self, client, userdata, mid):
        pass  # Could add debug logging here if needed

    def publish(self, topic, payload, qos=0, retain=False):
        full_topic = f"{self.topic_prefix}{topic}" if self.topic_prefix else topic
        try:
            with self._lock:
                if not self._connected:
                    self._connect()
                if isinstance(payload, (dict, list)):
                    payload = json.dumps(payload)
                result = self._client.publish(full_topic, payload, qos=qos, retain=retain)
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    self._log_error(f"MQTT publish failed: rc={result.rc}, topic={full_topic}")
        except Exception as e:
            self._log_error(f"MQTT publish exception: {e}")

    def _log_error(self, msg):
        try:
            with open(self.log_file, "a") as f:
                f.write(f"[MQTT][{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        except Exception:
            pass
