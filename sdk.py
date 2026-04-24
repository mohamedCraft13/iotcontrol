# Copyright (C) 2026 Mohamed Akoum
#24-4-2026
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

        self.current_telemetry_topic = None

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"SDK: Connected! Subscribing to {self.cmd_topic}")
            client.subscribe(self.cmd_topic)

            # Re-subscribe to telemetry topic if one is already set
            # This handles both initial connect and reconnects
            if self.current_telemetry_topic:
                print(f"SDK: Re-subscribing to {self.current_telemetry_topic}")
                client.subscribe(self.current_telemetry_topic)
        else:
            print(f"SDK: Connection failed with rc={rc}")

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
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass

    def send_telemetry(self, sensor_data):
        topic = f"devices/{self.id}/telemetry"
        payload = {"ts": int(time.time()), "data": sensor_data}
        self.client.publish(topic, json.dumps(payload))

    def subscribe_telemetry(self, target_id):
        """
        Set the telemetry target. If already connected, subscribe immediately.
        If not yet connected, _on_connect will pick it up automatically.
        """
        topic = f"devices/{target_id}/telemetry"

        # Unsubscribe from old topic if switching devices
        if self.current_telemetry_topic and self.current_telemetry_topic != topic:
            print("SDK: Unsubscribing from", self.current_telemetry_topic)
            self.client.unsubscribe(self.current_telemetry_topic)

        self.current_telemetry_topic = topic

        # Only subscribe immediately if already connected,
        # otherwise _on_connect handles it when connection is ready
        if self.client.is_connected():
            print("SDK: Subscribing to", topic)
            self.client.subscribe(topic)
        else:
            print("SDK: Topic queued for subscribe on connect:", topic)

    def send_command(self, target_id, command, value):
        topic = f"devices/{target_id}/commands"
        payload = {"command": command, "value": value}
        self.client.publish(topic, json.dumps(payload))

    def is_connected(self):
        """Returns True if the MQTT client is currently connected to the broker."""
        return self.client.is_connected()