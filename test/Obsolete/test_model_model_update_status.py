#!/usr/bin/env python3
# === PFAD-B FULL FILE: QGCR/test/Obsolete/test_model_model_update_status.py ===
# Obsolet: Model.update_status() existiert nicht mehr (ausgelagert aus test/pytest/test_model_model.py)

from QGCR.model.model import Model
from QGCR.core.queue_registry import QueueRegistry


def pop_gui_events(reg):
    return reg.require("gui").pop_all()


# ------------------------------------------------------------
# STATUS
# ------------------------------------------------------------
def test_update_status_pushes_gui_event():
    reg = QueueRegistry()
    m = Model(reg)

    m.update_status("Hello World")

    events = pop_gui_events(reg)
    assert len(events) == 1
    tag, text = events[0]
    assert tag == "status"
    assert text == "Hello World"


