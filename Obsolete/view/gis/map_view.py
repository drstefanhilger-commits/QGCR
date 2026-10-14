# === PFAD-B FULL FILE: gis/map_view.py ===

import tkinter as tk
import tkintermapview


class MapView(tk.Frame):
    """
    Phase 2:
    - Wrapper um tkintermapview
    - Zeichnet Home, Waypoints und Mission-Pfad
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.map = tkintermapview.TkinterMapView(
            self,
            corner_radius=0
        )
        self.map.pack(fill="both", expand=True)

        # Marker-Referenzen
        self.home_marker = None
        self.wp_markers = []
        self.path_line = None

    # ------------------------------------------------------------
    # Home-Position
    # ------------------------------------------------------------
    def set_home(self, lat, lon):
        if self.home_marker:
            self.home_marker.delete()

        self.home_marker = self.map.set_marker(
            lat, lon,
            text="HOME",
            marker_color_circle="green",
            marker_color_outside="darkgreen"
        )

    # ------------------------------------------------------------
    # Waypoints
    # ------------------------------------------------------------
    def set_waypoints(self, wp_list):
        # Alte Marker löschen
        for m in self.wp_markers:
            m.delete()
        self.wp_markers.clear()

        for wp in wp_list:
            lat = wp["x"] / 1e7
            lon = wp["y"] / 1e7
            seq = wp["seq"]

            marker = self.map.set_marker(
                lat, lon,
                text=f"WP{seq}",
                marker_color_circle="blue",
                marker_color_outside="darkblue"
            )
            self.wp_markers.append(marker)

    # ------------------------------------------------------------
    # Mission-Pfad
    # ------------------------------------------------------------
    def set_path(self, wp_list):
        if self.path_line:
            self.map.delete(self.path_line)
            self.path_line = None

        if len(wp_list) < 2:
            return

        coords = []
        for wp in wp_list:
            lat = wp["x"] / 1e7
            lon = wp["y"] / 1e7
            coords.append((lat, lon))

        self.path_line = self.map.set_path(coords)

    # ------------------------------------------------------------
    # Auto-Zoom auf Missionsgebiet
    # ------------------------------------------------------------
    def auto_zoom(self, wp_list, home_pos=None):
        points = []

        if home_pos:
            points.append(home_pos)

        for wp in wp_list:
            lat = wp["x"] / 1e7
            lon = wp["y"] / 1e7
            points.append((lat, lon))

        if not points:
            return

        # Bounding Box berechnen
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]

        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)

        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2

        self.map.set_position(center_lat, center_lon)

        # Zoom-Level abhängig von Ausdehnung
        lat_span = max_lat - min_lat
        lon_span = max_lon - min_lon
        span = max(lat_span, lon_span)

        if span < 0.0005:
            zoom = 18
        elif span < 0.001:
            zoom = 17
        elif span < 0.005:
            zoom = 16
        elif span < 0.01:
            zoom = 15
        else:
            zoom = 14

        self.map.set_zoom(zoom)
