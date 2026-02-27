import json
import os
import customtkinter as ctk
from sdk_old import IoTDevice

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

CONFIG_FILE = "config.json"

class IoTControlApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("IoT Control Pro")
        self.geometry("1200x800")
        self.state('zoomed')

        # --- Data Persistence ---
        self.load_data() # Sets self.device_options and self.device_data

        # Initial Active Device
        self.device_id = self.device_options[0] if self.device_options else "pico_01"

        # --- IoT Hub Setup ---
        self.hub = IoTDevice(device_id="control", broker="192.168.1.3")
        self.hub.on_telemetry_received = self.handle_tel
        try:
            self.hub.connect()
            if self.device_id: self.hub.subscribe_telemetry(self.device_id)
        except Exception as e:
            print(f"Connection error: {e}")

        # --- UI Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="DEVICE HUB", font=("Helvetica", 24, "bold")).pack(pady=30)

        self.dropdown = ctk.CTkOptionMenu(self.sidebar, values=self.device_options, command=self.on_device_change)
        self.dropdown.set(self.device_id)
        self.dropdown.pack(pady=10, padx=20)

        ctk.CTkButton(self.sidebar, text="Add Device", command=self.add_device_dialog).pack(pady=10, padx=20)

        # Main Content
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self.telemetry_label = ctk.CTkLabel(self.main_frame, text="Waiting for data...", font=("Helvetica", 22))
        self.telemetry_label.pack(pady=10)

        ctk.CTkButton(self.main_frame, text="+ Add Relay Card", fg_color="#1f538d", 
                      command=self.add_relay_flow).pack(anchor="e", pady=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self.main_frame, label_text=f"Controls for {self.device_id}")
        self.scroll_frame.pack(fill="both", expand=True)

        self.render_relays()

    # --- Persistence Logic ---
    def load_data(self):
        """Loads configuration from JSON file or sets defaults."""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                self.device_options = data.get("devices", ["pico_01"])
                self.device_data = data.get("relay_map", {"pico_01": []})
        else:
            self.device_options = ["pico_01"]
            self.device_data = {"pico_01": [{"name": "Default Relay", "cmd": "relay1"}]}
            self.save_data()

    def save_data(self):
        """Saves current state to JSON file."""
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "devices": self.device_options,
                "relay_map": self.device_data
            }, f, indent=4)

    # --- IoT & UI Logic ---
    def handle_tel(self, dev_id, data, timestamp):
        if dev_id == self.device_id:
            temp = data.get("temp", "N/A")
            self.telemetry_label.configure(text=f"Device: {dev_id} | Temp: {temp}°C")

    def on_device_change(self, choice):
        self.device_id = choice
        self.scroll_frame.configure(label_text=f"Controls for {self.device_id}")
        self.hub.subscribe_telemetry(self.device_id)
        self.render_relays()

    def render_relays(self):
        """Builds cards specific to the active device."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        current_relays = self.device_data.get(self.device_id, [])
        for relay in current_relays:
            card = ctk.CTkFrame(self.scroll_frame)
            card.pack(fill="x", pady=8, padx=10)

            lbl = ctk.CTkLabel(card, text=relay["name"].upper(), font=("Helvetica", 14, "bold"))
            lbl.pack(side="left", padx=20, pady=10)

            ctk.CTkButton(card, text="✕", width=40, fg_color="transparent", text_color="red",
                          command=lambda r=relay: self.remove_relay(r)).pack(side="right", padx=10)
            
            ctk.CTkButton(card, text="OFF", width=80, fg_color="#611e1e",
                          command=lambda r=relay: self.hub.send_command(self.device_id, r["cmd"], "off")).pack(side="right", padx=5)
            
            ctk.CTkButton(card, text="ON", width=80, fg_color="#1e6127",
                          command=lambda r=relay: self.hub.send_command(self.device_id, r["cmd"], "on")).pack(side="right", padx=5)

    def add_relay_flow(self):
        name = ctk.CTkInputDialog(text="Relay Label:", title="Step 1").get_input()
        if name:
            cmd = ctk.CTkInputDialog(text="MQTT Command (e.g. relay1):", title="Step 2").get_input()
            if cmd:
                if self.device_id not in self.device_data: self.device_data[self.device_id] = []
                self.device_data[self.device_id].append({"name": name, "cmd": cmd})
                self.save_data()
                self.render_relays()

    def remove_relay(self, relay_obj):
        self.device_data[self.device_id].remove(relay_obj)
        self.save_data()
        self.render_relays()

    def add_device_dialog(self):
        new_id = ctk.CTkInputDialog(text="New Device ID:", title="Add Device").get_input()
        if new_id and new_id not in self.device_options:
            self.device_options.append(new_id)
            self.device_data[new_id] = []
            self.dropdown.configure(values=self.device_options)
            self.save_data()

if __name__ == "__main__":
    app = IoTControlApp()
    app.mainloop()
