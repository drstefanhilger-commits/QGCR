# === PFAD-B FULL FILE: QGCR/view/telemetry_view.py ===

import tkinter as tk
from tkinter import ttk


class TelemetryView(ttk.Frame):
    """
    Zeigt grundlegende Telemetrie-Informationen an.
    - Mode
    - Armed
    - Altitude
    - PX4-Heartbeat
    - GUI-Spinner
    Öffentliche API:
    - update(telemetry_dict)
    - clear()
    """

    def __init__(self, parent):
        super().__init__(parent)

        self._build_ui()

    def _build_ui(self):
        grid = ttk.Frame(self)
        grid.pack(fill=tk.X, padx=5, pady=5)

        # Labels
        self.var_mode = tk.StringVar(value="UNKNOWN")
        self.var_armed = tk.StringVar(value="False")
        self.var_alt = tk.StringVar(value="0.0")
        self.var_px4_hb = tk.StringVar(value="-")
        self.var_gui_spinner = tk.StringVar(value="-")

        row = 0

        ttk.Label(grid, text="Mode:").grid(row=row, column=0, sticky=tk.W, padx=2, pady=2)
        ttk.Label(grid, textvariable=self.var_mode).grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)

        row += 1
        ttk.Label(grid, text="Armed:").grid(row=row, column=0, sticky=tk.W, padx=2, pady=2)
        ttk.Label(grid, textvariable=self.var_armed).grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)

        row += 1
        ttk.Label(grid, text="Alt [m]:").grid(row=row, column=0, sticky=tk.W, padx=2, pady=2)
        ttk.Label(grid, textvariable=self.var_alt).grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)

        row += 1
        ttk.Label(grid, text="PX4-HB:").grid(row=row, column=0, sticky=tk.W, padx=2, pady=2)
        ttk.Label(grid, textvariable=self.var_px4_hb).grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)

        row += 1
        ttk.Label(grid, text="GUI:").grid(row=row, column=0, sticky=tk.W, padx=2, pady=2)
        ttk.Label(grid, textvariable=self.var_gui_spinner).grid(row=row, column=1, sticky=tk.W, padx=2, pady=2)

    # ------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------
    def clear(self):
        self.var_mode.set("UNKNOWN")
        self.var_armed.set("False")
        self.var_alt.set("0.0")
        self.var_px4_hb.set("-")
        self.var_gui_spinner.set("-")

    def update(self, telemetry_dict):
        """
        Erwartet ein Dict wie:
        {
            "mode": "...",
            "armed": True/False,
            "alt": 12.3,
            "px4_hb": "...",
            "gui_spinner": "..."
        }
        """
        mode = telemetry_dict.get("mode", "UNKNOWN")
        armed = telemetry_dict.get("armed", False)
        alt = telemetry_dict.get("alt", 0.0)
        px4_hb = telemetry_dict.get("px4_hb", "-")
        gui_spinner = telemetry_dict.get("gui_spinner", "-")

        self.var_mode.set(str(mode))
        self.var_armed.set(str(armed))
        self.var_alt.set(f"{alt:.1f}")
        self.var_px4_hb.set(str(px4_hb))
        self.var_gui_spinner.set(str(gui_spinner))
