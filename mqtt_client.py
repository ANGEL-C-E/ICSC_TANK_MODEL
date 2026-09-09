import json
import paho.mqtt.client as mqtt


class MQTTClient:
    def __init__(self, broker="localhost", port=1883):
        self.client = mqtt.Client()
        self.broker = broker
        self.port = port

        self.pump_callback = None
        self.valve_callback = None

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def connect(self):
        self.client.connect(self.broker, self.port)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print("MQTT connected")

        client.subscribe("ics/tank/command/pump")
        client.subscribe("ics/tank/command/valve")

        print("Subscribed to tank commands")

    def on_message(self, client, userdata, msg):
        try:
            value = float(msg.payload.decode())

            if msg.topic == "ics/tank/command/pump":
                print(f"Pump command: {value}")

                if self.pump_callback:
                    self.pump_callback(value)

            elif msg.topic == "ics/tank/command/valve":
                print(f"Valve command: {value}")

                if self.valve_callback:
                    self.valve_callback(value)

        except ValueError:
            print(f"Invalid command: {msg.payload.decode()}")

    def publish_telemetry(self, data):
        self.client.publish(
            "ics/tank/telemetry",
            json.dumps(data)
        )