# === PFAD-B FULL FILE: QGCR/model/intercept.py ===
"""
Abfang-Berechnung für die kontrollierte FSL-Drohne.

Koordinaten: lokal ENU in Metern relativ zum Startpunkt der FSL
(Ost, Nord, Höhe über Start). Umrechnung nach lat/lon erst für PX4.

Ablauf:
1. Aufstieg auf 10 m, dann auf kürzestem Weg zum Lot-Fußpunkt der FSL auf der
   (geraden) Bahn der Trigger-Drohne = Wartepunkt.
2. Am Wartepunkt laufend (dynamisch) entscheiden:
   - Trigger hat den Punkt noch nicht erreicht → der Trigger-Drohne ENTGEGEN fliegen
   - Trigger hat ihn überschritten              → der Trigger-Drohne NACHFLIEGEN
   und berechnen, wann und wo beide Positionen gleich sind (Treffpunkt).
3. Reicht die Zeit (Treffzeit + Rückflug ≤ Rest-Timeout) nicht oder ist die FSL
   im Nachflug zu langsam → zurück und landen. Am Treffpunkt → zurück und landen.

Zeitmodell der FSL (Multicopter, SITL-Messung gz_fsl_rocket_vtol):
3 s Vorbereitung + 16 s bis Horizontalflug + Strecke / (8 m/s × 0,92) + 4 s Abbremsen.
"""

import math
from dataclasses import dataclass, field

from pymavlink import mavutil


EARTH_M_PER_DEG = 111_320.0

HEAD_ON = "entgegen"
CHASE = "nachfliegen"


@dataclass
class Trigger:
    """Fremde Drohne (Trigger): Position/Geschwindigkeit relativ zum FSL-Startpunkt."""
    drone_id: str
    timestamp: float            # Zeitpunkt der Messung (time.time())
    east: float
    north: float
    up: float
    v_east: float
    v_north: float
    v_up: float = 0.0

    def position_at(self, t):
        """(e, n, u) zur Zeit t – Geschwindigkeit kurzfristig konstant."""
        dt = t - self.timestamp
        return (self.east + self.v_east * dt,
                self.north + self.v_north * dt,
                self.up + self.v_up * dt)

    @property
    def ground_speed(self):
        return math.hypot(self.v_east, self.v_north)

    def direction(self):
        """Einheitsvektor (Ost, Nord) der Flugrichtung."""
        v = self.ground_speed
        return self.v_east / v, self.v_north / v

    def line_point(self, s, min_alt=0.0):
        """Punkt der Bahn im Abstand s (entlang der Flugrichtung) von der Messposition."""
        de, dn = self.direction()
        climb = self.v_up / self.ground_speed
        return (self.east + de * s, self.north + dn * s, max(min_alt, self.up + climb * s))

    def along(self, point):
        """Lage eines Punkts entlang der Bahn (Projektion), bezogen auf die Messposition."""
        de, dn = self.direction()
        return (point[0] - self.east) * de + (point[1] - self.north) * dn


@dataclass
class InterceptConfig:
    climb_alt: float = 10.0         # Aufstieg auf 10 m über Grund
    speed: float = 8.0              # Soll-Geschwindigkeit FSL (DO_CHANGE_SPEED / DO_REPOSITION) [m/s]
    speed_efficiency: float = 0.92  # erreichte / gesetzte Geschwindigkeit (SITL ≈ 7,5/8)
    prep_time: float = 3.0          # Trigger → Missionsstart (Planung, Upload, Startbefehl) [s]
    start_delay: float = 16.0       # Missionsstart → Beginn Horizontalflug [s]
    approach_time: float = 4.0      # Abbremsen am Ziel [s]
    climb_rate: float = 2.0         # vertikale Geschwindigkeit für Höhenänderung [m/s]
    land_rate: float = 1.35         # mittlere Sinkrate bei der Landung [m/s] (SITL: 60 m in ≈ 45 s)
    rtl_alt: float = 60.0           # PX4 RTL_RETURN_ALT: RTL steigt erst auf diese Höhe [m]
    return_margin: float = 10.0     # Reserve für den Rückflug [s]
    min_alt: float = 10.0           # Flughöhe nie unter 10 m
    wait_acceptance: float = 1.0    # Annahmeradius Wartepunkt [m] (PX4-Default NAV_ACC_RAD = 10 m)
    meet_radius: float = 5.0        # "Positionen gleich": Abstand Trigger–FSL ≤ 5 m
    timeout: float = 180.0          # Überwachung: max. Flugzeit ab Start [s]
    battery_min: float = 30.0       # Überwachung: min. Akku [%]

    @property
    def ground_speed(self):
        return self.speed * self.speed_efficiency


