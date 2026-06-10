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
            command=lambda: self.controller.handle_button_event("MISSION_UPLOAD"),
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
        # Missionsliste
        # ------------------------------------------------------------
        self.listbox = tk.Listbox(self, height=20)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # ------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------
    def set_enabled(self, upload: bool, download: bool, stop: bool):
        """Aktiviert/Deaktiviert Upload/Download/Stop Buttons."""
        self.btn_upload["state"] = "normal" if upload else "disabled"
        self.btn_download["state"] = "normal" if download else "disabled"
        self.btn_stop["state"] = "normal" if stop else "disabled"
