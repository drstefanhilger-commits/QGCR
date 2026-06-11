# === PFAD-B FULL FILE: QGCR/model/scenario_config.py ===

class ScenarioConfig:
    """
    Szenario-Konfiguration für SETUP → STARTUP → READY → AIRBORNE.
    Wird vom Setup-Tab beschrieben und vom StartupHFSM gelesen.

    Unterstützt:
    - Bis zu 10 UAVs
    - UAV-Typ (gz_rc_cessna, gz_500, gz_standard_vtol, ...)
    - Startposition (x, y, z)
    - Start-Yaw
    - Missionsdatei
    - Anzahl Wiederholungen
    - Automatisches Überspringen von SETUP bei Wiederholungen
    """

    def __init__(self):
        # Liste von UAV-Einträgen
        # Jeder Eintrag ist ein dict:
        # {
        #   "uav_type": str,
        #   "px4_dir": str,
        #   "start_pos": [x, y, z],
        #   "start_yaw": float,
        #   "mission_file": str
        # }
        self.uavs = []

        # Anzahl der Wiederholungen
        self.repetitions = 1

        # Aktuelle Wiederholung (0-basiert)
        self.current_repeat = 0

        # Wenn True → SETUP wird übersprungen
        self.skip_setup = False

    # ------------------------------------------------------------
    # UAV hinzufügen
    # ------------------------------------------------------------
    def add_uav(self, uav_type, px4_dir, start_pos, start_yaw, mission_file):
        entry = {
            "uav_type": uav_type,
            "px4_dir": px4_dir,
            "start_pos": list(start_pos),
            "start_yaw": float(start_yaw),
            "mission_file": mission_file
        }
        self.uavs.append(entry)

    # ------------------------------------------------------------
    # Szenario zurücksetzen
    # ------------------------------------------------------------
    def reset(self):
        self.uavs.clear()
        self.repetitions = 1
        self.current_repeat = 0
        self.skip_setup = False

    # ------------------------------------------------------------
    # Wiederholungslogik
    # ------------------------------------------------------------
    def next_repeat(self):
        """
        Erhöht current_repeat und entscheidet,
        ob SETUP übersprungen werden soll.
        """
        if self.repetitions <= 1:
            self.current_repeat = 0
            self.skip_setup = False
            return False  # keine Wiederholung

        self.current_repeat += 1

        if self.current_repeat < self.repetitions:
            # weitere Wiederholungen → SETUP überspringen
            self.skip_setup = True
            return True
        else:
            # letzte Wiederholung abgeschlossen
            self.current_repeat = 0
            self.skip_setup = False
            return False

    # ------------------------------------------------------------
    # Debug-Ausgabe
    # ------------------------------------------------------------
    def __repr__(self):
        return (
            f"ScenarioConfig(uavs={len(self.uavs)}, "
            f"repetitions={self.repetitions}, "
            f"current_repeat={self.current_repeat}, "
            f"skip_setup={self.skip_setup})"
        )
