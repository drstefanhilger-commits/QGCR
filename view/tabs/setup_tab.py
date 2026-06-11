# === PFAD-B FULL FILE: QGCR/view/tabs/setup_tab.py ===

import tkinter as tk
from tkinter import ttk, filedialog


class SetupTab(ttk.Frame):
    """
    Setup-Tab für UAV-Szenarien:
    - UAV #1 ist immer aktiv (editierbar, aber nicht deaktivierbar)
    - UAV #2–10 optional über Select-Button
    - Globaler PX4-Pfad für alle UAVs
    """

    UAV_TYPES = [
        "gz_rc_cessna",
        "gz_500",
        "gz_standard_vtol",
    ]

    def __init__(self, parent, model, controller):
        super().__init__(parent)

        self.model = model
        self.controller = controller

        self.uav_rows = []
        self.max_uavs = 10

        self._build_ui()

    # ------------------------------------------------------------
    # UI AUFBAU
    # ------------------------------------------------------------
    def _build_ui(self):

        title = ttk.Label(self, text="Scenario Setup", font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, columnspan=8, pady=10)

        # --------------------------------------------------------
        # GLOBALER PX4-PFAD
        # --------------------------------------------------------
        ttk.Label(self, text="PX4 Directory:", font=("Arial", 12)).grid(
            row=1, column=0, sticky="w", pady=5
        )

        self.global_px4_dir = tk.StringVar(value="/home/stefan/PX4_SITL/30Degrees")
        ttk.Entry(self, textvariable=self.global_px4_dir, width=40).grid(
            row=1, column=1, columnspan=4, sticky="w"
        )

        # --------------------------------------------------------
        # Tabellen-Header
        # --------------------------------------------------------
        header = [
            "UAV-Typ",
            "X",
            "Y",
            "Z",
            "Yaw",
            "Mission",
        ]

        for col, text in enumerate(header):
            ttk.Label(self, text=text, font=("Arial", 10, "bold")).grid(
                row=2, column=col, padx=5, pady=5
            )

        # --------------------------------------------------------
        # UAV-Zeilen
        # --------------------------------------------------------

        # UAV #1: immer aktiv, editierbar
        row = self._build_uav_row(3, fixed=True)
        self.uav_rows.append(row)

        # UAV #2–10: optional
        for i in range(1, self.max_uavs):
            row = self._build_uav_row(i + 3, fixed=False)
            self.uav_rows.append(row)

        # --------------------------------------------------------
        # Wiederholungen
        # --------------------------------------------------------
        ttk.Label(self, text="Wiederholungen:", font=("Arial", 12)).grid(
            row=20, column=0, sticky="w", pady=10
        )

        self.repeat_var = tk.IntVar(value=1)
        repeat_entry = ttk.Entry(self, textvariable=self.repeat_var, width=5)
        repeat_entry.grid(row=20, column=1, sticky="w")

        # --------------------------------------------------------
        # AIM-Button
        # --------------------------------------------------------
        aim_btn = ttk.Button(self, text="AIM (Start Scenario)", command=self._on_aim)
        aim_btn.grid(row=21, column=0, columnspan=2, pady=20)

    # ------------------------------------------------------------
    # UAV-ZEILE
    # ------------------------------------------------------------
    def _build_uav_row(self, row_index, fixed=False):

        # Variablen
        uav_type_var = tk.StringVar(value=self.UAV_TYPES[0])
        x_var = tk.DoubleVar(value=0.0)
        y_var = tk.DoubleVar(value=0.0)
        z_var = tk.DoubleVar(value=0.0)
        yaw_var = tk.DoubleVar(value=0.0)
        mission_var = tk.StringVar(value="/home/stefan/PX4_SITL/missions/27/Zurich.plan")


        # Widgets erzeugen
        type_box = ttk.Combobox(self, values=self.UAV_TYPES, textvariable=uav_type_var, width=18)
        x_entry = ttk.Entry(self, textvariable=x_var, width=6)
        y_entry = ttk.Entry(self, textvariable=y_var, width=6)
        z_entry = ttk.Entry(self, textvariable=z_var, width=6)
        yaw_entry = ttk.Entry(self, textvariable=yaw_var, width=6)
        mission_entry = ttk.Entry(self, textvariable=mission_var, width=20)

        # Positionierung
        type_box.grid(row=row_index, column=0, padx=5, pady=3)
        x_entry.grid(row=row_index, column=1)
        y_entry.grid(row=row_index, column=2)
        z_entry.grid(row=row_index, column=3)
        yaw_entry.grid(row=row_index, column=4)
        mission_entry.grid(row=row_index, column=5, padx=5)

        # Mission Picker
        def pick_file():
            file = filedialog.askopenfilename(
                title="Mission File auswählen",
                filetypes=[("Mission Files", "*.plan"), ("Alle Dateien", "*.*")]
            )
            if file:
                mission_var.set(file)

        pick_btn = ttk.Button(self, text="...", width=3, command=pick_file)
        pick_btn.grid(row=row_index, column=6)

        # --------------------------------------------------------
        # UAV #1 (fixed but editable)
        # --------------------------------------------------------
        if fixed:
            return {
                "enabled": True,
                "fixed": True,
                "uav_type": uav_type_var,
                "x": x_var,
                "y": y_var,
                "z": z_var,
                "yaw": yaw_var,
                "mission": mission_var,
            }

        # --------------------------------------------------------
        # UAV #2–10 (optional)
        # --------------------------------------------------------
        widgets = [type_box, x_entry, y_entry, z_entry, yaw_entry, mission_entry, pick_btn]

        # Start disabled
        for w in widgets:
            w.configure(state="disabled")

        def enable_row():
            for w in widgets:
                w.configure(state="normal")
            row_dict["enabled"] = True

        select_btn = ttk.Button(self, text="Select", width=6, command=enable_row)
        select_btn.grid(row=row_index, column=7, padx=5)

        row_dict = {
            "enabled": False,
            "fixed": False,
            "uav_type": uav_type_var,
            "x": x_var,
            "y": y_var,
            "z": z_var,
            "yaw": yaw_var,
            "mission": mission_var,
        }

        return row_dict

    # ------------------------------------------------------------
    # AIM BUTTON
    # ------------------------------------------------------------
    def _on_aim(self):
        """
        Liest alle UAV-Daten ein und schreibt sie ins Model.scenario.
        Sendet danach HFSM-Event "AIM".
        """

        scenario = self.model.scenario
        scenario.reset()

        # Globaler PX4-Pfad
        px4_dir = self.global_px4_dir.get().strip()
        if px4_dir == "":
            print("[SetupTab] ERROR: Globaler PX4-Pfad fehlt!")
            return

        # Wiederholungen
        scenario.repetitions = max(1, int(self.repeat_var.get()))

        # UAVs einlesen
        for row in self.uav_rows:
            if not row["enabled"]:
                continue

            scenario.add_uav(
                uav_type=row["uav_type"].get(),
                px4_dir=px4_dir,
                start_pos=[row["x"].get(), row["y"].get(), row["z"].get()],
                start_yaw=row["yaw"].get(),
                mission_file=row["mission"].get().strip(),
            )

        print("[SetupTab] Scenario übernommen:", scenario)

        # HFSM-Event senden
        self.controller.push_event("AIM")
