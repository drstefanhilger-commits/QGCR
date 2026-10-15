# === PFAD-B FULL FILE: QGCR/view/plot_2d.py ===

import math
import tkinter as tk


class Plot2D(tk.Canvas):
    """
    2D-Draufsicht (Nord oben) in Metern um den Startpunkt:
    - Missions-Track (blau), geplante Wegpunkte (grau, gestrichelt)
    - Startpunkt (grünes Dreieck), Landepunkt (rotes ⊗), aktuelle Position (orange)
    - Maßstab automatisch, Maßstabsbalken unten links

    draw(data) mit data = {
        "track": [(lat, lon), ...], "waypoints": [(lat, lon), ...],
        "start": (lat, lon) | None, "landing": (lat, lon) | None,
        "vehicle": (lat, lon) | None,
    }
    """

    MARGIN = 40
    EARTH_M_PER_DEG = 111_320.0
    PLACEHOLDER = "2D-Plot: Track erscheint bei aktiver Mission"

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("bg", "white")
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(parent, **kwargs)
        self._last_data = None
        self._draw_placeholder()
        self.bind("<Configure>", lambda _e: self._redraw())

    # ------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------
    def draw(self, data):
        """Zeichnet nur, wenn sich die Daten geändert haben."""
        if data == self._last_data:
            return
        self._last_data = data
        self._redraw()

    # ------------------------------------------------------------
    # Projektion (lokal, äquirektangulär)
    # ------------------------------------------------------------
    def _origin(self, data):
        for key in ("start", "landing", "vehicle"):
            if data.get(key):
                return data[key]
        for key in ("track", "waypoints"):
            if data.get(key):
                return data[key][0]
        return None

    def _to_metres(self, origin, point):
        lat0, lon0 = origin
        lat, lon = point
        x = (lon - lon0) * self.EARTH_M_PER_DEG * math.cos(math.radians(lat0))
        y = (lat - lat0) * self.EARTH_M_PER_DEG
        return x, y

    # ------------------------------------------------------------
    # Zeichnen
    # ------------------------------------------------------------
    def _draw_placeholder(self):
        self.delete("all")
        w = max(self.winfo_width(), 400)
        h = max(self.winfo_height(), 300)
        self.create_text(w / 2, h / 2, text=self.PLACEHOLDER, fill="gray", font=("Arial", 14),
                         tags=("placeholder",))

    def _redraw(self):
        data = self._last_data
        origin = self._origin(data) if data else None
        if origin is None:
            self._draw_placeholder()
            return

        self.delete("all")
        w = max(self.winfo_width(), 400)
        h = max(self.winfo_height(), 300)

        # Alle Punkte in Metern
        layers = {key: [self._to_metres(origin, p) for p in data.get(key) or []]
                  for key in ("track", "waypoints")}
        singles = {key: self._to_metres(origin, data[key])
                   for key in ("start", "landing", "vehicle") if data.get(key)}
        points = layers["track"] + layers["waypoints"] + list(singles.values())

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        span = max(max(xs) - min(xs), max(ys) - min(ys), 20.0)      # mind. 20 m
        scale = min(w, h - 20) - 2 * self.MARGIN
        scale = max(scale, 50) / span                               # Pixel pro Meter
        cx = (max(xs) + min(xs)) / 2
        cy = (max(ys) + min(ys)) / 2

        def px(p):
            return (w / 2 + (p[0] - cx) * scale, h / 2 - (p[1] - cy) * scale)

        # Wegpunkte (geplant)
        if len(layers["waypoints"]) >= 2:
            self.create_line(*[c for p in layers["waypoints"] for c in px(p)],
                             fill="gray", dash=(4, 3), tags=("waypoints",))
        for p in layers["waypoints"]:
            x, y = px(p)
            self.create_oval(x - 3, y - 3, x + 3, y + 3, outline="gray", tags=("waypoints",))

        # Track (geflogen)
        if len(layers["track"]) >= 2:
            self.create_line(*[c for p in layers["track"] for c in px(p)],
                             fill="blue", width=2, tags=("track",))

        # Startpunkt: grünes Dreieck
        if "start" in singles:
            x, y = px(singles["start"])
            self.create_polygon(x, y - 9, x - 8, y + 6, x + 8, y + 6,
                                fill="green", outline="darkgreen", tags=("start",))
            self.create_text(x, y + 16, text="Start", fill="darkgreen", tags=("start",))

        # Landepunkt: rotes ⊗
        if "landing" in singles:
            x, y = px(singles["landing"])
            self.create_oval(x - 8, y - 8, x + 8, y + 8, outline="red", width=2, tags=("landing",))
            self.create_line(x - 6, y - 6, x + 6, y + 6, fill="red", width=2, tags=("landing",))
            self.create_line(x - 6, y + 6, x + 6, y - 6, fill="red", width=2, tags=("landing",))
            self.create_text(x, y - 16, text="Landung", fill="red", tags=("landing",))

        # Aktuelle Position
        if "vehicle" in singles:
            x, y = px(singles["vehicle"])
            self.create_oval(x - 5, y - 5, x + 5, y + 5, fill="orange", outline="darkorange",
                             tags=("vehicle",))

        # Nordpfeil + Maßstab
        self.create_text(w - 20, 15, text="N ↑", fill="black", tags=("north",))
        self._draw_scale_bar(scale, h)

    def _draw_scale_bar(self, scale, h):
        target_px = 100
        metres = target_px / scale
        nice = 10 ** math.floor(math.log10(metres))
        for factor in (1, 2, 5, 10):
            if nice * factor >= metres:
                nice *= factor
                break
        length = nice * scale
        x0, y0 = 15, h - 15
        self.create_line(x0, y0, x0 + length, y0, width=2, tags=("scale",))
        label = f"{nice:.0f} m" if nice < 1000 else f"{nice / 1000:g} km"
        self.create_text(x0 + length / 2, y0 - 9, text=label, tags=("scale",))
