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

CONFIG_FILE = "config.json"

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
        self.add_widget(MDIconButton(icon="close", pos_hint={"center_y": .5}, 
                                     on_release=lambda x: on_remove(name, data_key)))

from kivy.clock import Clock
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.label import MDLabel

class RelayCard(MDCard):
    def __init__(self, name, cmd, on_remove, on_power, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = "85dp"
        self.padding = "10dp"
        self.spacing = "10dp"
        self.radius = [15,]
        self.cmd = cmd
        self.on_power = on_power

        # Current state: "on" or "off"
        self.card_state = "off"

        # Layout inside the card
        layout = MDBoxLayout(orientation="horizontal", spacing=10)
        layout.add_widget(MDLabel(text=name.upper(), bold=True, size_hint_x=0.4))

        # ON button
        self.on_btn = MDRaisedButton(text="ON", md_bg_color="green",
                                     on_release=lambda x: self.press_action("on"))
        layout.add_widget(self.on_btn)

        # OFF button
        self.off_btn = MDRaisedButton(text="OFF", md_bg_color="red",
                                      on_release=lambda x: self.press_action("off"))
        layout.add_widget(self.off_btn)

        # Trash button
        layout.add_widget(MDIconButton(icon="trash-can", theme_text_color="Error",
                                       on_release=lambda x: on_remove(name, cmd)))

        self.add_widget(layout)
        self.update_visual()

    def press_action(self, card_state):
        """Send command and update visual persistently"""
        self.card_state = card_state
        self.on_power(self.cmd, card_state)
        self.update_visual()

    def update_visual(self):
        """Set the card color based on current state"""
        if self.card_state == "on":
            self.md_bg_color = ("#3e7a62")  # green
        else:
            self.md_bg_color = ("#7a3e3e")  # red

class IoTControlApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        self.load_data()
        self.device_id = self.device_options[0] if self.device_options else "None"
        
        self.hub = IoTDevice(device_id="mobile_ctrl", broker=self.mqtt_broker)
        self.hub.on_telemetry_received = self.on_telemetry_callback
        self.reconnect_hub()

        Clock.schedule_interval(self.check_connection, 2)

        return Builder.load_string('''
MDBoxLayout:
    orientation: 'vertical'
    MDTopAppBar:
        title: "IoT Control Pro"
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
            size_hint_x: 0.7
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
        if dev_id == self.device_id:
            for widget in self.root.ids.sensor_container.children:
                if isinstance(widget, SensorCard):
                    # Pull value from the 'data' dict provided by your SDK
                    val = data.get(widget.data_key, "--")
                    unit = next((s['unit'] for s in self.sensor_data[self.device_id] if s['key'] == widget.data_key), "")
                    widget.val_label.text = f"{val} {unit}"

    def open_settings(self):
        self.set_field = MDTextField(text=self.mqtt_broker, hint_text="Broker IP")
        self.dialog = MDDialog(title="Settings", type="custom", content_cls=self.set_field,
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()),
                     MDRaisedButton(text="SAVE", on_release=self.save_settings)])
        self.dialog.open()

    def save_settings(self, *args):
        self.mqtt_broker = self.set_field.text
        self.save_data()
        self.dialog.dismiss()
        self.reconnect_hub()

    def reconnect_hub(self):
        self.hub.disconnect()
        self.hub.broker = self.mqtt_broker
        self.hub.connect()
        if self.device_id != "None":
            self.hub.subscribe_telemetry(self.device_id)

    def load_data(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                d = json.load(f)
                self.mqtt_broker = d.get("broker", "192.168.1.3")
                self.device_options = d.get("devices", [])
                self.device_data = d.get("relay_map", {})
                self.sensor_data = d.get("sensor_map", {})
        else:
            self.mqtt_broker, self.device_options, self.device_data, self.sensor_data = "192.168.1.3", [], {}, {}

    def save_data(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump({"broker": self.mqtt_broker, "devices": self.device_options, "relay_map": self.device_data, "sensor_map": self.sensor_data}, f, indent=4)

    def on_start(self): self.setup_menu(); self.render_all()
    def setup_menu(self):
        items = [{"viewclass": "OneLineListItem", "text": i, "on_release": lambda x=i: self.set_device(x)} for i in self.device_options]
        self.menu = MDDropdownMenu(caller=self.root.ids.drop_item, items=items, width_mult=4)
    def set_device(self, choice):
        self.device_id = choice; self.menu.dismiss(); self.reconnect_hub(); self.render_all()
    def render_all(self):
        self.root.ids.drop_item.text = self.device_id
        rel_con, sen_con = self.root.ids.relay_container, self.root.ids.sensor_container
        rel_con.clear_widgets(); sen_con.clear_widgets()
        for r in self.device_data.get(self.device_id, []):
            rel_con.add_widget(RelayCard(name=r["name"], cmd=r["cmd"], on_remove=self.remove_relay, on_power=self.send_cmd))
        for s in self.sensor_data.get(self.device_id, []):
            sen_con.add_widget(SensorCard(name=s["name"], data_key=s["key"], unit=s["unit"], on_remove=self.remove_sensor))
    def send_cmd(self, cmd, state): self.hub.send_command(self.device_id, cmd, state)
    def remove_relay(self, n, c):
        self.device_data[self.device_id] = [r for r in self.device_data[self.device_id] if not (r["name"]==n and r["cmd"]==c)]
        self.save_data(); self.render_all()
    def remove_sensor(self, n, k):
        self.sensor_data[self.device_id] = [s for s in self.sensor_data[self.device_id] if not (s["name"]==n and s["key"]==k)]
        self.save_data(); self.render_all()
    def remove_device_confirm(self):
        if self.device_id == "None": return
        self.dialog = MDDialog(title=f"Delete {self.device_id}?", text="Wipes all settings for this device.",
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()),
                     MDRaisedButton(text="DELETE", md_bg_color="red", on_release=self.delete_device)])
        self.dialog.open()
    def delete_device(self, *args):
        target = self.device_id
        if target in self.device_options: self.device_options.remove(target)
        self.device_data.pop(target, None); self.sensor_data.pop(target, None)
        self.device_id = self.device_options[0] if self.device_options else "None"
        self.save_data(); self.setup_menu(); self.render_all(); self.dialog.dismiss()
    def add_device_dialog(self):
        self.field = MDTextField(hint_text="Device ID")
        self.dialog = MDDialog(title="Add Device", type="custom", content_cls=self.field,
            buttons=[MDRaisedButton(text="ADD", on_release=self.confirm_dev)])
        self.dialog.open()
    def confirm_dev(self, *args):
        if self.field.text and self.field.text not in self.device_options:
            self.device_options.append(self.field.text); self.device_data[self.field.text] = []; self.sensor_data[self.field.text] = []
            self.save_data(); self.setup_menu(); self.set_device(self.field.text)
        self.dialog.dismiss()
    def add_widget_dialog(self):
        if self.device_id == "None": return
        box = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, height="180dp")
        self.s_name, self.s_key, self.s_unit = MDTextField(hint_text="Label"), MDTextField(hint_text="JSON Key"), MDTextField(hint_text="Unit")
        box.add_widget(self.s_name); box.add_widget(self.s_key); box.add_widget(self.s_unit)
        self.dialog = MDDialog(title="New Sensor", type="custom", content_cls=box, buttons=[MDRaisedButton(text="ADD", on_release=self.confirm_sensor)])
        self.dialog.open()
    def confirm_sensor(self, *args):
        self.sensor_data.setdefault(self.device_id, []).append({"name": self.s_name.text, "key": self.s_key.text, "unit": self.s_unit.text})
        self.save_data(); self.render_all(); self.dialog.dismiss()
    def add_relay_dialog(self):
        if self.device_id == "None": return
        box = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, height="120dp")
        self.n_in, self.c_in = MDTextField(hint_text="Label"), MDTextField(hint_text="Command")
        box.add_widget(self.n_in); box.add_widget(self.c_in)
        self.dialog = MDDialog(title="New Relay", type="custom", content_cls=box, buttons=[MDRaisedButton(text="SAVE", on_release=self.confirm_relay)])
        self.dialog.open()
    def confirm_relay(self, *args):
        self.device_data.setdefault(self.device_id, []).append({"name": self.n_in.text, "cmd": self.c_in.text})
        self.save_data(); self.render_all(); self.dialog.dismiss()

if __name__ == "__main__":
    IoTControlApp().run()
