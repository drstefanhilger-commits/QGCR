# === PFAD-B FULL FILE: QGCR/model/intercept.py ===
"""
Wartepunkt-Berechnung und Missionserzeugung für die kontrollierte FSL-Drohne.

Koordinaten der Berechnung: lokal ENU in Metern relativ zum Startpunkt der FSL
(Ost, Nord, Höhe über Start). Umrechnung nach lat/lon erst für die Mission.

Zeitmodell der FSL (Multicopter, gemessen in SITL mit gz_fsl_rocket_vtol):
- ~16 s vom Missionsstart bis zum Beginn des Horizontalflugs (Armen, Steigen auf 10 m)
- Reiseflug: DO_CHANGE_SPEED 8 m/s → ca. 7,5 m/s über Grund
- ca. 4 s Abbremsen am Wegpunkt
"""

import math
from dataclasses import dataclass, field

from pymavlink import mavutil


EARTH_M_PER_DEG = 111_320.0


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


@dataclass
class InterceptConfig:
    climb_alt: float = 10.0         # Aufstieg auf 10 m über Grund
    lead_distance: float = 10.0     # Wartepunkt mindestens 10 m vor dem Trigger
    follow_time: float = 10.0       # 10 s entlang der Trigger-Bahn
    speed: float = 8.0              # Soll-Geschwindigkeit FSL (DO_CHANGE_SPEED) [m/s]
    speed_efficiency: float = 0.92  # erreichte / gesetzte Geschwindigkeit (SITL ≈ 7,5/8)
    prep_time: float = 3.0          # Trigger → Missionsstart (Planung, Upload, Startbefehl) [s]
    start_delay: float = 16.0       # Missionsstart → Beginn Horizontalflug [s]
    approach_time: float = 4.0      # Abbremsen am Wartepunkt [s]
    climb_rate: float = 2.0         # vertikale Geschwindigkeit für Höhenänderung [m/s]
    min_alt: float = 10.0           # Wartepunkt nie unter 10 m
    max_search: float = 3000.0      # max. Suchweg entlang der Trigger-Bahn [m]
    step: float = 1.0               # Suchschritt [m]
    timeout: float = 180.0          # Überwachung: max. Flugzeit ab Start [s]
    battery_min: float = 30.0       # Überwachung: min. Akku [%]


@dataclass
class InterceptPlan:
    reachable: bool
    reason: str = ""
    trigger_now: tuple = None       # (e, n, u) bei Planung
    wait: tuple = None              # Wartepunkt (e, n, u)
    follow_end: tuple = None        # Ende der 10-s-Strecke entlang der Bahn
    along: float = 0.0              # Abstand Trigger → Wartepunkt entlang der Bahn [m]
    t_fsl: float = 0.0              # Ankunft FSL am Wartepunkt ab Planung [s]
    t_trigger: float = 0.0          # Trigger am Wartepunkt ab Planung [s]
    hold: float = 0.0               # Wartezeit der FSL am Wartepunkt [s]
    heading_deg: float = 0.0        # Flugrichtung des Triggers (0 = Nord, 90 = Ost)
    path: list = field(default_factory=list)   # Bahn des Triggers zur Anzeige [(e, n, u), ...]


def fsl_time_to(point, cfg):
    """Zeit vom Trigger (Planung), bis die FSL am Punkt (e, n, u) ist [s]."""
    e, n, u = point
    horizontal = math.hypot(e, n) / (cfg.speed * cfg.speed_efficiency)
    vertical = abs(u - cfg.climb_alt) / cfg.climb_rate
    return cfg.prep_time + cfg.start_delay + max(horizontal, vertical) + cfg.approach_time


def plan_intercept(trigger, now, cfg):
    """
    Frühester Punkt auf der geschätzten Bahn des Triggers, den die FSL erreicht,
    solange der Trigger noch mindestens lead_distance davor ist.
    """
    v = trigger.ground_speed
    if v < 0.1:
        return InterceptPlan(False, "Trigger bewegt sich nicht (keine Flugrichtung)")

    e0, n0, u0 = trigger.position_at(now)
    de, dn = trigger.v_east / v, trigger.v_north / v
    climb_per_m = trigger.v_up / v
    heading = (math.degrees(math.atan2(de, dn)) + 360.0) % 360.0

    def point(s):
        return (e0 + de * s, n0 + dn * s, max(cfg.min_alt, u0 + climb_per_m * s))

    s = cfg.lead_distance
    while s <= cfg.max_search:
        p = point(s)
        t_fsl = fsl_time_to(p, cfg)
        t_lead = (s - cfg.lead_distance) / v      # Trigger noch lead_distance vor dem Punkt
        if t_fsl <= t_lead:
            follow = cfg.speed * cfg.speed_efficiency * cfg.follow_time
            f = (p[0] + de * follow, p[1] + dn * follow, p[2])
            path_end = s + follow + 50.0
            return InterceptPlan(
                True, "erreichbar",
                trigger_now=(e0, n0, u0), wait=p, follow_end=f, along=s,
                t_fsl=t_fsl, t_trigger=s / v, hold=t_lead - t_fsl, heading_deg=heading,
                path=[(e0, n0, u0), point(path_end)],
            )
        s += cfg.step

    return InterceptPlan(False, f"kein Wartepunkt innerhalb {cfg.max_search:.0f} m erreichbar",
                         trigger_now=(e0, n0, u0), heading_deg=heading,
                         path=[(e0, n0, u0), point(cfg.max_search)])


def enu_to_latlon(origin, east, north):
    lat0, lon0 = origin
    lat = lat0 + north / EARTH_M_PER_DEG
    lon = lon0 + east / (EARTH_M_PER_DEG * math.cos(math.radians(lat0)))
    return lat, lon


def build_mission(plan, origin, cfg, target_system=1, target_component=1):
    """
    MAVLink-MISSION_ITEM_INT-Liste (Multicopter):
    Takeoff 10 m → Geschwindigkeit → Wartepunkt → Warten → 10 s entlang der Bahn → Landen am Start.
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
    fol_lat, fol_lon = enu_to_latlon(origin, plan.follow_end[0], plan.follow_end[1])

    add(M.MAV_CMD_NAV_TAKEOFF, rel, (0, 0, 0, nan), origin[0], origin[1], cfg.climb_alt)
    add(M.MAV_CMD_DO_CHANGE_SPEED, mis, (1, cfg.speed, -1, 0))
    add(M.MAV_CMD_NAV_WAYPOINT, rel, (0, 0, 0, nan), wait_lat, wait_lon, plan.wait[2])
    if plan.hold >= 1.0:
        add(M.MAV_CMD_NAV_LOITER_TIME, rel, (round(plan.hold, 1), 0, 0, nan), wait_lat, wait_lon, plan.wait[2])
    add(M.MAV_CMD_NAV_WAYPOINT, rel, (0, 0, 0, nan), fol_lat, fol_lon, plan.follow_end[2])
    add(M.MAV_CMD_NAV_LAND, rel, (0, 0, 0, nan), origin[0], origin[1], 0)
    return items
