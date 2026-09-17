"""
Typed MQTT Client wrapper for pub/sub operations across control, telemetry, and alerts.
"""

import json
import time
from typing import Any, Callable, Dict, List, Optional

import core.config as cfg
import mqtt.topics as topics
from mqtt.broker import connect_broker, make_mqtt_client


class ICSCMQTTClient:
    def __init__(self, client_id: str = "", broker: str = cfg.BROKER, port: int = cfg.PORT):
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self.client = make_mqtt_client(self.on_connect, self.on_message, client_id=client_id)

        # Callbacks map: topic -> list of callback fn(topic, payload_dict)
        self._subscriptions: Dict[str, List[Callable[[str, Dict[str, Any]], None]]] = {}

    def connect(self):
        connect_broker(self.client, self.broker, self.port)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]):
        if topic not in self._subscriptions:
            self._subscriptions[topic] = []
            if self.client.is_connected():
                self.client.subscribe(topic)
        self._subscriptions[topic].append(callback)

    def publish_json(self, topic: str, payload: Dict[str, Any]):
        raw = json.dumps(payload)
        self.client.publish(topic, raw)

    def on_connect(self, client, userdata, flags, rc, properties=None):
        for topic in self._subscriptions.keys():
            client.subscribe(topic)

    def on_message(self, client, userdata, msg):
        raw = msg.payload.decode(errors="replace").strip()
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = {"raw_text": raw}

        callbacks = self._subscriptions.get(msg.topic, [])
        for cb in callbacks:
            try:
                cb(msg.topic, payload)
            except Exception as e:
                print(f"[!] Exception in MQTT callback for topic {msg.topic}: {e}")
