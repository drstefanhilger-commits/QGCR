# === PFAD-B FULL FILE: QGCR/view/gis/overlay.py ===

import tkinter as tk


class OverlayCanvas(tk.Canvas):
    """
    Phase 2:
    - Overlay über der Karte
    - bg wird auf Elternfarbe gesetzt (kein ""!)
    """

    def __init__(self, parent):
        super().__init__(
            parent,
            bg=parent["bg"],          # FIX: kein leerer String
            highlightthickness=0
        )

        # Overlay immer über der Karte platzieren
        self.place(relx=0, rely=0, relwidth=1, relheight=1)

    def clear(self):
        self.delete("all")
