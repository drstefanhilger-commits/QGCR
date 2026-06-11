# === PFAD-B FULL FILE: QGCR/communication/microservices/microservice_factory.py ===

from QGCR.communication.microservices.mission_microservice import MissionMicroService
from QGCR.communication.microservices.mission_download_microservice import MissionDownloadMicroService
from QGCR.communication.microservices.upload_microservice import UploadMicroService
from QGCR.communication.microservices.home_microservice import HomeMicroService
from QGCR.communication.microservices.parameter_sync_microservice import ParameterSyncMicroService
from QGCR.communication.microservices.reset_microservice import ResetMicroService
from QGCR.communication.microservices.takeoff_microservice import TakeoffMicroService


class MicroServiceFactory:
    """
    Erzeugt deterministisch alle MicroServices für ein UAV,
    sobald PX4 verbunden ist.
    """

    def __init__(self, model, connection):
        self.model = model
        self.connection = connection

    def initialize(self):
        """
        Initialisiert ALLE MicroServices deterministisch.
        Muss erst nach PX4-Connect aufgerufen werden.
        """

        master = self.connection.master
        ts = master.target_system
        tc = master.target_component

        # Mission (klassisch)
        self.model.mission = MissionMicroService(master, ts, tc)

        # Upload (FSM)
        self.model.upload = UploadMicroService(self.model, self.connection)

        # Download (connection, model)
        self.model.download = MissionDownloadMicroService(self.connection, self.model)

        # Home (klassisch)
        self.model.home = HomeMicroService(master, ts, tc)

        # Takeoff (FSM)
        self.model.takeoff = TakeoffMicroService(self.model, self.connection)

        # Reset (FSM)
        self.model.reset = ResetMicroService(self.model)

        # ParamSync (klassisch)
        self.model.param_sync = ParameterSyncMicroService(master, ts, tc)

        print(f"[MicroServiceFactory] MicroServices initialisiert (sysid={ts}, compid={tc})")
