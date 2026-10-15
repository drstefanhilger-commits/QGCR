# === PFAD-B FULL FILE: QGCR/view/home_tab.py ===

import tkinter as tk
from tkinter import ttk

from QGCR.view.plot_2d import Plot2D
from QGCR.view.plot_alt import AltitudePlot


class HomeTab(ttk.Frame):
    """
    Home-Tab mit:
    - Button-Leiste (Arm, Disarm, Takeoff, Land, Mission, Reset) + Modellauswahl
    - 2D-Plot (Missions-Track, Start- und Landepunkt) + Höhen-Plot
    """

    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller

        self._build_buttons()
        self._build_canvas()

    # ------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------
    def _build_buttons(self):
        frame = ttk.Frame(self)
        frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.arm_button = ttk.Button(
            frame, text="ARM",
            command=lambda: self.controller.handle_button_event("ARM")
        )
        self.arm_button.pack(side=tk.LEFT, padx=5)

        self.disarm_button = ttk.Button(
            frame, text="DISARM",
            command=lambda: self.controller.handle_button_event("DISARM")
        )
        self.disarm_button.pack(side=tk.LEFT, padx=5)

        self.takeoff_button = ttk.Button(
            frame, text="TAKEOFF",
            command=lambda: self.controller.handle_button_event("TAKEOFF")
        )
        self.takeoff_button.pack(side=tk.LEFT, padx=5)

        self.land_button = ttk.Button(
            frame, text="LAND",
            command=lambda: self.controller.handle_button_event("LAND")
        )
        self.land_button.pack(side=tk.LEFT, padx=5)

        # Mission im Flug starten (AUTO.MISSION)
        self.mission_button = ttk.Button(
            frame, text="MISSION",
            command=lambda: self.controller.handle_button_event("MISSION_START")
        )
        self.mission_button.pack(side=tk.LEFT, padx=5)

        # RESET Button
        self.reset_button = ttk.Button(
            frame, text="RESET",
            command=lambda: self.controller.handle_button_event("RESET")
        )
        self.reset_button.pack(side=tk.LEFT, padx=5)

        # Track + Höhenverlauf im Plot löschen
        self.clear_track_button = ttk.Button(
            frame, text="Track löschen",
            command=lambda: self.controller.clear_track()
        )
        self.clear_track_button.pack(side=tk.LEFT, padx=15)

        # Modellauswahl (Wechsel löst RESET aus)
        choices = self.controller.get_model_choices() if self.controller else []
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(
            frame, textvariable=self.model_var, values=choices,
            state="readonly", width=22
        )
        self.model_combo.pack(side=tk.RIGHT, padx=5)
        ttk.Label(frame, text="Modell:").pack(side=tk.RIGHT)
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_selected)

        if self.controller:
            self.model_var.set(self.controller.get_selected_model() or "")

    # ------------------------------------------------------------
    # Canvas
    # ------------------------------------------------------------
    def _build_canvas(self):
        # Höhen-Plot unten, 2D-Plot (Missions-Track, Start- und Landepunkt) darüber
        self.alt_plot = AltitudePlot(self)
        self.alt_plot.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = Plot2D(self)
        self.canvas.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------
    def clear(self):
        self.canvas.delete("all")

    def draw_text(self, x, y, text, color="black"):
        self.canvas.create_text(x, y, text=text, fill=color)

    # ------------------------------------------------------------
    # Button-Enable API
    # ------------------------------------------------------------
    def set_arm_enabled(self, enabled: bool):
        self.arm_button.configure(state="normal" if enabled else "disabled")

    def set_disarm_enabled(self, enabled: bool):
        self.disarm_button.configure(state="normal" if enabled else "disabled")

    def set_land_enabled(self, enabled: bool):
        self.land_button.configure(state="normal" if enabled else "disabled")

    def set_reset_enabled(self, enabled: bool):
        self.reset_button.configure(state="normal" if enabled else "disabled")

    # ------------------------------------------------------------
    # Modellauswahl
    # ------------------------------------------------------------
    def _on_model_selected(self, _event=None):
        if self.controller:
            self.controller.request_model_change(self.model_var.get())

    def set_buttons_enabled(self, enabled: bool):
        """Buttons sperren (z. B. solange der FSL-Tab die Drohne steuert)."""
        state = "normal" if enabled else "disabled"
        for button in (self.arm_button, self.disarm_button, self.takeoff_button, self.land_button,
                       self.mission_button, self.reset_button, self.clear_track_button):
            button.configure(state=state)

    def set_model(self, model_name, enabled=True):
        """Aktuelles Modell anzeigen; Auswahl im Flug/RESET sperren."""
        if model_name and self.model_var.get() != model_name:
            self.model_var.set(model_name)
        self.model_combo.configure(state="readonly" if enabled else "disabled")
