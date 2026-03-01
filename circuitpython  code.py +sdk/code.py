import board
import digitalio
import wifi
import socketpool
import os
import time
import adafruit_dht
from iot_sdk import IoTDevice
import led_paterns

# ================= HARDWARE SETUP =================

# Relay pins (active LOW)
relays = {
    "relay1": digitalio.DigitalInOut(board.GP16),
    "relay2": digitalio.DigitalInOut(board.GP17),
    "relay3": digitalio.DigitalInOut(board.GP18),
    "relay4": digitalio.DigitalInOut(board.GP19),
}

# Configure all relays as outputs and turn them OFF initially
for r in relays.values():
    r.direction = digitalio.Direction.OUTPUT
    r.value = 1  # 1 = OFF (because active LOW)

# Onboard LED (status indicator)
devled = digitalio.DigitalInOut(board.GP15)
devled.direction = digitalio.Direction.OUTPUT

# DHT11 temperature & humidity sensor
dht11_sensor = adafruit_dht.DHT11(board.GP3)
time.sleep(2)  # Give sensor time to stabilize


# ================= HANDEL COMMANDS  =================

# Function to handle incoming MQTT commands
def handle_commands(command, value):
    print(f"MQTT Command: {command} -> {value}")

    # Only act if command matches a relay name
    if command in relays:
        if value.lower() == "on":
            relays[command].value = 0  # Turn relay ON
        elif value.lower() == "off":
            relays[command].value = 1  # Turn relay OFF





# ================= WIFI CONNECTION =================

print("Connecting to WiFi...")

ssid = os.getenv("WIFI_SSID")
password = os.getenv("WIFI_PASSWORD")

# Stop if WiFi credentials are missing
if not ssid or not password:
    print("Missing WiFi credentials!")
    led_paterns.blink(devled)

try:
    wifi.radio.connect(ssid, password)
    time.sleep(2)
    print("Connected! IP:", wifi.radio.ipv4_address)
except Exception as e:
    print("WiFi Error:", e)
    led_paterns.fast(devled)

# Create socket pool for networking
pool = socketpool.SocketPool(wifi.radio)


# ================= MQTT / SDK SETUP =================

device = IoTDevice(
    device_id="pico_01",
    broker="192.168.1.9",
    pool=pool
)

# Assign command handler
device.on_command_received = handle_commands

print("Connecting to MQTT broker...")
try:
    device.connect()
    print("MQTT Connected!")
except Exception as e:
    print("MQTT Error:", e)
    led_paterns.sos(devled)


# ================= MAIN LOOP =================

last_telemetry_time = 0
telemetry_interval = 5  # seconds

while True:
    # Keep MQTT alive
    try:
        device.update()
    except Exception as e:
        print("MQTT lost, reconnecting...", e)
        
        try:
            device.reconnect()
        except:
            pass

    current_time = time.monotonic()

    # Send telemetry every X seconds
    if current_time - last_telemetry_time >= telemetry_interval:
        try:
            # Read temperature and humidity
            temp = dht11_sensor.temperature
            humi = dht11_sensor.humidity

            if temp is not None and humi is not None:
                sensor_data = {
                    "temp": temp ,
                    "humi": humi,
                    "relay1": "on" if relays["relay1"].value == 0 else "off",
                    "relay2": "on" if relays["relay2"].value == 0 else "off",
                    "relay3": "on" if relays["relay3"].value == 0 else "off",
                    "relay4": "on" if relays["relay4"].value == 0 else "off",
                }

                # Send data to MQTT server
                device.send_telemetry(sensor_data)
                print(f"Sent: {temp}°C, {humi}%")

        except RuntimeError:
            # Normal DHT error (ignore and retry next cycle)
            dht11_sensor.exit()
            dht11_sensor = adafruit_dht.DHT11(board.GP3)

        except Exception as e:
            print("Telemetry Error:", e)
            led_paterns.slow(devled)

        last_telemetry_time = current_time

    time.sleep(0.1)