# === PFAD-B FULL FILE: QGCR/sim/gazebo_markers.py ===

import math
import os
import re
import subprocess
import threading
import time


class GazeboMarkers:
    """
    Zeigt Start- und Landepunkt in Gazebo Harmonic als statische, rein visuelle
    Modelle (keine Kollision): Scheibe + Mast, Start grün, Landung rot.

    - request(start, landing) mit (lat, lon) oder None; blockiert nicht.
      Ein Worker-Thread setzt nur den neuesten Wunsch um (gz-Aufrufe ~0,3 s).
    - invalidate(): Gazebo wurde neu gestartet (RESET/Modellwechsel) → neu platzieren.
    - Umrechnung lat/lon → Welt-ENU (x Ost, y Nord) um den Ursprung der Welt
      (<spherical_coordinates> der World-SDF).
    """

    NAMES = {"start": "qgcr_start", "landing": "qgcr_landing",
             "path": "qgcr_trigger_path", "wait": "qgcr_wait"}
    COLORS = {"start": "0 0.8 0 1", "landing": "0.9 0 0 1",
              "path": "0.6 0 0.8 1", "wait": "1 0.8 0 1"}
    DEFAULT_ORIGIN = (47.397971057728974, 8.546163739800146)   # PX4 Welt "default"
    EARTH_M_PER_DEG = 111_320.0
    RETRY_INTERVAL = 2.0
    TIMEOUT_MS = 3000

    def __init__(self, px4_dir=None, world="default", runner=None, log=None):
        self.world = world
        self.origin = self._read_origin(px4_dir, world)
        self._run = runner or self._run_gz
        self._log = log or (lambda text: None)

        self._placed = {}                 # name → (lat, lon) in Gazebo
        self._desired = {}
        self._failed_at = 0.0
        self._cond = threading.Condition()
        self._dirty = False
        self._stop = False
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------
    def request(self, start, landing, path=None, wait=None):
        """
        start/landing: (lat, lon) – Scheibe + Mast am Boden.
        path: ((lat, lon, alt), (lat, lon, alt)) – Flugbahn der Trigger-Drohne (Stab).
        wait: (lat, lon, alt) – Wartepunkt (Kugel in Höhe + Mast).
        """
        desired = {"start": start, "landing": landing,
                   "path": tuple(path) if path else None, "wait": wait}
        with self._cond:
            if desired == self._desired and not self._needs_retry():
                return
            self._desired = desired
            self._dirty = True
            self._cond.notify()

    def invalidate(self):
        """Neue Gazebo-Instanz: nichts ist mehr platziert."""
        with self._cond:
            if self._placed:
                self._placed = {}
                self._dirty = True
                self._cond.notify()

    def stop(self):
        with self._cond:
            self._stop = True
            self._cond.notify()
        if self._thread is not threading.current_thread():
            self._thread.join(timeout=5.0)

    # ------------------------------------------------------------
    # Umrechnung
    # ------------------------------------------------------------
    def to_enu(self, point):
        lat0, lon0 = self.origin
        lat, lon = point
        x = (lon - lon0) * self.EARTH_M_PER_DEG * math.cos(math.radians(lat0))
        y = (lat - lat0) * self.EARTH_M_PER_DEG
        return x, y

    @classmethod
    def _read_origin(cls, px4_dir, world):
        if px4_dir:
            path = os.path.join(os.path.expanduser(px4_dir), "Tools", "simulation", "gz", "worlds", f"{world}.sdf")
            try:
                with open(path) as f:
                    sdf = f.read()
                lat = float(re.search(r"<latitude_deg>\s*([-\d.]+)\s*<", sdf).group(1))
                lon = float(re.search(r"<longitude_deg>\s*([-\d.]+)\s*<", sdf).group(1))
                return lat, lon
            except (OSError, AttributeError, ValueError):
                pass
        return cls.DEFAULT_ORIGIN

    # ------------------------------------------------------------
    # Worker
    # ------------------------------------------------------------
    def _needs_retry(self):
        return any(self._desired.get(k) != self._placed.get(self.NAMES[k]) for k in self.NAMES) \
            and time.time() - self._failed_at >= self.RETRY_INTERVAL

    def _worker(self):
        while True:
            with self._cond:
                while not self._dirty and not self._stop:
                    self._cond.wait()
                if self._stop:
                    return
                self._dirty = False
                desired = dict(self._desired)

            ok = True
            for key, name in self.NAMES.items():
                want = desired.get(key)
                if self._placed.get(name) == want:
                    continue
                if name in self._placed:
                    self._remove(name)
                    self._placed.pop(name, None)
                if want is not None:
                    if self._create(name, key, want):
                        self._placed[name] = want
                    else:
                        ok = False

            if not ok:
                self._failed_at = time.time()

    # ------------------------------------------------------------
    # gz-Aufrufe
    # ------------------------------------------------------------
    def _sdf(self, name, key, point):
        color = self.COLORS[key]
        material = f"<material><ambient>{color}</ambient><diffuse>{color}</diffuse></material>"
        if key == "path":
            return self._sdf_path(name, point, material)
        if key == "wait":
            return self._sdf_wait(name, point, material)

        x, y = self.to_enu(point[:2])
        return (
            f"<sdf version='1.9'><model name='{name}'><static>true</static>"
            f"<pose>{x:.2f} {y:.2f} 0 0 0 0</pose><link name='link'>"
            f"<visual name='disc'><pose>0 0 0.03 0 0 0</pose><geometry><cylinder>"
            f"<radius>1.5</radius><length>0.05</length></cylinder></geometry>{material}</visual>"
            f"<visual name='pole'><pose>0 0 2 0 0 0</pose><geometry><cylinder>"
            f"<radius>0.08</radius><length>4</length></cylinder></geometry>{material}</visual>"
            f"</link></model></sdf>"
        )

    def _sdf_path(self, name, ends, material):
        """Stab von ends[0] nach ends[1] (je (lat, lon, alt)) in Flughöhe."""
        (x0, y0), (x1, y1) = self.to_enu(ends[0][:2]), self.to_enu(ends[1][:2])
        z0, z1 = ends[0][2], ends[1][2]
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        length = max(math.sqrt(dx * dx + dy * dy + dz * dz), 0.1)
        yaw = math.atan2(dy, dx)
        pitch = -math.atan2(dz, math.hypot(dx, dy))
        return (
            f"<sdf version='1.9'><model name='{name}'><static>true</static>"
            f"<pose>{(x0 + x1) / 2:.2f} {(y0 + y1) / 2:.2f} {(z0 + z1) / 2:.2f} 0 {pitch:.4f} {yaw:.4f}</pose>"
            f"<link name='link'><visual name='path'><geometry><box><size>{length:.2f} 0.3 0.3</size></box>"
            f"</geometry>{material}</visual></link></model></sdf>"
        )

    def _sdf_wait(self, name, point, material):
        """Kugel in Wartehöhe + dünner Mast zum Boden."""
        x, y = self.to_enu(point[:2])
        z = point[2]
        return (
            f"<sdf version='1.9'><model name='{name}'><static>true</static>"
            f"<pose>{x:.2f} {y:.2f} 0 0 0 0</pose><link name='link'>"
            f"<visual name='ball'><pose>0 0 {z:.2f} 0 0 0</pose><geometry><sphere><radius>1.2</radius>"
            f"</sphere></geometry>{material}</visual>"
            f"<visual name='pole'><pose>0 0 {z / 2:.2f} 0 0 0</pose><geometry><cylinder>"
            f"<radius>0.05</radius><length>{max(z, 0.1):.2f}</length></cylinder></geometry>{material}</visual>"
            f"</link></model></sdf>"
        )

    def _create(self, name, key, point):
        sdf = self._sdf(name, key, point).replace('"', '\\"')
        ok = self._run(["service", "-s", f"/world/{self.world}/create",
                        "--reqtype", "gz.msgs.EntityFactory", "--reptype", "gz.msgs.Boolean",
                        "--timeout", str(self.TIMEOUT_MS),
                        "--req", f'sdf: "{sdf}" name: "{name}" allow_renaming: false'])
        self._log(f"[GazeboMarkers] {name} {'gesetzt' if ok else 'nicht gesetzt'} bei {point}")
        return ok

    def _remove(self, name):
        return self._run(["service", "-s", f"/world/{self.world}/remove",
                          "--reqtype", "gz.msgs.Entity", "--reptype", "gz.msgs.Boolean",
                          "--timeout", str(self.TIMEOUT_MS),
                          "--req", f'name: "{name}" type: MODEL'])

    @staticmethod
    def _run_gz(args):
        env = dict(os.environ, GZ_IP="127.0.0.1")     # wie PX4 beim Start von gz sim
        try:
            result = subprocess.run(["gz", *args], env=env, capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0 and "data: true" in result.stdout
