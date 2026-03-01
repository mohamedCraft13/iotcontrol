#Copyright (C) 2026 Mohamed Akoum

import json, os
from kivy.lang import Builder
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.textfield import MDTextField
from sdk import IoTDevice
import shutil



class SensorCard(MDCard):
    def __init__(self, name, data_key, unit, on_remove, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = "75dp"
        self.padding = "15dp"
        self.md_bg_color = [0.1, 0.1, 0.2, 1]
        self.radius = [15,]
        self.data_key = data_key
        content = MDBoxLayout(orientation='vertical')
        content.add_widget(MDLabel(text=name, font_style="Caption", theme_text_color="Secondary"))
        self.val_label = MDLabel(text=f"-- {unit}", font_style="H6", bold=True)
        content.add_widget(self.val_label)
        self.add_widget(content)
        self.add_widget(MDIconButton(icon="close", pos_hint={"center_y": .5}, on_release=lambda x: on_remove(name, data_key)))

class RelayCard(MDCard):
    def __init__(self, name, cmd, state, on_remove, on_power, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = "85dp"
        self.padding = "10dp"
        self.spacing = "10dp"
        self.radius = [15,]
        self.cmd = cmd
        self.on_power = on_power
        self.card_state = state  # Loaded from config
        
        layout = MDBoxLayout(orientation="horizontal", spacing=10)
        layout.add_widget(MDLabel(text=name.upper(), bold=True, size_hint_x=0.4))
        
        self.on_btn = MDRaisedButton(text="ON", md_bg_color="green", on_release=lambda x: self.press_action("on"))
        layout.add_widget(self.on_btn)
        
        self.off_btn = MDRaisedButton(text="OFF", md_bg_color="red", on_release=lambda x: self.press_action("off"))
        layout.add_widget(self.off_btn)
        
        layout.add_widget(MDIconButton(icon="trash-can", theme_text_color="Error", on_release=lambda x: on_remove(name, cmd)))
        self.add_widget(layout)
        self.update_visual()

    def press_action(self, card_state):
        self.card_state = card_state
        self.on_power(self.cmd, card_state) # This now handles saving too
        self.update_visual()

    def update_visual(self):
        if self.card_state == "on":
            self.md_bg_color = ("#3e7a62")
        else:
            self.md_bg_color = ("#7a3e3e")

class IoTControlApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        self.icon = 'icon.png' 
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.config_path = os.path.join(self.user_data_dir, "config.json")

        # old location (where you used to store it)
        self.old_config_path = os.path.join(os.getcwd(), "config.json")
        self.migrate_old_config()
        self.load_data()
        self.device_id = self.device_options[0] if self.device_options else "None"
        self.hub = IoTDevice(device_id=self.mqtt_id, broker=self.mqtt_broker, port=self.mqtt_port)
        self.hub.on_telemetry_received = self.on_telemetry_callback
        self.reconnect_hub()
        Clock.schedule_interval(self.check_connection, 2)
        return Builder.load_string('''
MDBoxLayout:
    orientation: 'vertical'
    MDTopAppBar:
        title: "IoT Control"
        right_action_items: [["cog", lambda x: app.open_settings()], ["chart-bell-curve", lambda x: app.add_widget_dialog()], ["plus-box", lambda x: app.add_relay_dialog()]]
    MDLabel:
        id: conn_warning
        text: "⚠️ SERVER OFFLINE"
        halign: "center"
        size_hint_y: None
        height: 0
        opacity: 0
        md_bg_color: 0.8, 0, 0, 1
        color: 1, 1, 1, 1
    MDBoxLayout:
        orientation: 'horizontal'
        size_hint_y: None
        height: "65dp"
        padding: "10dp"
        spacing: "10dp"
        MDRaisedButton:
            id: drop_item
            
            text: app.device_id
            size_hint_x: 0.5
            font_size: "18sp"
            on_release: app.menu.open()
        MDIconButton:
            icon: "plus-circle"
            on_release: app.add_device_dialog()
        MDIconButton:
            icon: "delete-forever"
            theme_text_color: "Error"
            on_release: app.remove_device_confirm()
    ScrollView:
        MDBoxLayout:
            id: scroll_content
            orientation: 'vertical'
            adaptive_height: True
            padding: "15dp"
            spacing: "15dp"
            MDLabel:
                text: "SENSORS"
                font_style: "Button"
                theme_text_color: "Secondary"
                size_hint_y: None
                height: "30dp"
            MDBoxLayout:
                id: sensor_container
                orientation: 'vertical'
                adaptive_height: True
                spacing: "10dp"
            MDLabel:
                text: "RELAYS"
                font_style: "Button"
                theme_text_color: "Secondary"
                size_hint_y: None
                height: "30dp"
            MDBoxLayout:
                id: relay_container
                orientation: 'vertical'
                adaptive_height: True
                spacing: "10dp"
''')

    def check_connection(self, dt):
        if not self.hub.is_connected():
            self.root.ids.conn_warning.height = "35dp"
            self.root.ids.conn_warning.opacity = 1
        else:
            self.root.ids.conn_warning.height = 0
            self.root.ids.conn_warning.opacity = 0

    def on_telemetry_callback(self, dev_id, data, timestamp):
        Clock.schedule_once(lambda dt: self.update_widgets(dev_id, data))

    def update_widgets(self, dev_id, data):
        if dev_id != self.device_id:
            return

        # ---- UPDATE SENSORS ----
        for widget in self.root.ids.sensor_container.children:
            if isinstance(widget, SensorCard):
                val = data.get(widget.data_key, "--")
                unit = next((s['unit'] for s in self.sensor_data[self.device_id]
                            if s['key'] == widget.data_key), "")
                widget.val_label.text = f"{val} {unit}"

        # ---- UPDATE RELAYS FROM DEVICE DATA ----
        for widget in self.root.ids.relay_container.children:
            if isinstance(widget, RelayCard):
                if widget.cmd in data:
                    device_state = str(data[widget.cmd]).lower()

                    if device_state in ("on", "off"):
                        widget.card_state = device_state
                        widget.update_visual()

                        # also save it to config memory
                        for r in self.device_data[self.device_id]:
                            if r["cmd"] == widget.cmd:
                                r["state"] = device_state

        self.save_data()

    def open_settings(self):
        box = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, height="250dp")
        self.set_broker = MDTextField(text=self.mqtt_broker, hint_text="Broker IP")
        self.set_port = MDTextField(text=str(self.mqtt_port), hint_text="Port", input_filter="int")
        self.set_mqtt = MDTextField(text=self.mqtt_id, hint_text="Device MQTT ID")
        box.add_widget(self.set_broker)
        box.add_widget(self.set_port)
        box.add_widget(self.set_mqtt)


        self.theme_btn = MDRaisedButton(
            text=f"Theme: {self.theme_cls.theme_style}",
            on_release=self.toggle_theme,
            size_hint_x=1
        )
        box.add_widget(self.theme_btn)


        
        self.dialog = MDDialog(
            title="Settings",
            type="custom",
            content_cls=box,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(text="SAVE", on_release=self.save_settings)
            ]
        )
        self.dialog.open()

    def save_settings(self, *args):
        self.mqtt_broker = self.set_broker.text
        self.mqtt_port = int(self.set_port.text) if self.set_port.text else 1883
        self.mqtt_id = self.set_mqtt.text if self.set_mqtt.text else "None"
        self.save_data()
        self.dialog.dismiss()
        self.reconnect_hub()

    def reconnect_hub(self):
        self.hub.disconnect()
        self.hub.broker = self.mqtt_broker
        self.hub.port=self.mqtt_port
        self.hub.mqtt_id = self.mqtt_id
        self.hub.connect()
        if self.mqtt_id != "None":
            self.hub.subscribe_telemetry(self.mqtt_id)

    def load_data(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                d = json.load(f)
                self.mqtt_broker = d.get("broker", "192.168.1.3")
                self.mqtt_port = d.get("port", 1883)
                self.mqtt_id = d.get("id", "default_device")
                self.theme_cls.theme_style = d.get("theme", "Dark") 
                self.device_options = d.get("devices", [])
                self.device_data = d.get("relay_map", {})
                self.sensor_data = d.get("sensor_map", {})
        else:
            self.mqtt_broker = "192.168.1.3"
            self.mqtt_id = "default_device"
            self.mqtt_port = 1883
            self.theme_cls.theme_style = "Dark"
            self.device_options, self.device_data, self.sensor_data = [], {}, {}




    def toggle_theme(self, *args):
        # Switch between Dark and Light
        self.theme_cls.theme_style = (
            "Light" if self.theme_cls.theme_style == "Dark" else "Dark"
        )
        self.save_data()
        
        # Update button text if the dialog is open
        if hasattr(self, 'theme_btn'):
            self.theme_btn.text = f"Theme: {self.theme_cls.theme_style}"

    def migrate_old_config(self):
        # if new config does NOT exist yet
        if not os.path.exists(self.config_path):
            # but old config DOES exist
            if os.path.exists(self.old_config_path):
                shutil.copy(self.old_config_path, self.config_path)
                print("Old config migrated to new app storage.")

    def save_data(self):
        with open(self.config_path, "w") as f:
            json.dump({
                "broker": self.mqtt_broker,
                "port": self.mqtt_port,
                "id": self.mqtt_id, 
                "theme": self.theme_cls.theme_style,
                "devices": self.device_options,
                "relay_map": self.device_data,
                "sensor_map": self.sensor_data
            }, f, indent=4)

    def on_start(self):
        self.setup_menu()
        self.render_all()

    def setup_menu(self):
        items = [{"viewclass": "OneLineListItem", "text": i,"font_size": "8sp" ,"font_style": "Caption", "on_release": lambda x=i: self.set_device(x)} for i in self.device_options]
        self.menu = MDDropdownMenu(caller=self.root.ids.drop_item, items=items, width=170)

    def set_device(self, choice):
        self.device_id = choice
        self.menu.dismiss()
        self.reconnect_hub()
        self.render_all()

    def render_all(self):
        self.root.ids.drop_item.text = self.device_id
        rel_con, sen_con = self.root.ids.relay_container, self.root.ids.sensor_container
        rel_con.clear_widgets()
        sen_con.clear_widgets()
        
        for r in self.device_data.get(self.device_id, []):
            # Pass the saved state from config (default to off)
            state = r.get("state", "off")
            rel_con.add_widget(RelayCard(name=r["name"], cmd=r["cmd"], state=state, on_remove=self.remove_relay, on_power=self.send_cmd))
        
        for s in self.sensor_data.get(self.device_id, []):
            sen_con.add_widget(SensorCard(name=s["name"], data_key=s["key"], unit=s["unit"], on_remove=self.remove_sensor))

    def send_cmd(self, cmd, state):
        # 1. Update the state in memory
        for r in self.device_data.get(self.device_id, []):
            if r["cmd"] == cmd:
                r["state"] = state
        # 2. Save to config.json
        self.save_data()
        # 3. Send over network
        self.hub.send_command(self.device_id, cmd, state)

    def remove_relay(self, n, c):
        self.device_data[self.device_id] = [r for r in self.device_data[self.device_id] if not (r["name"]==n and r["cmd"]==c)]
        self.save_data()
        self.render_all()

    def remove_sensor(self, n, k):
        self.sensor_data[self.device_id] = [s for s in self.sensor_data[self.device_id] if not (s["name"]==n and s["key"]==k)]
        self.save_data()
        self.render_all()

    def remove_device_confirm(self):
        if self.device_id == "None": return
        self.dialog = MDDialog(title=f"Delete {self.device_id}?", text="Wipes all settings for this device.", buttons=[MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()), MDRaisedButton(text="DELETE", md_bg_color="red", on_release=self.delete_device)])
        self.dialog.open()

    def delete_device(self, *args):
        target = self.device_id
        if target in self.device_options:
            self.device_options.remove(target)
            self.device_data.pop(target, None)
            self.sensor_data.pop(target, None)
        self.device_id = self.device_options[0] if self.device_options else "None"
        self.save_data()
        self.setup_menu()
        self.render_all()
        self.dialog.dismiss()

    def add_device_dialog(self):
        self.field = MDTextField(hint_text="Device ID")
        self.dialog = MDDialog(title="Add Device", type="custom", content_cls=self.field, buttons=[MDRaisedButton(text="ADD", on_release=self.confirm_dev)])
        self.dialog.open()

    def confirm_dev(self, *args):
        if self.field.text and self.field.text not in self.device_options:
            self.device_options.append(self.field.text)
            self.device_data[self.field.text] = []
            self.sensor_data[self.field.text] = []
            self.save_data()
            self.setup_menu()
            self.set_device(self.field.text)
        self.dialog.dismiss()

    def add_widget_dialog(self):
        if self.device_id == "None": return
        box = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, height="180dp")
        self.s_name, self.s_key, self.s_unit = MDTextField(hint_text="Label"), MDTextField(hint_text="JSON Key"), MDTextField(hint_text="Unit")
        box.add_widget(self.s_name); box.add_widget(self.s_key); box.add_widget(self.s_unit)
        self.dialog = MDDialog(title="New widget", type="custom", content_cls=box, buttons=[MDRaisedButton(text="ADD", on_release=self.confirm_sensor)])
        self.dialog.open()

    def confirm_sensor(self, *args):
        self.sensor_data.setdefault(self.device_id, []).append({"name": self.s_name.text, "key": self.s_key.text, "unit": self.s_unit.text})
        self.save_data()
        self.render_all()
        self.dialog.dismiss()

    def add_relay_dialog(self):
        if self.device_id == "None": return
        box = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, height="120dp")
        self.n_in, self.c_in = MDTextField(hint_text="Label"), MDTextField(hint_text="Command")
        box.add_widget(self.n_in); box.add_widget(self.c_in)
        self.dialog = MDDialog(title="New control card", type="custom", content_cls=box, buttons=[MDRaisedButton(text="SAVE", on_release=self.confirm_relay)])
        self.dialog.open()

    def confirm_relay(self, *args):
        # Default new relays to 'off' state
        self.device_data.setdefault(self.device_id, []).append({"name": self.n_in.text, "cmd": self.c_in.text, "state": "off"})
        self.save_data()
        self.render_all()
        self.dialog.dismiss()

if __name__ == "__main__":
    IoTControlApp().run()
