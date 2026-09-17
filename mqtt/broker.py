"""
MQTT broker client factory supporting both paho-mqtt 1.x and 2.x.
"""

import paho.mqtt.client as mqtt
import core.config as cfg


def make_mqtt_client(on_connect=None, on_message=None, client_id="") -> mqtt.Client:
    """Create an mqtt.Client configured for the installed paho version."""
    if hasattr(mqtt, "CallbackAPIVersion"):
        # paho-mqtt 2.x
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
        )
    else:
        # paho-mqtt 1.x
        client = mqtt.Client(client_id=client_id)

    if on_connect:
        client.on_connect = on_connect
    if on_message:
        client.on_message = on_message

    return client


def connect_broker(client: mqtt.Client, broker: str = cfg.BROKER, port: int = cfg.PORT, keepalive: int = cfg.KEEPALIVE):
    client.connect(broker, port, keepalive)
