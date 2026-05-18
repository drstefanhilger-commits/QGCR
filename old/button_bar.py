# QGCR/view/button_bar.py

import tkinter as tk
from tkinter import ttk


class ButtonBar(ttk.Frame):
    """
    Obere Button-Leiste des GUI.
    Akzeptiert einen GUI-Controller, der die Aktionen ausführt.
    """

    def __init__(self, parent, controller):
        super().__init__(parent)

        self.controller = controller

        # Layout
        self.grid_columnconfigure(0, weight=1)

        # ------------------------------------------------------------
        # Buttons
        # ------------------------------------------------------------

        self.btn_connect = ttk.Button(
            self,
            text="Connect",
            command=self._on_connect
        )
        self.btn_connect.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.btn_arm = ttk.Button(
            self,
            text="Arm",
            command=self._on_arm
        )
        self.btn_arm.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.btn_takeoff = ttk.Button(
            self,
            text="Takeoff",
            command=self._on_takeoff
        )
        self.btn_takeoff.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        self.btn_land = ttk.Button(
            self,
            text="Land",
            command=self._on_land
        )
        self.btn_land.grid(row=0, column=3, padx=5, pady=5, sticky="w")

    # ------------------------------------------------------------
    # Button Callbacks
    # ------------------------------------------------------------

    def _on_connect(self):
        if hasattr(self.controller, "connect"):
            self.controller.connect()

    def _on_arm(self):
        if hasattr(self.controller, "arm"):
            self.controller.arm()

    def _on_takeoff(self):
        if hasattr(self.controller, "takeoff"):
            self.controller.takeoff()

    def _on_land(self):
        if hasattr(self.controller, "land"):
            self.controller.land()
