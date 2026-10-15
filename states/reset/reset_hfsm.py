# === PFAD-B FULL FILE: QGCR/states/reset/reset_hfsm.py ===

import os
import shutil
from datetime import datetime

from QGCR.states.main_state import MainState
from QGCR.states.base_hfsm import BaseHFSM


class ResetHFSM(BaseHFSM):

    def __init__(self, model):
        super().__init__(model, MainState.RESET)
        self._next_state = MainState.STARTUP

    def _on_enter(self):
        self.model.log.qgcr("[ResetHFSM] entering RESET")
        self.model.hfsm_main = "RESET"
        self.model.hfsm_sub = "CLEANUP"
        self.model.push_state_update()

        # Wenn bereits ein Reset läuft, nichts mehr tun
        if getattr(self.model, "reset_in_progress", False):
            self.model.log.qgcr("[ResetHFSM] reset_in_progress=True → skip duplicate RESET")
            self._next_state = MainState.STARTUP
            return

        self.model.reset_in_progress = True

        # ------------------------------------------------------------
        # 0) HFSM-Eventqueue leeren
        # ------------------------------------------------------------
        try:
            self.model.hfsm_events.clear()
            self.model.log.qgcr("[ResetHFSM] cleared hfsm_events on enter")
        except Exception:
            pass

        # ------------------------------------------------------------
        # 0b) Takeoff-MicroService zurücksetzen
        # ------------------------------------------------------------
        try:
            if hasattr(self.model, "takeoff"):
                if hasattr(self.model.takeoff, "reset"):
                    self.model.takeoff.reset()
                    self.model.log.qgcr("[ResetHFSM] TakeoffMS.reset() called")
                else:
                    # Fallback: State hart auf IDLE setzen
                    if hasattr(self.model.takeoff, "STATE_IDLE"):
                        self.model.takeoff.state = self.model.takeoff.STATE_IDLE
                        self.model.log.qgcr("[ResetHFSM] TakeoffMS.state → STATE_IDLE")
        except Exception as e:
            self.model.log.qgcr(f"[ResetHFSM] TakeoffMS reset failed: {e}")

        # ------------------------------------------------------------
        # 1) Logging
        # ------------------------------------------------------------
        try:
            px4_pids = getattr(self.model, "px4_pids", None)
            px4_pid = getattr(self.model, "px4_pid", None)
            model_name = getattr(self.model, "model_name", None)
            self.model.log.qgcr(
                f"[ResetHFSM] px4_pid={px4_pid}, px4_pids={px4_pids}, model_name={model_name}"
            )
        except Exception as e:
            self.model.log.qgcr(f"[ResetHFSM] PID logging failed: {e}")

        # ------------------------------------------------------------
        # 2) Backup
        # ------------------------------------------------------------
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = getattr(self.model, "base_path", os.getcwd())
            target = os.path.join(base, "reset_backup", ts)
            os.makedirs(target, exist_ok=True)

            if hasattr(self.model, "ugl_path") and os.path.isdir(self.model.ugl_path):
                shutil.copytree(self.model.ugl_path, os.path.join(target, "ugl"))

            if hasattr(self.model, "log_path") and os.path.isdir(self.model.log_path):
                shutil.copytree(self.model.log_path, os.path.join(target, "logs"))

            self.model.log.qgcr(f"[ResetHFSM] Backup saved → {target}")
        except Exception as e:
            self.model.log.qgcr(f"[ResetHFSM] Backup failed: {e}")

        # ------------------------------------------------------------
        # 3) PX4-SITL stoppen
        # ------------------------------------------------------------
        try:
            starter = getattr(self.model, "startup_controller", None)
            if starter and hasattr(starter, "stop_all"):
                starter.stop_all()
                self.model.log.qgcr("[ResetHFSM] startup_controller.stop_all() called")
            else:
                px4_pids = getattr(self.model, "px4_pids", {}) or {}
                px4_pid = getattr(self.model, "px4_pid", None)
                if px4_pid:
                    px4_pids.setdefault(-1, px4_pid)

                if px4_pids:
                    import signal
                    for inst_id, pid in list(px4_pids.items()):
                        try:
                            os.kill(pid, signal.SIGTERM)
                            self.model.log.qgcr(f"[ResetHFSM] SIGTERM sent to PX4[{inst_id}] (PID={pid})")
                        except Exception as e:
                            self.model.log.qgcr(f"[ResetHFSM] kill PX4[{inst_id}] failed: {e}")
                else:
                    self.model.log.qgcr("[ResetHFSM] No PX4 PIDs found to stop.")
        except Exception as e:
            self.model.log.qgcr(f"[ResetHFSM] PX4 stop error: {e}")

        # --- NEU: PX4 SITL Rootfs + Lockfiles löschen ---
        try:
            px4_root = os.path.join(self.model.base_path, "build", "px4_sitl_default", "tmp", "rootfs")
            if os.path.isdir(px4_root):
                shutil.rmtree(px4_root)
                self.model.log.qgcr("[ResetHFSM] PX4 rootfs deleted")

            # /tmp Lockfiles
            for f in os.listdir("/tmp"):
                if f.startswith("px4-") or f.startswith("gz-"):
                    try:
                        os.remove(os.path.join("/tmp", f))
                        self.model.log.qgcr(f"[ResetHFSM] removed /tmp/{f}")
                    except:
                        pass

        except Exception as e:
            self.model.log.qgcr(f"[ResetHFSM] PX4 cleanup failed: {e}")


        # ------------------------------------------------------------
        # 3b) Model-Felder zurücksetzen
        # ------------------------------------------------------------
        try:
            if hasattr(self.model, "startup_controller"):
                self.model.startup_controller = None
            # noch nicht verarbeitete Nachrichten des alten PX4 verwerfen,
            # sonst setzen alte Heartbeats den Status gleich wieder auf "verbunden"
            connection = getattr(self.model, "connection", None)
            if hasattr(connection, "clear_pending"):
                connection.clear_pending()
            if hasattr(self.model, "reset_heartbeat"):
                self.model.reset_heartbeat()
            self.model.mission_running = False
            if hasattr(self.model, "px4_pids"):
                self.model.px4_pids = {}
            if hasattr(self.model, "px4_pid"):
                self.model.px4_pid = None
            if hasattr(self.model, "model_name"):
                self.model.model_name = None
        except Exception as e:
            self.model.log.qgcr(f"[ResetHFSM] model cleanup failed: {e}")

        # ------------------------------------------------------------
        # 4) Reset-Flag setzen
        # ------------------------------------------------------------
        self.model.reset_done = True
        self.model.log.qgcr("[ResetHFSM] reset_done=True → will switch to STARTUP")

    def _on_during(self):
        self._next_state = MainState.STARTUP

    def _on_exit(self):
        self.model.reset_in_progress = False
        return self._next_state
