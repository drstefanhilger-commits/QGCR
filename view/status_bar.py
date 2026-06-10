# QGCR/view/status_bar.py

import tkinter as tk
from tkinter import ttk


class StatusBar(ttk.Frame):
    """
    Statusleiste am unteren Rand des Fensters.
    Zeigt HFSM-State, Sub-State, Mode, Heartbeat-Counter und Spinner an – wie in v1.16.
    """

    def __init__(self, parent, controller):
        super().__init__(parent)

        self.controller = controller

        # Default-Werte wie in v1.16
        self.hfsm_state = "-"
        self.sub_state = "-"
        self.mode = "-"
        self.armed = False
        self.hb_counter = 0
        self.spinner_index = 0
        self.spinner_frames = ["|", "/", "-", "\\"]

        # Textvariable für die Anzeige
        self.status_var = tk.StringVar()
        self._update_text()

        # EIN EINZIGES LABEL → alles nebeneinander
        self.label = ttk.Label(
            self,
            textvariable=self.status_var,
            anchor="w",
            padding=(8, 3)
        )
        self.label.grid(row=0, column=0, sticky="ew")

        # Layout
        self.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------
    # Öffentliche API – vom Controller aufrufbar
    # ------------------------------------------------------------

    def set_hfsm_state(self, value: str):
        self.hfsm_state = value
        self._update_text()

    def set_sub_state(self, value: str):
        self.sub_state = value
        self._update_text()

    def set_mode(self, value: str):
        self.mode = value
        self._update_text()

    def set_armed(self, value):
        self.armed = value
        self._update_text()

    def set_hb(self, value):
        self.hb_counter = value
        self._update_text()

    # def increment_hb(self):
    #     """Heartbeat-Counter erhöhen (wird vom MAVLink-Thread aufgerufen)."""
    #     self.hb_counter += 1
    #     self._update_text()

    def spin(self):
        """Spinner einen Schritt weiterdrehen."""
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)
        self._update_text()

    # ------------------------------------------------------------
    # Interne Methode zum Aktualisieren des Textes
    # ------------------------------------------------------------

    def _update_text(self):
        spinner = self.spinner_frames[self.spinner_index]
        self.status_var.set(
            f"HFSM: {self.hfsm_state}    "
            f"Sub: {self.sub_state}    "
            f"Mode: {self.mode}    "
            f"Armed: {'ARMED' if self.armed else 'DISARMED'}    "
            f"HB: {self.hb_counter}    "
            f"Spin: {spinner}"
        )
