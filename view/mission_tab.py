# === PFAD-B FULL FILE: QGCR/view/mission_tab.py ===

import tkinter as tk
from tkinter import ttk


class MissionTab(ttk.Frame):
    """
    Mission-Tab (Tkinter, MVC-korrekt):
    - View ruft Controller auf
    - Controller ruft Model auf
    - View zeigt nur Daten an
    """

    def __init__(self, parent, controller):
        super().__init__(parent)

        self.controller = controller

        # ------------------------------------------------------------
        # Buttons
        # ------------------------------------------------------------
        button_frame = ttk.Frame(self)
        button_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

        self.btn_upload = ttk.Button(
            button_frame,
            text="Upload",
            command=lambda: self.controller.request_mission_upload(),
            state="disabled"
        )
        self.btn_upload.pack(side=tk.LEFT, padx=4)

        self.btn_download = ttk.Button(
            button_frame,
            text="Download",
            command=lambda: self.controller.handle_button_event("MISSION_DOWNLOAD"),
            state="disabled"
        )
        self.btn_download.pack(side=tk.LEFT, padx=4)

        # ------------------------------------------------------------
        # Stop-Button (neu)
        # ------------------------------------------------------------
        self.btn_stop = ttk.Button(
            button_frame,
            text="Stop",
            command=lambda: self.controller.handle_button_event("MISSION_STOP"),
            state="disabled"
        )
        self.btn_stop.pack(side=tk.LEFT, padx=4)

        # ------------------------------------------------------------
        # Mission starten (armt + AUTO.MISSION)
        # ------------------------------------------------------------
        self.btn_start = ttk.Button(
            button_frame,
            text="Start",
            command=lambda: self.controller.handle_button_event("MISSION_START"),
            state="disabled"
        )
        self.btn_start.pack(side=tk.LEFT, padx=12)

        # ------------------------------------------------------------
        # Home Position
        # ------------------------------------------------------------
        self.lbl_home = ttk.Label(self, text="Home: -")
        self.lbl_home.pack(anchor="w", padx=5, pady=2)

        # ------------------------------------------------------------
        # Mission Info
        # ------------------------------------------------------------
        self.lbl_mission = ttk.Label(self, text="Mission: -")
        self.lbl_mission.pack(anchor="w", padx=5, pady=2)

        # ------------------------------------------------------------
        # Upload-/Download-Status
        # ------------------------------------------------------------
        self.lbl_status = ttk.Label(self, text="Status: -")
        self.lbl_status.pack(anchor="w", padx=5, pady=2)

        # ------------------------------------------------------------
        # Missionsliste
        # ------------------------------------------------------------
        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # ------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------
    def set_enabled(self, upload: bool, download: bool, stop: bool, start: bool = False):
        """Aktiviert/Deaktiviert Upload/Download/Stop/Start Buttons."""
        self.btn_upload["state"] = "normal" if upload else "disabled"
        self.btn_download["state"] = "normal" if download else "disabled"
        self.btn_stop["state"] = "normal" if stop else "disabled"
        self.btn_start["state"] = "normal" if start else "disabled"

    def show_mission(self, data):
        """
        Zeigt Home, Mission, Status und Wegpunkte an.
        data = GUIController.get_mission_view_data()
        """
        self.lbl_home["text"] = data["home_text"]
        self.lbl_mission["text"] = data["mission_text"]
        self.lbl_status["text"] = data["status_text"]

        # Liste nur bei Änderung neu aufbauen (kein Flackern / Scroll-Reset)
        if list(self.listbox.get(0, "end")) != data["waypoints"]:
            self.listbox.delete(0, "end")
            for line in data["waypoints"]:
                self.listbox.insert("end", line)
