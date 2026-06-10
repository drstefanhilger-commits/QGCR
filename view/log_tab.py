import tkinter as tk
from tkinter import ttk


class LogTab(ttk.Frame):
    """
    Drei getrennte Log-Fenster:
    - PX4-Logs (1-N Instanzen)
    - Simulator-Logs (Gazebo, Matlab, Python-Sim)
    - QGCR-Logs (HFSM, GUI, MicroServices)
    """

    def __init__(self, parent):
        super().__init__(parent)

        # ------------------------------------------------------------
        # Layout
        # ------------------------------------------------------------
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        # ------------------------------------------------------------
        # PX4-Logs
        # ------------------------------------------------------------
        px4_frame = ttk.LabelFrame(self, text="PX4 Logs")
        px4_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        px4_frame.rowconfigure(0, weight=1)
        px4_frame.columnconfigure(0, weight=1)

        self.px4_text = tk.Text(px4_frame, height=10, wrap="none")
        self.px4_text.grid(row=0, column=0, sticky="nsew")

        px4_scroll = ttk.Scrollbar(px4_frame, orient="vertical", command=self.px4_text.yview)
        px4_scroll.grid(row=0, column=1, sticky="ns")
        self.px4_text.configure(yscrollcommand=px4_scroll.set)

        # ------------------------------------------------------------
        # Simulator-Logs
        # ------------------------------------------------------------
        sim_frame = ttk.LabelFrame(self, text="Simulator Logs (Gazebo / Matlab / Python)")
        sim_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        sim_frame.rowconfigure(0, weight=1)
        sim_frame.columnconfigure(0, weight=1)

        self.sim_text = tk.Text(sim_frame, height=10, wrap="none")
        self.sim_text.grid(row=0, column=0, sticky="nsew")

        sim_scroll = ttk.Scrollbar(sim_frame, orient="vertical", command=self.sim_text.yview)
        sim_scroll.grid(row=0, column=1, sticky="ns")
        self.sim_text.configure(yscrollcommand=sim_scroll.set)

        # ------------------------------------------------------------
        # QGCR-Logs
        # ------------------------------------------------------------
        qgcr_frame = ttk.LabelFrame(self, text="QGCR Logs")
        qgcr_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

        qgcr_frame.rowconfigure(0, weight=1)
        qgcr_frame.columnconfigure(0, weight=1)

        self.qgcr_text = tk.Text(qgcr_frame, height=10, wrap="none")
        self.qgcr_text.grid(row=0, column=0, sticky="nsew")

        qgcr_scroll = ttk.Scrollbar(qgcr_frame, orient="vertical", command=self.qgcr_text.yview)
        qgcr_scroll.grid(row=0, column=1, sticky="ns")
        self.qgcr_text.configure(yscrollcommand=qgcr_scroll.set)

    # ------------------------------------------------------------
    # Append-Methoden
    # ------------------------------------------------------------
    def append_px4(self, text: str):
        self.px4_text.insert("end", text + "\n")
        self.px4_text.see("end")

    def append_sim(self, text: str):
        self.sim_text.insert("end", text + "\n")
        self.sim_text.see("end")

    def append_qgcr(self, text: str):
        self.qgcr_text.insert("end", text + "\n")
        self.qgcr_text.see("end")
