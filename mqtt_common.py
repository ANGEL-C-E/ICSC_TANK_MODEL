"""
Small compatibility layer so the project runs on both paho-mqtt 1.x and 2.x.

paho-mqtt >= 2.0 requires a CallbackAPIVersion as the first argument to
mqtt.Client(); 1.x does not accept it. This module picks the right call.
"""

import paho.mqtt.client as mqtt

from config import BROKER, KEEPALIVE, PORT


def make_client(on_connect, on_message):
    """Create an mqtt.Client configured for the installed paho version."""
    if hasattr(mqtt, "CallbackAPIVersion"):
        # paho-mqtt 2.x
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        client.on_connect = on_connect
        client.on_message = on_message
    else:
        # paho-mqtt 1.x
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
    return client


def connect(client, broker=BROKER, port=PORT, keepalive=KEEPALIVE):
    client.connect(broker, port, keepalive)
