# === PFAD-B FULL FILE: QGCR/sim/px4_swarm_starter.py ===

import subprocess
import os
import signal
import time
import threading


class PX4InstanceConfig:
    """
    Konfiguration für eine einzelne PX4-SITL-Instanz.
    """

    def __init__(self, px4_dir, model_name, instance_id, verbose=True):
        self.px4_dir = os.path.expanduser(px4_dir)
        self.model_name = model_name
        self.instance_id = instance_id
        self.verbose = verbose


class PX4SwarmStarter:
    """
    Startet mehrere PX4-SITL-Instanzen (Swarm-fähig).
    Idempotent: start_all() und stop_all() werden nur ausgeführt,
    wenn der Zustand es erlaubt.
    """

    def __init__(self, instances, model=None):
        self.instances = instances              # Liste von PX4InstanceConfig
        self.processes = {}                     # instance_id -> Popen
        self.stdout_threads = {}                # instance_id -> Thread
        self.stderr_threads = {}                # instance_id -> Thread
        self.model = model
        self.running = False                    # Idempotenz-Flag

    # ------------------------------------------------------------
    # START
    # ------------------------------------------------------------
    def start_all(self):
        """
        Startet alle konfigurierten PX4-Instanzen.
        Wird ignoriert, wenn bereits running == True.
        """

        if self.running:
            print("[PX4SwarmStarter] start_all() ignored – already running.")
            return

        self.running = True

        for cfg in self.instances:
            if cfg.instance_id in self.processes:
                if cfg.verbose:
                    print(f"[PX4SwarmStarter] Instance {cfg.instance_id} already running.")
                continue

            mavlink_port = 14550 + (cfg.instance_id - 1) * 10

            env = os.environ.copy()
            env["PX4_SIM_MODEL"] = cfg.model_name
            env["PX4_INSTANCE"] = str(cfg.instance_id)
            env["PX4_MAVLINK_UDP_PORT"] = str(mavlink_port)

            cmd = ["make", "px4_sitl", cfg.model_name]

            if cfg.verbose:
                print(
                    f"[PX4SwarmStarter] Starting PX4[{cfg.instance_id}] "
                    f"with target '{cfg.model_name}' on UDP {mavlink_port}"
                )

            proc = subprocess.Popen(
                cmd,
                cwd=cfg.px4_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,
                env=env
            )
            self.processes[cfg.instance_id] = proc

            # Model-Infos aktualisieren
            if self.model:
                if not hasattr(self.model, "px4_pids"):
                    self.model.px4_pids = {}
                self.model.px4_pids[cfg.instance_id] = proc.pid
                self.model.px4_pid = proc.pid

                if not hasattr(self.model, "swarm_model_names"):
                    self.model.swarm_model_names = {}
                self.model.swarm_model_names[cfg.instance_id] = cfg.model_name
                self.model.model_name = cfg.model_name

            time.sleep(1.0)

            if cfg.verbose:
                print(f"[PX4SwarmStarter] PX4[{cfg.instance_id}] started (PID={proc.pid}).")

            # Log-Streaming in separaten Threads
            if self.model and hasattr(self.model, "log"):
                t_out = threading.Thread(
                    target=self._stream_output,
                    args=(cfg.instance_id, proc.stdout, "STDOUT"),
                    daemon=True
                )
                t_err = threading.Thread(
                    target=self._stream_output,
                    args=(cfg.instance_id, proc.stderr, "STDERR"),
                    daemon=True
                )
                t_out.start()
                t_err.start()
                self.stdout_threads[cfg.instance_id] = t_out
                self.stderr_threads[cfg.instance_id] = t_err

    # ------------------------------------------------------------
    # LOG STREAM
    # ------------------------------------------------------------
    def _stream_output(self, instance_id, pipe, stream_name):
        """
        Liest kontinuierlich aus pipe und leitet die Zeilen ins Model-Log.
        """
        if pipe is None:
            return

        for line in pipe:
            try:
                text = line.decode(errors="ignore").rstrip()
            except AttributeError:
                # falls bereits str
                text = line.rstrip()

            if self.model and hasattr(self.model, "log"):
                # Du kannst hier differenzieren nach STDOUT/STDERR, falls gewünscht
                self.model.log.px4(instance_id, f"[{stream_name}] {text}")

    # ------------------------------------------------------------
    # STOP (HFSM-gesteuert, normaler Stop)
    # ------------------------------------------------------------
    def stop_all(self):
        """
        Normaler Stop, HFSM-gesteuert.
        Idempotent: wird ignoriert, wenn bereits gestoppt.
        """

        if not self.running:
            print("[PX4SwarmStarter] stop_all() ignored – already stopped.")
            return

        self.running = False

        for instance_id, proc in list(self.processes.items()):
            try:
                pgid = os.getpgid(proc.pid)
            except Exception:
                pgid = None

            # 1) SIGTERM an Prozessgruppe
            if pgid is not None:
                try:
                    os.killpg(pgid, signal.SIGTERM)
                except Exception:
                    pass

            # 2) kurz warten
            try:
                proc.wait(timeout=5.0)
            except Exception:
                # 3) falls noch lebendig: SIGKILL
                if pgid is not None:
                    try:
                        os.killpg(pgid, signal.SIGKILL)
                    except Exception:
                        pass

            print(f"[PX4SwarmStarter] PX4[{instance_id}] stopped.")

            if hasattr(self.model, "px4_pids"):
                self.model.px4_pids.pop(instance_id, None)
            if hasattr(self.model, "swarm_model_names"):
                self.model.swarm_model_names.pop(instance_id, None)

        if hasattr(self.model, "px4_pid"):
            self.model.px4_pid = None
        if hasattr(self.model, "model_name"):
            self.model.model_name = None

        # Gazebo-Prozesse explizit beenden
        gazebo_names = ["gzserver", "gzclient", "gz", "ign", "ign-gazebo"]
        for name in gazebo_names:
            try:
                subprocess.run(
                    ["pkill", "-9", name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print(f"[PX4SwarmStarter] killed leftover Gazebo process: {name}")
            except Exception:
                pass

        self.processes.clear()

    # ------------------------------------------------------------
    # CLEANUP (für App-Shutdown / Terminal-Freigabe)
    # ------------------------------------------------------------
    def cleanup(self):
        """
        Sauberes Beenden aller PX4-Prozesse, Threads und Pipes.
        Wird typischerweise beim Beenden der Applikation aufgerufen.
        """

        # 1) Prozesse terminieren
        for instance_id, proc in list(self.processes.items()):
            try:
                pgid = os.getpgid(proc.pid)
            except Exception:
                pgid = None

            if pgid is not None:
                try:
                    os.killpg(pgid, signal.SIGTERM)
                except Exception:
                    pass

            try:
                proc.wait(timeout=3.0)
            except Exception:
                if pgid is not None:
                    try:
                        os.killpg(pgid, signal.SIGKILL)
                    except Exception:
                        pass

            # Pipes schließen
            try:
                if proc.stdout:
                    proc.stdout.close()
                if proc.stderr:
                    proc.stderr.close()
            except Exception:
                pass

            print(f"[PX4SwarmStarter] cleanup: PX4[{instance_id}] terminated.")

        # 2) Threads joinen
        for instance_id, t in list(self.stdout_threads.items()):
            try:
                t.join(timeout=1.0)
            except Exception:
                pass

        for instance_id, t in list(self.stderr_threads.items()):
            try:
                t.join(timeout=1.0)
            except Exception:
                pass

        # 3) Gazebo-Reste killen
        gazebo_names = ["gzserver", "gzclient", "gz", "ign", "ign-gazebo"]
        for name in gazebo_names:
            try:
                subprocess.run(
                    ["pkill", "-9", name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass

        # 4) interne Strukturen leeren
        self.processes.clear()
        self.stdout_threads.clear()
        self.stderr_threads.clear()

        self.running = False

        print("[PX4SwarmStarter] cleanup complete.")
