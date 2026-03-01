#Copyright (C) 2026 Mohamed Akoum

import json
import time
import paho.mqtt.client as mqtt

class IoTDevice:
    def __init__(self, device_id, broker, port=1883):
        self.id = device_id
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.broker = broker
        self.port = port
        
        self.cmd_topic = f"devices/{device_id}/commands"
        self.on_command_received = None
        self.on_telemetry_received = None

        self.current_telemetry_topic = None  # ⭐ NEW

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"SDK: Connected! Subscribing to {self.cmd_topic}")
            client.subscribe(self.cmd_topic)
        else:
            print(f"SDK: Connection failed: {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())

            if "commands" in msg.topic and self.on_command_received:
                self.on_command_received(data.get("command"), data.get("value"))

            elif "telemetry" in msg.topic and self.on_telemetry_received:
                sender_id = msg.topic.split("/")[1]
                self.on_telemetry_received(sender_id, data.get("data"), data.get("ts"))

        except Exception as e:
            print(f"SDK JSON Error: {e}")

    def connect(self):
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            print(f"SDK Connect Error: {e}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def send_telemetry(self, sensor_data):
        topic = f"devices/{self.id}/telemetry"
        payload = {"ts": int(time.time()), "data": sensor_data}
        self.client.publish(topic, json.dumps(payload))

    
    def subscribe_telemetry(self, target_id):
        topic = f"devices/{target_id}/telemetry"

        # unsubscribe old topic first
        if self.current_telemetry_topic:
            print("SDK: Unsubscribing from", self.current_telemetry_topic)
            self.client.unsubscribe(self.current_telemetry_topic)

        print("SDK: Subscribing to", topic)
        self.client.subscribe(topic)
        self.current_telemetry_topic = topic

    def send_command(self, target_id, command, value):
        topic = f"devices/{target_id}/commands"
        payload = {"command": command, "value": value}
        self.client.publish(topic, json.dumps(payload))

    def is_connected(self):
            """Returns True if the MQTT client is currently connected to the broker."""
            is_connected = self.client.is_connected()
            if is_connected:
                print("SDK: MQTT client is connected.")
            return is_connected
