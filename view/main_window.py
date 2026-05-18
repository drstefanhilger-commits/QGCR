# QGCR/view/main_window.py

import tkinter as tk
from tkinter import ttk

# from QGCR.view.button_bar import ButtonBar
from QGCR.view.status_bar import StatusBar
from QGCR.view.home_tab import HomeTab
from QGCR.view.mission_tab import MissionTab
from QGCR.view.log_tab import LogTab


class MainWindow(ttk.Frame):
    """
    MainWindow ist ein Frame, KEIN tk.Tk.
    Die Application() erzeugt das Tk-Root und bettet MainWindow ein.
    """

    def __init__(self, parent, controller, queue_registry=None):
        super().__init__(parent)

        self.controller = controller
        self.queue_registry = queue_registry

        # Layout-Konfiguration
        self.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)   # Tabs
        self.rowconfigure(1, weight=0)   # StatusBar

        # # ------------------------------------------------------------
        # # ButtonBar (oben)
        # # ------------------------------------------------------------
        # self.button_bar = ButtonBar(self, controller=self.controller)
        # self.button_bar.grid(row=0, column=0, sticky="ew")

        # ------------------------------------------------------------
        # Notebook (Tabs)
        # ------------------------------------------------------------
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        # Tabs erzeugen
        self.home_tab = HomeTab(self.notebook, controller=self.controller)
        self.mission_tab = MissionTab(self.notebook, controller=self.controller)
        self.log_tab = LogTab(self.notebook)

        # Tabs hinzufügen
        self.notebook.add(self.home_tab, text="Home")
        self.notebook.add(self.mission_tab, text="Mission")
        self.notebook.add(self.log_tab, text="Log")

        # ------------------------------------------------------------
        # StatusBar (unten)
        # ------------------------------------------------------------
        self.status_bar = StatusBar(self, controller=self.controller)
        self.status_bar.grid(row=1, column=0, sticky="ew")
