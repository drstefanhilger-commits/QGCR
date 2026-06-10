# === PFAD-B FULL FILE: QGCR/microservices/reset_microservice.py ===

import time
from QGCR.model.mavlink_commands import (
    cmd_set_mode_loiter,
    cmd_set_mode_manual,
    cmd_disarm
)


class ResetMicroService:
    """
    ResetMicroService für Fixed-Wing:
    Führt einen sicheren Reset durch:
    1) AUTO → LOITER (Mission stoppen)
    2) LOITER → MANUAL (erlaubt DISARM)
    3) DISARM (Motor aus)
    4) done=True setzen

    Wird von AirborneResetFSM gestartet und tickt im Model-Update-Loop.
    """

    def __init__(self, model):
        self.model = model
        self.done = False
        self.error = None
        self._started = False
        self._step = 0
        self._last_send = 0.0

    # ------------------------------------------------------------
    # START
    # ------------------------------------------------------------
    def start(self):
        """
        Startet den Reset-Vorgang.
        """
        self._started = True
        self.done = False
        self.error = None
        self._step = 0
        self._last_send = 0.0

        try:
            self.model.log.qgcr("[ResetMS] START")
        except Exception:
            pass

    # ------------------------------------------------------------
    # TICK
    # ------------------------------------------------------------
    def tick(self):
        """
        Wird in jedem Model-Update aufgerufen.
        Führt die Reset-Schritte sequenziell aus.
        """

        if not self._started or self.done or self.error:
            return

        now = time.time()

        # --------------------------------------------------------
        # Schritt 1: AUTO → LOITER
        # --------------------------------------------------------
        if self._step == 0:
            if now - self._last_send > 0.5:
                try:
                    msg = cmd_set_mode_loiter(self.model.sysid, self.model.compid)
                    self.model.connection.master.mav.send(msg)
                    self.model.log.qgcr("[ResetMS] → LOITER gesendet")
                except Exception as e:
                    self.error = f"LOITER fehlgeschlagen: {e}"
                    return
                self._last_send = now
                self._step = 1
            return

        # --------------------------------------------------------
        # Schritt 2: LOITER → MANUAL
        # --------------------------------------------------------
        if self._step == 1:
            if now - self._last_send > 0.5:
                try:
                    msg = cmd_set_mode_manual(self.model.sysid, self.model.compid)
                    self.model.connection.master.mav.send(msg)
                    self.model.log.qgcr("[ResetMS] → MANUAL gesendet")
                except Exception as e:
                    self.error = f"MANUAL fehlgeschlagen: {e}"
                    return
                self._last_send = now
                self._step = 2
            return

        # --------------------------------------------------------
        # Schritt 3: DISARM
        # --------------------------------------------------------
        if self._step == 2:
            if now - self._last_send > 0.5:
                try:
                    msg = cmd_disarm(self.model.sysid, self.model.compid)
                    self.model.connection.master.mav.send(msg)  
                    self.model.log.qgcr("[ResetMS] → DISARM gesendet")
                except Exception as e:
                    self.error = f"DISARM fehlgeschlagen: {e}"
                    return
                self._last_send = now
                self._step = 3
            return

        # --------------------------------------------------------
        # Schritt 4: DONE
        # --------------------------------------------------------
        if self._step == 3:
            self.done = True
            try:
                self.model.log.qgcr("[ResetMS] DONE")
            except Exception:
                pass
            return
