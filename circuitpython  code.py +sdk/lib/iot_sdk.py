import json
import time
import adafruit_minimqtt.adafruit_minimqtt as MQTT

class IoTDevice:
    def __init__(self, device_id, broker, pool, port=1883):
        self.id = device_id
        self.client = MQTT.MQTT(
            broker=broker, 
            port=port, 
            socket_pool=pool,
            connect_retries=3,  # initial connect retries
        )

        self.cmd_topic = f"devices/{device_id}/commands"
        self.on_command_received = None
        self.on_telemetry_received = None

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    # ---------------- Internal Callbacks ----------------
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"SDK: Connected! Subscribing to {self.cmd_topic}")
            client.subscribe(self.cmd_topic)

    def _on_message(self, client, topic, payload):
        try:
            data = json.loads(payload)
            if "commands" in topic and self.on_command_received:
                self.on_command_received(data.get("command"), data.get("value"))
            elif "telemetry" in topic and self.on_telemetry_received:
                sender_id = topic.split("/")[1]
                self.on_telemetry_received(sender_id, data.get("data"), data.get("ts"))
        except Exception as e:
            print(f"SDK JSON Error: {e}")

    # ---------------- Public Methods ----------------
    def connect(self):
        """Connect to the MQTT broker"""
        self.client.connect()

    def update(self):
        """Process MQTT messages"""
        self.client.loop(timeout=1)

    def send_telemetry(self, sensor_data):
        topic = f"devices/{self.id}/telemetry"
        payload = {"ts": int(time.monotonic()), "data": sensor_data}
        self.client.publish(topic, json.dumps(payload))

    def subscribe_telemetry(self, target_id="+"):
        self.client.subscribe(f"devices/{target_id}/telemetry")

    def send_command(self, target_id, command, value):
        topic = f"devices/{target_id}/commands"
        payload = {"command": command, "value": value}
        self.client.publish(topic, json.dumps(payload))

    def is_connected(self):
        return self.client.is_connected()

    # ---------------- New Method: Reconnect ----------------
    def reconnect(self, retry_delay=5):
        """
        Attempt to reconnect until successful.
        Blocks until the connection is restored.
        """
        while True:
            try:
                print("SDK: Attempting MQTT reconnect...")
                self.client.connect()
                print("SDK: MQTT reconnected!")
                return  # exit loop when successful
            except Exception as e:
                print("SDK: Reconnect failed:", e)
                time.sleep(retry_delay)