@dataclass
class InterceptPlan:
    reachable: bool
    reason: str = ""
    trigger_now: tuple = None       # (e, n, u) bei Planung
    wait: tuple = None              # Wartepunkt = Lot-Fußpunkt (e, n, u)
    along: float = 0.0              # Abstand Trigger → Wartepunkt entlang der Bahn [m] (< 0: schon vorbei)
    t_fsl: float = 0.0              # Ankunft FSL am Wartepunkt ab Planung [s]
    t_trigger: float = 0.0          # Trigger am Wartepunkt ab Planung [s] (< 0: schon vorbei)
    mode: str = ""                  # erwartete Entscheidung am Wartepunkt (entgegen / nachfliegen)
    t_meet: float = 0.0             # erwartete Treffzeit ab Ankunft am Wartepunkt [s]
    meet: tuple = None              # erwarteter Treffpunkt (e, n, u)
    total: float = 0.0              # erwartete Flugzeit ab Missionsstart bis zur Landung [s]
    heading_deg: float = 0.0        # Flugrichtung des Triggers (0 = Nord, 90 = Ost)
    path: list = field(default_factory=list)   # Bahn des Triggers zur Anzeige [(e, n, u), ...]


@dataclass
class Pursuit:
    """Laufende Entscheidung am / nach dem Wartepunkt."""
    mode: str                       # entgegen / nachfliegen
    gap: float                      # Abstand Trigger–FSL entlang der Bahn [m]
    t_meet: float = None            # Treffzeit ab jetzt [s]; None = kein Treffen möglich
    meet: tuple = None              # Treffpunkt (e, n, u)


# ------------------------------------------------------------
# Zeiten
# ------------------------------------------------------------
def fsl_time_to(point, cfg):
    """Zeit vom Trigger (Planung), bis die FSL vom Start aus am Punkt (e, n, u) ist [s]."""
    e, n, u = point
    horizontal = math.hypot(e, n) / cfg.ground_speed
    vertical = abs(u - cfg.climb_alt) / cfg.climb_rate
    return cfg.prep_time + cfg.start_delay + max(horizontal, vertical) + cfg.approach_time


def return_time(point, cfg):
    """
    RTL vom Punkt (e, n, u) zum Start inkl. Landung und Reserve [s]:
    Steigen auf RTL_RETURN_ALT, Rückflug, Abbremsen, Sinken bis zum Boden.
    """
    alt = max(point[2], 0.0)
    climb = max(cfg.rtl_alt - alt, 0.0) / cfg.climb_rate
    return (climb + math.hypot(point[0], point[1]) / cfg.ground_speed
            + max(alt, cfg.rtl_alt) / cfg.land_rate + cfg.approach_time + cfg.return_margin)


# ------------------------------------------------------------
# Entscheidung + Treffpunkt
# ------------------------------------------------------------
def pursuit(trigger, fsl_pos, now, cfg):
    """
    Entgegen oder nachfliegen und wann/wo sich FSL und Trigger treffen.
    fsl_pos: (e, n, u) der FSL (auf bzw. nahe der Trigger-Bahn).
    """
    v_t, v_f = trigger.ground_speed, cfg.ground_speed
    s_trigger = v_t * (now - trigger.timestamp)            # Trigger jetzt, entlang der Bahn
    s_fsl = trigger.along(fsl_pos)
    gap = s_fsl - s_trigger                                 # > 0: Trigger noch vor der FSL

    if gap >= 0:
        t = gap / (v_t + v_f)
        mode = HEAD_ON
    else:
        mode = CHASE
        if v_f <= v_t:
            return Pursuit(mode, -gap, None, None)
        t = -gap / (v_f - v_t)

    s_meet = s_trigger + v_t * t
    return Pursuit(mode, abs(gap), t, trigger.line_point(s_meet, cfg.min_alt))


