# log_tab.py

import tkinter as tk
from tkinter import ttk

class LogTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.text_widget = tk.Text(
            self,
            wrap="none",
            height=20,
            background="#ffffff",
            foreground="#000000",
            insertbackground="#000000",
            font=("Consolas", 10),
        )

        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=self.scrollbar.set)

        self.text_widget.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def update_logs(self, messages: list[str]):
        # NICHT mehr disabled setzen → Kopieren möglich
        self.text_widget.delete("1.0", "end")

        for msg in messages:
            self.text_widget.insert("end", msg + "\n")

        self.text_widget.see("end")
