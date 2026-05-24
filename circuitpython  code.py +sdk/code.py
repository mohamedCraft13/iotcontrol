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

relays = {
    "relay1": digitalio.DigitalInOut(board.GP16),
    "relay2": digitalio.DigitalInOut(board.GP17),
    "relay3": digitalio.DigitalInOut(board.GP18),
    "relay4": digitalio.DigitalInOut(board.GP19),
}

for r in relays.values():
    r.direction = digitalio.Direction.OUTPUT
    r.value = 1  # OFF (active LOW)

devled = digitalio.DigitalInOut(board.GP15)
devled.direction = digitalio.Direction.OUTPUT

dht11_sensor = adafruit_dht.DHT11(board.GP3)
time.sleep(2)

# ================= GLOBALS =================

auto_mode = False

# ================= WIFI =================

print("Connecting to WiFi...")
ssid = os.getenv("WIFI_SSID")
password = os.getenv("WIFI_PASSWORD")

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

pool = socketpool.SocketPool(wifi.radio)

# ================= MQTT SETUP =================

device = IoTDevice(device_id="pico_01", broker="broker.hivemq.com", pool=pool)

def handle_commands(command, value):
    global auto_mode
    if command in relays:
        relays[command].value = 0 if value.lower() == "on" else 1
    if command == "auto_mode":
        auto_mode = value.lower() == "on"
        print("Auto mode:", auto_mode)

device.on_command_received = handle_commands

print("Connecting to MQTT broker...")
try:
    device.connect()
    print("MQTT Connected!")
except Exception as e:
    print("MQTT Error:", e)
    led_paterns.sos(devled)

# ================= HELPERS =================

def interruptible_sleep(seconds):
    """Sleep while keeping MQTT alive; exits early if auto_mode turns off."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and auto_mode:
        device.update()
        time.sleep(0.1)


# ================= AUTO MOD LOOP  =================

def automode_loop():
    print("Auto mode started")
    while auto_mode:
        temp = dht11_sensor.temperature
        try:
            if  int(temp) >= 23:  
                relays["relay1"].value = 0       # turn ON
            else:
                relays["relay1"].value = 1       # turn OFF

            print(temp)
            time.sleep(0.5)
        except:
            print("error")


        
    device.send_telemetry({"online": True})
    print("Auto mode stopped")

# ================= MAIN LOOP =================

last_telemetry_time = 0
telemetry_interval = 5

while True:
    try:
        device.update()
    except Exception as e:
        print("MQTT lost, reconnecting...", e)
        try:
            device.reconnect()
        except:
            pass

    if auto_mode:
        automode_loop()  # blocks until auto_mode = False

    current_time = time.monotonic()
    if current_time - last_telemetry_time >= telemetry_interval:
        try:
            temp = dht11_sensor.temperature
            humi = dht11_sensor.humidity
            if temp is not None and humi is not None:
                device.send_telemetry({
                    "temp": temp,
                    "humi": humi,
                    "online": True,
                    "relay1": "on" if relays["relay1"].value == 0 else "off",
                    "relay2": "on" if relays["relay2"].value == 0 else "off",
                    "relay3": "on" if relays["relay3"].value == 0 else "off",
                    "relay4": "on" if relays["relay4"].value == 0 else "off",
                })
                print(f"Sent: {temp}°C, {humi}%")
        except RuntimeError:
            dht11_sensor.exit()
            dht11_sensor = adafruit_dht.DHT11(board.GP3)
        except Exception as e:
            print("Telemetry Error:", e)

        last_telemetry_time = current_time

    time.sleep(0.1)
