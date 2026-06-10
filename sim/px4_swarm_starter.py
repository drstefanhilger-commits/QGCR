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
        self.instances = instances
        self.processes = {}
        self.model = model
        self.running = False   # <--- NEU: Idempotenz-Flag

    # ------------------------------------------------------------
    # START
    # ------------------------------------------------------------
    def start_all(self):

        # Idempotenz: Wenn bereits gestartet → ignorieren
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

            if self.model and hasattr(self.model, "log"):
                threading.Thread(
                    target=self._stream_output,
                    args=(cfg.instance_id, proc),
                    daemon=True
                ).start()

    # ------------------------------------------------------------
    # LOG STREAM
    # ------------------------------------------------------------
    def _stream_output(self, instance_id, proc):
        if proc.stdout:
            for line in proc.stdout:
                text = line.decode(errors="ignore").rstrip()
                self.model.log.px4(instance_id, text)

        if proc.stderr:
            for line in proc.stderr:
                text = line.decode(errors="ignore").rstrip()
                self.model.log.px4(instance_id, text)

    # ------------------------------------------------------------
    # STOP
    # ------------------------------------------------------------
    def stop_all(self):

        # Idempotenz: Wenn bereits gestoppt → ignorieren
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

        # --- NEU: Gazebo-Prozesse explizit beenden ---
        gazebo_names = ["gzserver", "gzclient", "gz", "ign", "ign-gazebo"]

        for name in gazebo_names:
            try:
                subprocess.run(["pkill", "-9", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"[PX4SwarmStarter] killed leftover Gazebo process: {name}")
            except Exception:
                pass


        self.processes.clear()
