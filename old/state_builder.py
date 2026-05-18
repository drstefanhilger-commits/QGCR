# === PFAD-B FULL FILE: QGCR/states/state_builder.py ===

from QGCR.states.startup.startup_hfsm import StartupHFSM
from QGCR.states.ready.ready_hfsm import ReadyHFSM
from QGCR.states.airborne.airborne_hfsm import AirborneHFSM
from QGCR.states.mission.mission_hfsm import MissionHFSM  # wird ignoriert, aber import bleibt ok


def build_state_machine(model):
    """
    Baut die High-Level-HFSMs.
    Keine SubFSMs werden hier erzeugt – das machen die HFSMs selbst.
    """

    # StartupHFSM benötigt nur model + state_map (kommt aus model.startup_state_map)
    startup_hfsm = StartupHFSM(
        model=model,
        state_map=model.startup_state_map
    )

    # ReadyHFSM erzeugt seine SubFSMs selbst
    ready_hfsm = ReadyHFSM(
        model=model
    )

    # MissionHFSM wird ignoriert, aber wir geben eine Instanz zurück
    mission_hfsm = MissionHFSM(model)

    # AirborneHFSM erzeugt seinen Controller selbst
    airborne_hfsm = AirborneHFSM(
        model=model
    )

    return startup_hfsm, ready_hfsm, mission_hfsm, airborne_hfsm
