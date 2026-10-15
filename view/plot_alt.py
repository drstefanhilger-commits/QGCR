# === PFAD-B FULL FILE: QGCR/view/plot_alt.py ===

import math
import tkinter as tk


class AltitudePlot(tk.Canvas):
    """
    Höhenverlauf: Höhe über Home [m] über der Zeit seit Missionsstart [s].

    draw(data) mit data = {"samples": [(t, alt), ...]}
    """

    LEFT, RIGHT, TOP, BOTTOM = 45, 15, 18, 22
    PLACEHOLDER = "Höhen-Plot: Verlauf erscheint bei aktiver Mission"

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("bg", "white")
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("height", 170)
        super().__init__(parent, **kwargs)
        self._last_data = None
        self._redraw()
        self.bind("<Configure>", lambda _e: self._redraw())

    def draw(self, data):
        if data == self._last_data:
            return
        self._last_data = data
        self._redraw()

    @staticmethod
    def nice_step(span, target_ticks=5):
        """Schöne Teilung (1, 2, 5 · 10^n) für etwa target_ticks Teilstriche."""
        raw = max(span, 1e-9) / target_ticks
        base = 10 ** math.floor(math.log10(raw))
        for factor in (1, 2, 5, 10):
            if base * factor >= raw:
                return base * factor
        return base * 10

    def _redraw(self):
        self.delete("all")
        w = max(self.winfo_width(), 400)
        h = max(self.winfo_height(), 120)
        samples = (self._last_data or {}).get("samples") or []

        if len(samples) < 2:
            self.create_text(w / 2, h / 2, text=self.PLACEHOLDER, fill="gray", font=("Arial", 12),
                             tags=("placeholder",))
            return

        t_max = max(samples[-1][0], 1.0)
        alts = [a for _, a in samples]
        a_min = min(0.0, min(alts))
        a_max = max(max(alts), a_min + 5.0)
        a_step = self.nice_step(a_max - a_min, 4)
        a_max = math.ceil(a_max / a_step) * a_step
        a_min = math.floor(a_min / a_step) * a_step
        t_step = self.nice_step(t_max, 6)

        x0, x1 = self.LEFT, w - self.RIGHT
        y0, y1 = h - self.BOTTOM, self.TOP

        def px(t, a):
            return (x0 + (x1 - x0) * t / t_max,
                    y0 - (y0 - y1) * (a - a_min) / (a_max - a_min))

        # Achsen + Gitter
        self.create_line(x0, y0, x1, y0, tags=("axis",))
        self.create_line(x0, y0, x0, y1, tags=("axis",))
        a = a_min
        while a <= a_max + 1e-9:
            _, y = px(0, a)
            self.create_line(x0, y, x1, y, fill="#e6e6e6", tags=("grid",))
            self.create_text(x0 - 5, y, text=f"{a:g}", anchor="e", tags=("ytick",))
            a += a_step
        t = 0.0
        while t <= t_max + 1e-9:
            x, _ = px(t, a_min)
            self.create_text(x, y0 + 10, text=f"{t:g}", tags=("xtick",))
            t += t_step
        self.create_text(x0, y1 - 9, text="Höhe [m]", anchor="w", tags=("label",))
        self.create_text(x1, y0 + 10, text="t [s]", anchor="e", tags=("label",))

        # Verlauf + aktueller Wert
        self.create_line(*[c for s in samples for c in px(*s)], fill="blue", width=2, tags=("altitude",))
        self.create_text(x1, y1 - 9, text=f"{samples[-1][1]:.1f} m", anchor="e",
                         fill="blue", tags=("current",))
