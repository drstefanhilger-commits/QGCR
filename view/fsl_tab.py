# === PFAD-B FULL FILE: QGCR/view/fsl_tab.py ===

import tkinter as tk
from tkinter import ttk

from QGCR.view.plot_2d import Plot2D
from QGCR.view.plot_alt import AltitudePlot


class FslTab(ttk.Frame):
    """
    Tab „FSL“ – kontrollierte FSL-Drohne:
    - Eingabe des (simulierten) Triggers: ID, Position Ost/Nord/Höhe [m] relativ zum
      FSL-Startpunkt, Geschwindigkeit Ost/Nord/Vertikal [m/s]
    - Parameter: FSL-Geschwindigkeit, Timeout, Akku-Minimum
    - Buttons: Trigger senden, Abbrechen (RTL), Modell auf FSL umstellen
    - Status, Plan, 2D-Plot und Höhen-Plot
    """

    TRIGGER_FIELDS = [
        ("drone_id", "ID", "T1"),
        ("east", "Ost [m]", "-150"),
        ("north", "Nord [m]", "100"),
        ("up", "Höhe [m]", "20"),
        ("v_east", "v Ost [m/s]", "5"),
        ("v_north", "v Nord [m/s]", "0"),
        ("v_up", "v Höhe [m/s]", "0"),
    ]
    CONFIG_FIELDS = [
        ("speed", "FSL-Geschw. [m/s]", "8"),
        ("timeout", "Timeout [s]", "180"),
        ("battery_min", "Akku min [%]", "30"),
    ]

    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.vars = {}

        left = ttk.Frame(self, padding=6)
        left.pack(side=tk.LEFT, fill=tk.Y)

        trig = ttk.LabelFrame(left, text="Trigger (simuliert)", padding=6)
        trig.pack(fill=tk.X)
        self._fields(trig, self.TRIGGER_FIELDS)

        cfg = ttk.LabelFrame(left, text="Parameter", padding=6)
        cfg.pack(fill=tk.X, pady=6)
        self._fields(cfg, self.CONFIG_FIELDS)

        buttons = ttk.Frame(left)
        buttons.pack(fill=tk.X, pady=4)
        self.btn_trigger = ttk.Button(buttons, text="Trigger senden", command=self._send)
        self.btn_trigger.pack(fill=tk.X)
        self.btn_abort = ttk.Button(buttons, text="Abbrechen (RTL)", state="disabled",
                                    command=lambda: self.controller.abort_intercept())
        self.btn_abort.pack(fill=tk.X, pady=2)
        self.btn_model = ttk.Button(buttons, text="Modell auf FSL umstellen",
                                    command=lambda: self.controller.switch_to_fsl_model())

        info = ttk.LabelFrame(left, text="Status", padding=6)
        info.pack(fill=tk.X, pady=6)
        self.lbl_state = ttk.Label(info, text="Zustand: -")
        self.lbl_state.pack(anchor="w")
        self.lbl_status = ttk.Label(info, text="-", wraplength=260, justify="left")
        self.lbl_status.pack(anchor="w", pady=2)
        self.lbl_plan = ttk.Label(info, text="Plan: -", wraplength=260, justify="left")
        self.lbl_plan.pack(anchor="w", pady=2)
        self.lbl_flight = ttk.Label(info, text="Akku: -   Flugzeit: -")
        self.lbl_flight.pack(anchor="w")

        right = ttk.Frame(self)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.alt_plot = AltitudePlot(right)
        self.alt_plot.pack(side=tk.BOTTOM, fill=tk.X)
        self.plot = Plot2D(right)
        self.plot.pack(fill=tk.BOTH, expand=True)

    def _fields(self, parent, fields):
        for row, (key, label, default) in enumerate(fields):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 6), pady=1)
            var = tk.StringVar(value=default)
            ttk.Entry(parent, textvariable=var, width=10).grid(row=row, column=1, sticky="ew", pady=1)
            self.vars[key] = var

    # ------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------
    def values(self):
        return {key: var.get().strip() for key, var in self.vars.items()}

    def _send(self):
        if self.controller:
            self.controller.send_trigger(self.values())

    def set_enabled(self, trigger: bool, abort: bool, model_hint: bool):
        self.btn_trigger["state"] = "normal" if trigger else "disabled"
        self.btn_abort["state"] = "normal" if abort else "disabled"
        # winfo_manager statt winfo_ismapped: gilt auch, wenn der Tab gerade nicht sichtbar ist
        packed = self.btn_model.winfo_manager() == "pack"
        if model_hint and not packed:
            self.btn_model.pack(fill=tk.X, pady=2)
        elif not model_hint and packed:
            self.btn_model.pack_forget()

    def show_status(self, state, status, plan, flight):
        self.lbl_state["text"] = f"Zustand: {state}"
        self.lbl_status["text"] = status
        self.lbl_plan["text"] = plan
        self.lbl_flight["text"] = flight
