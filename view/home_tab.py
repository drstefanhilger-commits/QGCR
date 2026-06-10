# === PFAD-B FULL FILE: QGCR/view/home_tab.py ===

import tkinter as tk
from tkinter import ttk


class HomeTab(ttk.Frame):
    """
    Home-Tab mit:
    - Button-Leiste (Arm, Disarm, Takeoff, Land, Reset)
    - Canvas (Map/Plot Platzhalter)
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

        # RESET Button
        self.reset_button = ttk.Button(
            frame, text="RESET",
            command=lambda: self.controller.handle_button_event("RESET")
        )
        self.reset_button.pack(side=tk.LEFT, padx=5)

    # ------------------------------------------------------------
    # Canvas
    # ------------------------------------------------------------
    def _build_canvas(self):
        self.canvas = tk.Canvas(self, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.create_text(
            400, 250,
            text="2D Plot Canvas",
            fill="gray",
            font=("Arial", 20)
        )

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