# ------------------------------------------------------------
# Planung beim Trigger
# ------------------------------------------------------------
def plan_intercept(trigger, now, cfg):
    """
    Wartepunkt = Lot-Fußpunkt vom FSL-Start auf die Trigger-Bahn.
    Vorhersage der Entscheidung dort und Prüfung des Zeitbudgets.
    """
    if trigger.ground_speed < 0.1:
        return InterceptPlan(False, "Trigger bewegt sich nicht (keine Flugrichtung)")

    de, dn = trigger.direction()
    heading = (math.degrees(math.atan2(de, dn)) + 360.0) % 360.0
    v_t = trigger.ground_speed
    s_now = v_t * (now - trigger.timestamp)
    trigger_now = trigger.position_at(now)

    # Lot vom Start (0, 0) auf die Gerade
    s_foot = trigger.along((0.0, 0.0, 0.0))
    wait = trigger.line_point(s_foot, cfg.min_alt)
    t_fsl = fsl_time_to(wait, cfg)

    # Entscheidung bei Ankunft am Wartepunkt
    p = pursuit(trigger, wait, now + t_fsl, cfg)

    s_meet = trigger.along(p.meet) if p.meet else s_foot
    lo = min(s_now, s_foot, s_meet) - 30.0
    hi = max(s_now, s_foot, s_meet) + 60.0
    plan = InterceptPlan(
        False, "",
        trigger_now=trigger_now, wait=wait, along=s_foot - s_now,
        t_fsl=t_fsl, t_trigger=(s_foot - s_now) / v_t,
        mode=p.mode, heading_deg=heading,
        path=[trigger.line_point(max(lo, s_now), cfg.min_alt), trigger.line_point(hi, cfg.min_alt)],
    )

    if p.t_meet is None:
        plan.reason = "Trigger schneller als FSL – Nachfliegen unmöglich"
        return plan

    plan.t_meet, plan.meet = p.t_meet, p.meet
    plan.total = t_fsl - cfg.prep_time + p.t_meet + return_time(p.meet, cfg)
    if plan.total > cfg.timeout:
        plan.reason = f"Zeit reicht nicht: {plan.total:.0f} s > Timeout {cfg.timeout:.0f} s"
        return plan

    plan.reachable = True
    plan.reason = "erreichbar"
    return plan


# ------------------------------------------------------------
# PX4: Mission + Reposition
# ------------------------------------------------------------
def enu_to_latlon(origin, east, north):
    lat0, lon0 = origin
    lat = lat0 + north / EARTH_M_PER_DEG
    lon = lon0 + east / (EARTH_M_PER_DEG * math.cos(math.radians(lat0)))
    return lat, lon


def latlon_to_enu(origin, lat, lon):
    lat0, lon0 = origin
    return ((lon - lon0) * EARTH_M_PER_DEG * math.cos(math.radians(lat0)),
            (lat - lat0) * EARTH_M_PER_DEG)


def build_mission(plan, origin, cfg, target_system=1, target_component=1):
    """
    MAVLink-MISSION_ITEM_INT-Liste (Multicopter):
    Takeoff 10 m → Geschwindigkeit → Wartepunkt (Lot-Fußpunkt) → dort warten (LOITER_UNLIM),
    bis QGCR per DO_REPOSITION übernimmt → (Pflicht für PX4) Landen am Start.
    """
    M = mavutil.mavlink
    rel, mis = M.MAV_FRAME_GLOBAL_RELATIVE_ALT, M.MAV_FRAME_MISSION
    nan = float("nan")
    items = []

    def add(cmd, frame, params, lat=0.0, lon=0.0, alt=0.0):
        items.append(M.MAVLink_mission_item_int_message(
            target_system, target_component, len(items), frame, cmd,
            1 if not items else 0, 1, *params, int(lat * 1e7), int(lon * 1e7), float(alt)))

    wait_lat, wait_lon = enu_to_latlon(origin, plan.wait[0], plan.wait[1])

    add(M.MAV_CMD_NAV_TAKEOFF, rel, (0, 0, 0, nan), origin[0], origin[1], cfg.climb_alt)
    add(M.MAV_CMD_DO_CHANGE_SPEED, mis, (1, cfg.speed, -1, 0))
    # param2 = Annahmeradius: Wartepunkt genau anfliegen
    add(M.MAV_CMD_NAV_WAYPOINT, rel, (0, cfg.wait_acceptance, 0, nan), wait_lat, wait_lon, plan.wait[2])
    add(M.MAV_CMD_NAV_LOITER_UNLIM, rel, (0, 0, 0, nan), wait_lat, wait_lon, plan.wait[2])
    add(M.MAV_CMD_NAV_LAND, rel, (0, 0, 0, nan), origin[0], origin[1], 0)
    return items


def reposition_command(target_system, target_component, lat, lon, alt_amsl, speed):
    """
    MAV_CMD_DO_REPOSITION als COMMAND_INT (lat/lon als Ganzzahl ×1e7, genau):
    param1 = Geschwindigkeit, param2 = Modus wechseln (Reposition/Hold), z = Höhe AMSL.
    """
    M = mavutil.mavlink
    return M.MAVLink_command_int_message(
        target_system, target_component, M.MAV_FRAME_GLOBAL, M.MAV_CMD_DO_REPOSITION, 0, 0,
        float(speed), float(M.MAV_DO_REPOSITION_FLAGS_CHANGE_MODE), 0.0, float("nan"),
        int(lat * 1e7), int(lon * 1e7), float(alt_amsl))
