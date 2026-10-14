#!/usr/bin/env python3
import os
import subprocess
import signal
from dataclasses import dataclass, field
from typing import List, Dict


# -------------------------------------------------------------------------
# VehicleConfig: beschreibt EIN Fahrzeug im Swarm
# -------------------------------------------------------------------------
@dataclass
class VehicleConfig:
    name: str                     # Logischer Name: "fw_1", "mc_1", "vtol_1"
    model: str                    # PX4_SIM_MODEL: rc_cessna, x500, standard_vtol
    workdir: str                  # PX4-SITL Root
    sim_backend: str = "gz"       # "gz" oder später "matlab"
    instance_index: int = 0       # 0,1,2,... für Swarm
    sim_port_offset: int = 0      # Port-Offset für MAVLink
    extra_env: Dict[str, str] = field(default_factory=dict)


# -------------------------------------------------------------------------
# VehicleProcess: hält den laufenden Prozess
# -------------------------------------------------------------------------
@dataclass
class VehicleProcess:
    config: VehicleConfig
    process: subprocess.Popen


# -------------------------------------------------------------------------
# StartupController: Startet / Stoppt alle PX4-Instanzen
# -------------------------------------------------------------------------
class StartupController:
    def __init__(self, vehicles: List[VehicleConfig]) -> None:
        self.vehicles_cfg = vehicles
        self.vehicles_proc: List[VehicleProcess] = []

    # ---------------------------------------------------------------------
    # Öffentliche API
    # ---------------------------------------------------------------------
    def start_all(self) -> None:
        if self.vehicles_proc:
            raise RuntimeError("PX4 läuft bereits – zuerst stop_all() aufrufen.")

        for cfg in self.vehicles_cfg:
            vp = self._start_single(cfg)
            self.vehicles_proc.append(vp)

    def stop_all(self, kill: bool = True) -> None:
        for vp in self.vehicles_proc:
            self._stop_single(vp, kill=kill)
        self.vehicles_proc.clear()

    def is_running(self) -> bool:
        return any(vp.process.poll() is None for vp in self.vehicles_proc)

    # ---------------------------------------------------------------------
    # Interne Helfer
    # ---------------------------------------------------------------------
    def _start_single(self, cfg: VehicleConfig) -> VehicleProcess:
        env = os.environ.copy()

        # PX4/Gazebo Modell-Umgebungsvariablen
        env["PX4_SIM_MODEL"] = cfg.model
        env["PX4_GZ_MODEL"] = cfg.model
        env["PX4_GZ_MODEL_NAME"] = f"{cfg.model}_{cfg.instance_index}"
        env["PX4_SIM_PORT_OFFSET"] = str(cfg.sim_port_offset)

        # Benutzerdefinierte Variablen
        for k, v in cfg.extra_env.items():
            env[k] = v

        # Backend auswählen
        if cfg.sim_backend == "gz":
            cmd = ["make", "px4_sitl", f"gz_{cfg.model}"]
        else:
            raise ValueError(f"Unbekannter sim_backend: {cfg.sim_backend}")

        # Prozess starten
        proc = subprocess.Popen(
            cmd,
            cwd=cfg.workdir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid
        )

        return VehicleProcess(config=cfg, process=proc)

    def _stop_single(self, vp: VehicleProcess, kill: bool = True) -> None:
        if vp.process.poll() is not None:
            return

        try:
            pgid = os.getpgid(vp.process.pid)
            os.killpg(pgid, signal.SIGKILL if kill else signal.SIGTERM)
        except ProcessLookupError:
            pass

        try:
            vp.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(vp.process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass


# -------------------------------------------------------------------------
# Beispiel: 1x Fixed Wing + 1x Multicopter + 1x VTOL
# -------------------------------------------------------------------------
if __name__ == "__main__":
    px4_dir = os.path.expanduser(os.environ.get("PX4_DIR", "~/PX4-Autopilot"))

    vehicles = [
        VehicleConfig(
            name="fw_1",
            model="rc_cessna",
            workdir=px4_dir,
            sim_backend="gz",
            instance_index=0,
            sim_port_offset=0,
        ),
        VehicleConfig(
            name="mc_1",
            model="x500",
            workdir=px4_dir,
            sim_backend="gz",
            instance_index=1,
            sim_port_offset=10,
        ),
        VehicleConfig(
            name="vtol_1",
            model="standard_vtol",
            workdir=px4_dir,
            sim_backend="gz",
            instance_index=2,
            sim_port_offset=20,
        ),
    ]

    startup = StartupController(vehicles)
    startup.start_all()

    print("PX4-SITL Swarm gestartet. Enter zum Stoppen…")
    input()

    startup.stop_all(kill=True)
    print("Swarm gestoppt.")
